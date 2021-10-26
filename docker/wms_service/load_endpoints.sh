#!/bin/sh

echo "[$(date)] Beginning WMS endpoint configuration..." >> /var/log/onearth/config.log

if [ -z "$SHAPEFILE_BUCKET" ]
then
	grep -l mapserver /etc/onearth/config/endpoint/*.yaml | parallel -j 4 python3.6 /usr/bin/oe2_wms_configure.py {} >> /var/log/onearth/config.log 2>&1
else
	grep -l mapserver /etc/onearth/config/endpoint/*.yaml | parallel -j 4 python3.6 /usr/bin/oe2_wms_configure.py {} --shapefile_bucket "${SHAPEFILE_BUCKET}" >> /var/log/onearth/config.log 2>&1
fi
echo "[$(date)] Completed WMS endpoint configuration" >> /var/log/onearth/config.log