#!/bin/sh

# SSL options
USE_SSL=${1:-false}
SERVER_NAME=${2:-localhost}

# Set OnEarth version and release
. ./version.sh

# Detect CPU architecture
ARCH=$(uname -m)
DOCKER_PLATFORM_OPTION=""

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    DOCKER_PLATFORM_OPTION="--platform=linux/amd64"
fi

# Start by making a docker network. This will allow us to lookup hostnames from each Docker instance
docker network create oe2

# Run onearth-time-service using port 6379 for Redis
docker run -d --rm --name onearth-time-service $DOCKER_PLATFORM_OPTION --hostname onearth-time-service --net oe2 -p 6379:6379 nasagibs/onearth-time-service:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-tile-services using port 443 for https
docker run -d --rm --name onearth-tile-services $DOCKER_PLATFORM_OPTION --hostname onearth-tile-services --net oe2 -p 443:443 \
    -v $(pwd)/certs:/home/oe2/onearth/certs -e USE_SSL=$USE_SSL -e SERVER_NAME=$SERVER_NAME \
    nasagibs/onearth-tile-services:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-capabilities using port 8081 for httpd
docker run -d --rm --name onearth-capabilities $DOCKER_PLATFORM_OPTION --hostname onearth-capabilities --net oe2 -p 8081:80 nasagibs/onearth-capabilities:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Allow other services to load before starting reproject and wms
sleep 20

# Run onearth-reproject using port 8082 for httpd
docker run -d --rm --name onearth-reproject $DOCKER_PLATFORM_OPTION --hostname onearth-reproject --net oe2 -p 8082:80 nasagibs/onearth-reproject:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-wms using port 8443 for https
docker run -d --rm --name onearth-wms $DOCKER_PLATFORM_OPTION --hostname onearth-wms --net oe2 -p 8443:443 \
    -v $(pwd)/certs:/home/oe2/onearth/certs -e USE_SSL=$USE_SSL -e SERVER_NAME=$SERVER_NAME \
    nasagibs/onearth-wms:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-demo using port 80 for httpd
docker run -d --rm --name onearth-demo $DOCKER_PLATFORM_OPTION --hostname onearth-demo --net oe2 -p 80:80 nasagibs/onearth-demo:$ONEARTH_VERSION-$ONEARTH_RELEASE