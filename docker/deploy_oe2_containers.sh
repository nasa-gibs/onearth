#!/bin/sh

# Start by making a docker network. This will allow us to lookup hostnames from each Docker instance
docker network create oe2

docker build -t onearth .

cd date_service
docker build -t oe2-date-service .
docker run -d --name oe2-date-service --hostname oe2-date-service --net oe2 oe2-date-service
docker run --name onearth --hostname onearth --net oe2 -p 80:80 onearth