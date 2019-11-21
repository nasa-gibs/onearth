#!/bin/sh
DEBUG_LOGGING=${1:-false}
S3_CONFIGS=$2

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

# Create config directories
mkdir -p /onearth
chmod -R 755 /onearth
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/conf/

# Copy sample configs
cp ../sample_configs/conf/* /etc/onearth/config/conf/
cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "S3_CONFIGS not set"
else
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf
fi

# Copy tilematrixsets config file
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Run reproject config tools
sleep 10
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/oe-status_reproject.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/profiler_reproject.yaml

# Set Apache logs to debug log level
if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
    perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf
fi

echo 'Starting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Load additional endpoints
echo 'Loading additional endpoints'
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_best.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_all.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_nrt.yaml

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Tail the apache logs
crond
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log