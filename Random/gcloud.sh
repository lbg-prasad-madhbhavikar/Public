#!/bin/bash
# set -x
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8


print_message() {
  local message=$1
  local color=$2
  if $USE_COLORS; then
    echo -e "${color}${message}\033[0m"
  else
    echo "$message"
  fi
}

space() {
  echo ""
}


# print_as_columns() {
#   local column_width=35
# local terminal_width=$(tput cols)
# (( terminal_width < column_width )) && terminal_width=$column_width
# local columns=$(( terminal_width / column_width ))
# echo "$columns $terminal_width"

# local i=1
# local col=1
# local format=""
# local args=()

# while IFS= read -r line; do
#   format+="%-${column_width}s"
#   args+=("$i. $line")

#   (( i++ ))
#   (( col++ ))

#   if (( col > columns )); then
#     printf "$format\n" "${args[@]}"
#     format=""
#     args=()
#     col=1
#   fi
# done <<< "$(gcloud projects list --format="value(projectId)")"

# # Print remaining columns if any
# if (( ${#args[@]} > 0 )); then
#   printf "$format\n" "${args[@]}"
# fi

# }

select_account() {
  print_message "Available Accounts" "\033[1;34m"
  local accounts=$(gcloud auth list --format="value(account)")
  echo -e "\033[1;34m"
  echo "$accounts" | nl -w4 -s'. '
  echo -e "\033[0m"
  space
  read -p "Select index of a account to be used : " account_index
  local selected_account=$(echo "$accounts" | sed -n "${account_index}p")
  gcloud config set account "$selected_account"
}

prompt_login() {
  read -p "Do you want to login? (y/n): " choice
  if [[ $choice == "y" || $choice == "Y" ]]; then
    gcloud auth login
  fi
}

select_project() {
  print_message "Available Projects" "\033[1;32m"
  local projects=$(gcloud projects list --format="value(projectId)")
  local i=0
  echo "$projects" | while read -r project; do
    print_message "$((i + 1)). ${project}" "\033[1;32m"
    i=$((i + 1))
  done
  # print_as_columns $projects
  space
  read -p "Select index of a project to be used: " project_index
  local selected_project=$(echo "$projects" | sed -n "${project_index}p")
  gcloud config set project "$selected_project"
  export SELECTED_PROJECT="$selected_project"
}


# select_project() {
#   print_message "Available Projects" "\033[1;32m"
#   local projects=$(gcloud projects list --format="value(projectId)")
#   local i=1
  
#   # if [ -f ".projects.cache" ]; then
#   #   rm ".projects.cache"
#   # fi
#   eecho "$projects" | nl -w4 -s'. ' | column -s '\n'
#   # echo "$projects" | while read -r project; do
#   #   echo -e "${i}\t${project}" >> .projects.cache
#   #   i=$((i + 1))
#   # done

#   # if [ -f ".projects.cache" ]; then
#   #   rm ".projects.cache"
#   # fi
#   space
#   read -p "Select index of a project to be used: " project_index
#   local selected_project=$(echo "$projects" | sed -n "${project_index}p")
#   gcloud config set project "$selected_project"
#   export SELECTED_PROJECT="$selected_project"
# }

prompt_pull_gke_secret() {
  local project_id=$1
  local gke_cluster_name=$2
  local gke_cluster_region=$3
  read -p "Do you want to pull gke secret? (y/n): " choice
  if [[ $choice == "y" || $choice == "Y" ]]; then
    gcloud container clusters get-credentials ${gke_cluster_name} --region ${gke_cluster_region} --project ${project_id}
  fi
}

get_gke_clusters() {
  local project_id=$1

  print_message "Available GKE clusters for project: $project_id" "\033[1;36m"

  local clusters=$(gcloud container clusters list --project "$project_id" --format="value(name,location)")

  if [[ -z "$clusters" ]]; then
    print_message "No GKE clusters found in project: $project_id" "\033[1;31m"
    return 1
  fi

  local i=0
  local cluster_array=()
  echo "$clusters" | while read -r name location; do
    i=$((i + 1))
    cluster_array+=("$name $location")
    print_message "$i. Cluster: $name | Region/Zone: $location" "\033[1;33m"
  done

  space
  read -p "Select index of a cluster to use: " cluster_index

  # Re-fetch the selected line (since arrays in subshells don't persist)
  local selected=$(echo "$clusters" | sed -n "${cluster_index}p")
  export GKE_CLUSTER_NAME=$(echo "$selected" | awk '{print $1}')
  export GKE_CLUSTER_REGION=$(echo "$selected" | awk '{print $2}')
}

select_account
space
prompt_login
space
select_project
space
get_gke_clusters ${SELECTED_PROJECT}
space
prompt_pull_gke_secret ${SELECTED_PROJECT} ${GKE_CLUSTER_NAME} ${GKE_CLUSTER_REGION}
space

read -p "Press any key to continue... " deploy