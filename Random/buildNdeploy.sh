#!/bin/bash
# set -x
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

DOCKER_TARGET_ENV="playpen"
PROJECT_ID="playpen-d9fbec"
GKE_NAMESPACE="default"
GAR_BUCKET_NAME="$PROJECT_ID-terraform-bucket"
DOCKER_REGION="europe-west2"
DOCKER_REGISTRY="$DOCKER_REGION-docker.pkg.dev"
LIB_BUCKET_NAME="$PROJECT_ID-lib-bucket"
USE_COLORS=true

components=("foundation-component-audit" "foundation-component-workflow" "foundation-component-scheduler" "foundation-component-registration-ui" "foundation-component-registration-api" "foundation-component-data-transformation-ui" "transformation-api" "foundation-component-feature-flag-manager")
k8s_components=("foundation-component-audit" "foundation-component-workflow" "foundation-component-scheduler" "registration-ui" "foundation-registration-api" "transformation-ui" "data-transformation-framework-api"  "foundation-component-feature-flag-manager" )

print_message() {
  local message=$1
  local color=$2
  if $USE_COLORS; then
    echo -e "${color}${message}\033[0m"
  else
    echo "$message"
  fi
}

select_component() {
  print_message "Available Services" "\033[1;34m"
  for i in "${!components[@]}"; do
    print_message "$((i+1)). ${components[$i]}" "\033[1;34m"
  done
  read -p "Select index of a service : " component_index
  selected_component=${components[$((component_index-1))]}
  selected_k8s_component=${k8s_components[$((component_index-1))]}
}

list_files_in_bucket() {
  files=$(gsutil ls gs://$LIB_BUCKET_NAME/${selected_component}*)
}

extract_versions() {
  versions=()
  for file in $files; do
    version=$(echo $file |grep -oP '(?<=-)[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z]+\.[0-9]+)?(?=\.(jar|zip))')
    selected_extension=$(echo $file | grep -oP '(?<=-)[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z]+\.[0-9]+)?\.(jar|zip)' | sed 's/.*\.//')
    versions+=($version)
  done
  # versions=$(sort_versions "${versions[@]}") FIXME
}

select_version() {
  if [ ${#versions[@]} -eq 0 ]; then
    print_message "No Deployable versions found, check the file naming standard ${selected_component}" "\033[1;31m"
    exit 1
  fi
  print_message "Available versions for ${selected_component}" "\033[1;34m"
  for i in "${!versions[@]}"; do
    print_message "$((i+1)). ${versions[$i]}" "\033[1;34m"
  done
  read -p "Select index of a version : " version_index
  selected_version=${versions[$((version_index-1))]}
}

sort_versions() {
  versions=("$@")
  sorted_versions=$(printf "%s\n" "${versions[@]}" | sort -rV)
  echo "${sorted_versions[@]}"
}

download_file() {
  if [ -z "$selected_extension" ]; then 
    selected_extension="zip"
  fi
  file_name="${selected_component}-${selected_version}.$selected_extension"
  destination_dir="jars/${selected_component}"
  mkdir -p $destination_dir
  if [ -f "${destination_dir}/${file_name}" ]; then
    read -p "File ${file_name} already exists. Do you want to re-download? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
      print_message "Skipping download of ${file_name}." "\033[1;33m"
      return
    fi
  fi
  print_message "Downloading ${file_name}..." "\033[1;32m"
  gsutil -m cp gs://$LIB_BUCKET_NAME/$file_name $destination_dir/
  print_message "Download of $file_name complete." "\033[1;32m"
}

generate_cloudbuild_yaml() {
  timestamp=$(date +%Y%m%d%H%M%S)
  image_tag="${selected_component}:${selected_version}.${timestamp}-${DOCKER_TARGET_ENV}"
  dockerfile="${selected_component}.dockerfile"

  cat <<EOF > ${selected_component}-cloudbuild.yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', '${dockerfile}', '-t', '${DOCKER_REGISTRY}/${PROJECT_ID}/main/${image_tag}', '.']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', '${DOCKER_REGISTRY}/${PROJECT_ID}/main/${image_tag}']
images:
- '${DOCKER_REGISTRY}/${PROJECT_ID}/main/${image_tag}'
EOF
  print_message "Built cloudbuild.yaml for image tag ${image_tag}" "\033[1;32m"
}

update_dockerfile() {
  dockerfile_path="${selected_component}.dockerfile"
  sed -i -r "s|COPY +jars/${selected_component}/${selected_component}-.*\.${selected_extension} +app\.${selected_extension}|COPY jars/${selected_component}/${file_name} app.${selected_extension}|" $dockerfile_path
  print_message "${dockerfile_path} updated." "\033[1;32m"
  # read -p "Press any key to continue... " deploy1
}

submit_build() {
  if $USE_COLORS; then
    echo -e "\033[1;37m"
  fi
  set -x
  gcloud builds submit --config=${selected_component}-cloudbuild.yaml --region=$DOCKER_REGION --gcs-source-staging-dir=gs://$GAR_BUCKET_NAME/images
  set +x
  rm ${selected_component}-cloudbuild.yaml
  if $USE_COLORS; then
    echo -e "\033[0m"
  fi
}

list_available_images() {
  available_images=$(gcloud artifacts tags list --package="$selected_component" --repository=main --location=$DOCKER_REGION --format="value(name)" --sort-by=~name --limit=10)
  print_message "Available images" "\033[1;34m"
  index=1
  tags=()
  while IFS= read -r tag; do
    print_message "$index. $tag" "\033[1;34m"
    tags+=("$tag")
    index=$((index + 1))
  done <<< "$available_images"
}

update_deployment_yaml() {
  deployment_file="../manifest_files/services/manual/${selected_component}/deployment.yaml"
  service_file="../manifest_files/services/manual/${selected_component}/service.yaml"
  proposed_image=$(echo "${DOCKER_REGISTRY}/${PROJECT_ID}/main/${selected_component}:${image_tag}" | sed "s|\(.*\):${selected_component}:\(.*\)|\1:\2|")
  echo $proposed_image
  sed -i "s|image: .*|image: ${proposed_image}|" $deployment_file
  print_message "Updated deployment defination for ${deployment_file} with ${image_tag}" "\033[1;32m"
}

get_deployed_version() {
  deployed_image=$(kubectl --insecure-skip-tls-verify get deployment $selected_k8s_component -n $GKE_NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
  deployed_version=$(echo $deployed_image | grep -oP '[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9]+)?')
  print_message "$selected_component" "\033[1;33m"
  print_message "Deployed version : $deployed_version" "\033[1;33m"
  print_message "Image version :  $deployed_image" "\033[1;33m"
}

check_pods_running() {
  kubectl --insecure-skip-tls-verify get pods -n $GKE_NAMESPACE -l app=$selected_k8s_component -o jsonpath='{.items[*].status.phase}' | grep -qv "Running"
}

deploy_application() {
  read -p "Do you want to delete the previous deployment? (y/n): " deploy
  if [ "$deploy" != "n" ]; then
    print_message "Deleting previous deployment" "\033[1;31m"
    kubectl --insecure-skip-tls-verify delete deployment $selected_k8s_component
  fi
  kubectl --insecure-skip-tls-verify apply -f $deployment_file
  kubectl --insecure-skip-tls-verify apply -f $service_file
  max_iterations=15
  iteration=0

  while check_pods_running; do
    if [ $iteration -ge $max_iterations ]; then
      print_message "Manual intervention required. Exiting..." "\033[1;31m"
      kubectl --insecure-skip-tls-verify get pods | grep $selected_k8s_component
      read -p "Press any key to exit... " deploy
      exit 0
    fi
    print_message "Waiting for all pods to be in 'Running' status..." "\033[1;33m"
    sleep 2
    iteration=$((iteration + 1))
  done
  print_message "Deployment of ${selected_component} successful" "\033[1;32m"
}

# Main script execution
select_component
get_deployed_version

read -p "Do you want to proceed with a build? (y/n): " proceed
if [ "$proceed" != "y" ]; then
  print_message "Build process aborted." "\033[1;31m"
  list_available_images
  read -p "Select index of image for deployment: " tag_index
  image_tag=${tags[$((tag_index-1))]}
  update_deployment_yaml
else
  list_files_in_bucket
  extract_versions
  select_version
  download_file
  update_dockerfile
  generate_cloudbuild_yaml
  update_deployment_yaml
  submit_build
fi

read -p "Do you want to proceed with the deployment? (y/n): " deploy
if [ "$deploy" != "y" ]; then
  print_message "Deploy process aborted." "\033[1;31m"
  exit 0
fi

deploy_application

read -p "Press any key to continue... " deploy
rm -rf jars