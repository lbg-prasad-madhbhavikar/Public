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