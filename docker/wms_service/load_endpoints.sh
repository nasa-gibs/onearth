#!/bin/sh

# Refresh endpoints

python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/oe-status_reproject.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_std.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_nrt.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_all.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_best.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_std.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_nrt.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_all.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_best.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_std.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_nrt.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_all.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_best.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_nrt.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_all.yaml >>/var/log/onearth/config.log 2>&1
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_best.yaml >>/var/log/onearth/config.log 2>&1