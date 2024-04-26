#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

# Detect CPU architecture
ARCH=$(uname -m)
DOCKER_PLATFORM_OPTION=""

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    DOCKER_PLATFORM_OPTION="--platform=linux/amd64"
fi

rm -rf Dockerfile

#DOCKER_UID=$(id -u)
#DOCKER_GID=$(id -g)

cp ./docker/test/Dockerfile .

docker build \
  $DOCKER_PLATFORM_OPTION \
  --tag "$TAG" \
  ./

rm Dockerfile
