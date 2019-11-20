#!/bin/sh
S3_CONFIGS=$1

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Copy sample configs
mkdir -p /etc/onearth/config/mapserver/
cp ../sample_configs/mapserver/* /etc/onearth/config/mapserver/
mkdir -p /etc/onearth/config/endpoint/
cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "S3_CONFIGS not set for OnEarth configs"
else
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/mapserver/' -b $S3_CONFIGS -p config/mapserver
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint
fi

# Copy tilematrixsets config file
mkdir -p /etc/onearth/config/conf/
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Create endpoints
cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi
mkdir -p /var/www/html/wms/epsg4326/std
mkdir -p /var/www/html/wms/epsg4326/nrt
mkdir -p /var/www/html/wms/epsg4326/all
mkdir -p /var/www/html/wms/epsg4326/best
mkdir -p /var/www/html/wms/epsg3031/std
mkdir -p /var/www/html/wms/epsg3031/nrt
mkdir -p /var/www/html/wms/epsg3031/all
mkdir -p /var/www/html/wms/epsg3031/best
mkdir -p /var/www/html/wms/epsg3413/std
mkdir -p /var/www/html/wms/epsg3413/nrt
mkdir -p /var/www/html/wms/epsg3413/all
mkdir -p /var/www/html/wms/epsg3413/best
mkdir -p /var/www/html/wms/epsg3857/std
mkdir -p /var/www/html/wms/epsg3857/nrt
mkdir -p /var/www/html/wms/epsg3857/all
mkdir -p /var/www/html/wms/epsg3857/best
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg4326/std/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg4326/nrt/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg4326/all/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg4326/best/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3031/std/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3031/nrt/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3031/all/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3031/best/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3413/std/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3413/nrt/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3413/all/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3413/best/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3857/std/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3857/nrt/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3857/all/wms.cgi
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/epsg3857/best/wms.cgi

# Make endpoint configurations
sleep 20
sh load_endpoints.sh

echo 'Starting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Tail the apache logs
crond
exec tail -qF \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log