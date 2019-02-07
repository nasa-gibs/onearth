#!/bin/sh
OE_VERSION=${1:-2.2.1}

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

# Build the onearth-wms image
docker build --no-cache -t nasagibs/onearth-wms:$OE_VERSION ./docker/wms_service/

# Run onearth-time-service using port 6379 for Redis
docker run -d --rm --name onearth-time-service --hostname onearth-time-service --net oe2 -p 6379:6379 nasagibs/onearth-time-service:$OE_VERSION

# Run onearth-tile-services using port 80 for httpd
docker run -d --rm --name onearth-tile-services --hostname onearth-tile-services --net oe2 -p 80:80 nasagibs/onearth-tile-services:$OE_VERSION

# Run onearth-reproject using port 8081 for httpd
docker run -d --rm --name onearth-reproject --hostname onearth-reproject --net oe2 -p 8081:80 nasagibs/onearth-tile-services:$OE_VERSION

# Run onearth-wms using port 8082 for httpd
docker run -d --rm --name onearth-wms --hostname onearth-wms --net oe2 -p 8082:80 nasagibs/onearth-wms:$OE_VERSION