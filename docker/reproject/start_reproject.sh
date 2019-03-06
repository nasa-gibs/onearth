#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

cd /home/oe2/onearth/docker/reproject

# Load test layers
mkdir -p /var/www/html/reproject_endpoint/date_test/default/tms
cp oe2_test_mod_reproject_date.conf /etc/httpd/conf.d
cp ../layer_configs/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/date_test/default/tms/oe2_test_mod_reproject_date_layer_source.config
cp ../layer_configs/oe2_test_mod_reproject_date*.config /var/www/html/reproject_endpoint/date_test/default/tms/

mkdir -p /var/www/html/reproject_endpoint/static_test/default/tms
cp oe2_test_mod_reproject_static.conf /etc/httpd/conf.d
cp ../layer_configs/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/static_test/default/tms/oe2_test_mod_reproject_static_layer_source.config
cp ../layer_configs/oe2_test_mod_reproject_static*.config /var/www/html/reproject_endpoint/static_test/default/tms/

# WMTS endpoints
mkdir -p /var/www/html/oe-status_reproject/
mkdir -p /var/www/html/profiler_reproject/
mkdir -p /var/www/html/wmts/epsg3857/all
mkdir -p /var/www/html/wmts/epsg3857/best
mkdir -p /var/www/html/wmts/epsg3857/std
mkdir -p /var/www/html/wmts/epsg3857/nrt

# TWMS endpoints
mkdir -p /var/www/html/twms/epsg3857/all
mkdir -p /var/www/html/twms/epsg3857/best
mkdir -p /var/www/html/twms/epsg3857/std
mkdir -p /var/www/html/twms/epsg3857/nrt

# Copy sample configs
mkdir -p /onearth
chmod -R 755 /onearth
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/conf/
cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Run reproject config tools
sleep 10
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/oe-status_reproject.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/profiler_reproject.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_best.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_all.yaml

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log