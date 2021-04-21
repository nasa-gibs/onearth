#!/bin/sh

set -e

if ! ls dist/onearth-*.el8.*.rpm >/dev/null 2>&1; then
  echo "No RPMs found in ./dist/" >&2
  exit 1
fi

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

rm -rf tmp/docker
mkdir -p tmp/docker/rpms
cp dist/onearth-*.rpm tmp/docker/rpms/
cp docker/el8/run-onearth.sh tmp/docker/run-onearth.sh
cp docker/el8/pip-requirements.txt tmp/docker/pip-requirements.txt

BASE_IMAGE="centos:8"
echo "FROM ${BASE_IMAGE}" > tmp/docker/Dockerfile
egrep -v '^FROM ' < docker/el8/Dockerfile >> tmp/docker/Dockerfile

docker build \
  --no-cache \
  --tag "$TAG" \
  tmp/docker

rm -rf tmp/docker
