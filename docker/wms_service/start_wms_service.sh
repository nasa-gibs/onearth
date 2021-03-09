#!/bin/sh
S3_CONFIGS=$1
ENDPOINT_REFRESH=$2 # Interval for refreshing the WMS endpoints in minutes

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
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/mapserver/' -b $S3_CONFIGS -p config/mapserver >>/var/log/onearth/config.log 2>&1
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
fi

# Copy tilematrixsets config file
mkdir -p /etc/onearth/config/conf/
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Create endpoints
cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi
mkdir -p /var/www/html/wms/oe-status_reproject
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
cp /var/www/cgi-bin/mapserv.fcgi /var/www/html/wms/oe-status_reproject/wms.cgi
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

# Set up cron job for refreshing endpoints
if [ -z "$ENDPOINT_REFRESH" ]
then
	echo "ENDPOINT_REFRESH not set...using default of 60 minutes"
	echo "*/58 * * * * /home/oe2/onearth/docker/wms_service/load_endpoints.sh" >> /etc/crontab
else
	echo "*/$ENDPOINT_REFRESH * * * * /home/oe2/onearth/docker/wms_service/load_endpoints.sh" >> /etc/crontab
fi

# Setup Apache extended server status
cat >> /etc/httpd/conf/httpd.conf <<EOS
LoadModule status_module modules/mod_status.so

<Location /server-status>
   SetHandler server-status
   Allow from all 
</Location>

# ExtendedStatus controls whether Apache will generate "full" status
# information (ExtendedStatus On) or just basic information (ExtendedStatus
# Off) when the "server-status" handler is called. The default is Off.
#
ExtendedStatus On
EOS

echo 'Starting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Run logrotate hourly
echo "0 * * * * /etc/cron.hourly/logrotate" >> /etc/crontab

# Start cron
supercronic -debug /etc/crontab > /var/log/cron_jobs.log 2>&1 &

# Tail the logs
exec tail -qFn 1000 \
  /var/log/cron_jobs.log \
  /var/log/onearth/config.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log