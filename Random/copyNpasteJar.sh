#!/bin/bash

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Variables
SOURCE_BUCKET="source-bucket-name"
DEST_BUCKETS=("dest-bucket1-name" "dest-bucket2-name")

JAR_NAME=("jar-1" "jar-2")

LOCAL_PATH="/path/to/local/directory"

# Copy the JAR from the source bucket to local directory
gsutil cp gs://$SOURCE_BUCKET/$JAR_NAME $LOCAL_PATH

# Delete the JAR from the source bucket
gsutil rm gs://$SOURCE_BUCKET/$JAR_NAME

# Move the JAR to other destination buckets
for BUCKET in "${DEST_BUCKETS[@]}"; do
  gsutil cp $LOCAL_PATH/$JAR_NAME gs://$BUCKET/
done

echo "JAR file copied locally and moved to destination buckets successfully."

