#!/bin/sh

# Set OnEarth version and release
source ./version.sh

# Start by making a docker network. This will allow us to lookup hostnames from each Docker instance
docker network create oe2

# Run onearth-time-service using port 6379 for Redis
docker run -d --rm --name onearth-time-service --hostname onearth-time-service --net oe2 -p 6379:6379 nasagibs/onearth-time-service:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-tile-services using port 8080 for httpd
docker run -d --rm --name onearth-tile-services --hostname onearth-tile-services --net oe2 -p 8080:80 nasagibs/onearth-tile-services:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-capabilities using port 8081 for httpd
docker run -d --rm --name onearth-capabilities --hostname onearth-capabilities --net oe2 -p 8081:80 nasagibs/onearth-capabilities:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Allow other services to load before starting reproject and wms
sleep 20

# Run onearth-reproject using port 8082 for httpd
docker run -d --rm --name onearth-reproject --hostname onearth-reproject --net oe2 -p 8082:80 nasagibs/onearth-reproject:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-wms using port 8083 for httpd
docker run -d --rm --name onearth-wms --hostname onearth-wms --net oe2 -p 8083:80 nasagibs/onearth-wms:$ONEARTH_VERSION-$ONEARTH_RELEASE

# Run onearth-demo using port 80 for httpd
docker run -d --rm --name onearth-demo --hostname onearth-demo --net oe2 -p 80:80 nasagibs/onearth-demo:$ONEARTH_VERSION-$ONEARTH_RELEASE