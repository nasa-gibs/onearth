#!/bin/sh

echo "[$(date)] Beginning WMS endpoint configuration..." >> /var/log/onearth/config.log

# Refresh endpoints
for f in $(grep -l mapserver /etc/onearth/config/endpoint/*.yaml); do
  python3.6 /usr/bin/oe2_wms_configure.py $f --shapefile_bucket "${SHAPEFILE_BUCKET}" >>/var/log/onearth/config.log 2>&1
done

echo "[$(date)] Completed WMS endpoint configuration" >> /var/log/onearth/config.log