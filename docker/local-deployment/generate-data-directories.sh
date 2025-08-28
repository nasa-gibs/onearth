#!/bin/bash

# Always create directories in docker/local-deployment, regardless of where script is run from
if [[ "$(pwd)" == */docker/local-deployment ]]; then
    # Running from docker/local-deployment directory
    TARGET_DIR="."
else
    # Running from elsewhere, target the docker/local-deployment directory
    TARGET_DIR="docker/local-deployment"
fi

mkdir -p "$TARGET_DIR/downloaded-onearth-configs/config/layers/epsg4326/all/"
mkdir -p "$TARGET_DIR/downloaded-onearth-configs/config/layers/epsg3031/all/"
mkdir -p "$TARGET_DIR/downloaded-onearth-configs/config/layers/epsg3413/all/"
mkdir -p "$TARGET_DIR/downloaded-onearth-configs/config/layers/epsg3857/all/"

mkdir -p "$TARGET_DIR/local-mrf-archive/epsg4326/"
mkdir -p "$TARGET_DIR/local-mrf-archive/epsg3031/"
mkdir -p "$TARGET_DIR/local-mrf-archive/epsg3413/"
mkdir -p "$TARGET_DIR/local-mrf-archive/epsg3857/"

mkdir -p "$TARGET_DIR/local-shp-archive/epsg4326/"
mkdir -p "$TARGET_DIR/local-shp-archive/epsg3031/"
mkdir -p "$TARGET_DIR/local-shp-archive/epsg3413/"
mkdir -p "$TARGET_DIR/local-shp-archive/epsg3857/"