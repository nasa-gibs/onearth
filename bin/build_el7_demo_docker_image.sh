#!/bin/sh

set -e

if ! ls dist/onearth-demo-*.el7.centos.noarch.rpm >/dev/null 2>&1; then
  echo "onearth-demo RPM not found in ./dist/" >&2
  exit 1
fi

SCRIPT_NAME=$(basename "$0")
BASE_IMAGE="$1"
TAG="$2"

if [ -z "$BASE_IMAGE" ] || [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} BASE_IMAGE TAG" >&2
  exit 1
fi

rm -rf tmp/docker
mkdir -p tmp/docker/rpms
cp dist/onearth-demo-*.el7.centos.noarch.rpm tmp/docker/rpms/

echo "FROM ${BASE_IMAGE}" > tmp/docker/Dockerfile
egrep -v '^FROM ' < docker/el7-demo/Dockerfile >> tmp/docker/Dockerfile

docker build \
  --no-cache \
  --tag "$TAG" \
  tmp/docker

rm -rf tmp/docker
