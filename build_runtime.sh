#!/bin/bash

# Assumes you've set your AWS creds up already.
# TODO: Add test for ^.

docker build \
    --build-arg AWS_SECRET_ACCESS_KEY=$(cat ~/.aws/credentials | grep secret | cut -d '=' -f2 | awk '{$1=$1};1') \
    --build-arg AWS_ACCESS_KEY_ID=$(cat ~/.aws/credentials | grep id | cut -d '=' -f2 | awk '{$1=$1};1') \
    -t runtime runtime/Dockerfile
