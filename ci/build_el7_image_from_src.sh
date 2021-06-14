#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

rm -rf Dockerfile

#DOCKER_UID=$(id -u)
#DOCKER_GID=$(id -g)

cp ./docker/test/Dockerfile .

source ./version.sh

docker build \
  --tag "$TAG" \
  --no-cache \
  --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
  ./

rm Dockerfile
