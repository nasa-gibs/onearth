#!/bin/sh

# Refresh endpoints
for f in $(grep -l mapserver /etc/onearth/config/endpoint/*.yaml); do
  python3.6 /usr/bin/oe2_wms_configure.py $f "${SHAPEFILE_BUCKET}" >>/var/log/onearth/config.log 2>&1
done