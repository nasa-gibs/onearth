#!/bin/sh

# Set OnEarth version and release
. ./version.sh

# Detect CPU architecture
ARCH=$(uname -m)
DOCKER_PLATFORM_OPTION=""

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    DOCKER_PLATFORM_OPTION="--platform=linux/amd64"
fi


# Build the onearth-tile-services image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --no-cache \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/tile_services/Dockerfile \
    -t nasagibs/onearth-tile-services:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-time-service image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --no-cache \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/time_service/Dockerfile \
    -t nasagibs/onearth-time-service:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-capabilities image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --no-cache \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/capabilities/Dockerfile \
    -t nasagibs/onearth-capabilities:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-reproject image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --no-cache \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/reproject/Dockerfile \
    -t nasagibs/onearth-reproject:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-demo image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --no-cache \
    -f ./docker/demo/Dockerfile \
    -t nasagibs/onearth-demo:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-wms image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/wms_service/Dockerfile \
    -t nasagibs/onearth-wms:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .

# Build the onearth-tools image
docker build \
    $DOCKER_PLATFORM_OPTION \
    --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
    -f ./docker/tools/Dockerfile \
    -t nasagibs/onearth-tools:$ONEARTH_VERSION-$ONEARTH_RELEASE \
    .
