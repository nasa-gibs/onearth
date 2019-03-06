#!/bin/sh
OE_VERSION=${1:-2.2.1}
REDIS_HOST=onearth-time-service

# Start by making a docker network. This will allow us to lookup hostnames from each Docker instance
docker network create oe2

# Build the onearth-tile-services image
cp ./docker/tile_services/Dockerfile .
docker build --no-cache -t nasagibs/onearth-tile-services:$OE_VERSION .
rm Dockerfile

# Build the onearth-time-service image
cp ./docker/time_service/Dockerfile .
docker build --no-cache -t nasagibs/onearth-time-service:$OE_VERSION .
rm Dockerfile

# Build the onearth-capabilities image
cp ./docker/capabilities/Dockerfile .
docker build --no-cache -t nasagibs/onearth-capabilities:$OE_VERSION .
rm Dockerfile

# Build the onearth-reproject image
cp ./docker/reproject/Dockerfile .
docker build --no-cache -t nasagibs/onearth-reproject:$OE_VERSION .
rm Dockerfile

# Build the onearth-demo image
cp ./docker/demo/Dockerfile .
docker build --no-cache -t nasagibs/onearth-demo:$OE_VERSION .
rm Dockerfile

# Build the onearth-wms image
docker build --no-cache -t nasagibs/onearth-wms:$OE_VERSION ./docker/wms_service/

# Build the onearth-tools image
docker build --no-cache -t nasagibs/onearth-tools:$OE_VERSION ./docker/tools/

# Run onearth-time-service using port 6379 for Redis
docker run -d --rm --name onearth-time-service --hostname onearth-time-service --net oe2 -p 6379:6379 nasagibs/onearth-time-service:$OE_VERSION

# Run onearth-tile-services using port 8080 for httpd
docker run -d --rm --name onearth-tile-services --hostname onearth-tile-services --net oe2 -p 8080:80 nasagibs/onearth-tile-services:$OE_VERSION

# Run onearth-capabilities using port 8081 for httpd
docker run -d --rm --name onearth-capabilities --hostname onearth-capabilities --net oe2 -p 8081:80 nasagibs/onearth-capabilities:$OE_VERSION

# Allow other services to load before starting reproject and wms
sleep 20

# Run onearth-reproject using port 8082 for httpd
docker run -d --rm --name onearth-reproject --hostname onearth-reproject --net oe2 -p 8082:80 nasagibs/onearth-reproject:$OE_VERSION

# Run onearth-wms using port 8083 for httpd
docker run -d --rm --name onearth-wms --hostname onearth-wms --net oe2 -p 8083:80 nasagibs/onearth-wms:$OE_VERSION

# Run onearth-demo using port 80 for httpd
docker run -d --rm --name onearth-demo --hostname onearth-demo --net oe2 -p 80:80 nasagibs/onearth-demo:$OE_VERSION