#!/bin/sh

# Refresh endpoints

python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_std.yaml
#python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_nrt.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_all.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg4326_best.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_std.yaml
#python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_nrt.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_all.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3031_best.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_std.yaml
#python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_nrt.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_all.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3413_best.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml
#python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_nrt.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_all.yaml
python3.6 /usr/bin/oe2_wms_configure.py /etc/onearth/config/endpoint/epsg3857_best.yaml