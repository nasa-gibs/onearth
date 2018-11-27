#!/bin/sh
OE_VERSION=${1:-2.2.0}

# Start by making a docker network. This will allow us to lookup hostnames from each Docker instance
docker network create oe2

# Build the onearth image
docker build --no-cache -t onearth:$OE_VERSION .

# Build the onearth-time-service image
cd time_service
docker build --no-cache -t onearth-time-service:$OE_VERSION .

# Build the onearth-wms image (not started by default)
# cd ../wms_service
# docker build --no-cache -t onearth-wms:$OE_VERSION .

# Run onearth-time-service
docker run -d --rm --name onearth-time-service --hostname onearth-time-service --net oe2 onearth-time-service:$OE_VERSION

# Run onearth using port 80 for httpd and port 6379 for Redis
docker run -d --rm --name onearth --hostname onearth --net oe2 -p 80:80 -p 6379:6379 onearth:$OE_VERSION