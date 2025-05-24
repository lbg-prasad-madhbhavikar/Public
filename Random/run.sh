#!/bin/bash

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


select_services() {
    local script_labels=("Account actions" "Stratos - Deployments")
    local scripts=("scripts/gcloud.sh" "scripts/buildNdeploy.sh")
    
    print_message "Available Services" "\033[1;34m"
    for i in "${!script_labels[@]}"; do
        print_message "$((i+1)). ${script_labels[$i]}" "\033[1;34m"
    done
    
    space
    read -p "Select index of a service : " component_index
    local selected_service=${scripts[$((component_index-1))]}
    $(${selected_service})
}

while true; do
    select_services
    space
    space
    read -p "Do you want to quit? (y/n): " choice
    if [ "$choice" = "y" ]; then
        echo "Exiting..."
        break
    fi
done
