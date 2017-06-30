#!/bin/sh

set -evx

SCRIPT_NAME=$(basename "$0")
GIBS_GDAL_DOCKER_IMAGE="$1"
TAG="$2"

if [ -z "$GIBS_GDAL_DOCKER_IMAGE" ]; then
  echo "Usage: ${SCRIPT_NAME} GIBS_GDAL_DOCKER_IMAGE TAG" >&2
  exit 1
fi

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} GIBS_GDAL_DOCKER_IMAGE TAG" >&2
  exit 1
fi

rm -rf tmp/docker
mkdir -p tmp/docker/rpms
cp dist/onearth-*.el7.*.rpm tmp/docker/rpms/
cp docker/el7/run-onearth.sh tmp/docker/run-onearth.sh
echo "FROM ${GIBS_GDAL_DOCKER_IMAGE}" > tmp/docker/Dockerfile
grep -Ev '^FROM' docker/el7/Dockerfile >> tmp/docker/Dockerfile

(
  set -evx
  cd tmp/docker
  docker build -t "$TAG" .
)

rm -rf tmp/docker
