#!/bin/sh
S3_CONFIGS=$1
ENDPOINT_REFRESH=$2 # Interval for refreshing the WMS endpoints in minutes
TILES_HEALTHCHECK=${3:-http://172.17.0.1/oe-status/BlueMarble16km/default/2004-08-01/16km/0/0/0.jpeg}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

mkdir -p /etc/onearth/config/mapserver/
mkdir -p /etc/onearth/config/endpoint/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "S3_CONFIGS not set for OnEarth configs, using sample data"

  # Copy sample configs
  cp ../sample_configs/mapserver/* /etc/onearth/config/mapserver/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
else
	echo "S3_CONFIGS set for OnEarth configs, downloading from S3"

	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/mapserver/' -b $S3_CONFIGS -p config/mapserver >>/var/log/onearth/config.log 2>&1
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
fi

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/
mkdir -p $(yq eval ".twms_service.internal_endpoint" /etc/onearth/config/endpoint/oe-status_reproject.yaml)
cp ../oe-status/mapserver/oe-status_reproject.header /etc/onearth/config/mapserver/

# Copy tilematrixsets config file
mkdir -p /etc/onearth/config/conf/
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Create endpoints
cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi

for f in $(grep -l mapserver /etc/onearth/config/endpoint/*.yaml); do
  INTERNAL_ENDPOINT=$(yq eval ".mapserver.internal_endpoint" $f)
  # WMS Endpoint
  mkdir -p $INTERNAL_ENDPOINT

  cp /var/www/cgi-bin/mapserv.fcgi ${INTERNAL_ENDPOINT}/wms.cgi
done

time_out=60
echo "checking $TILES_HEALTHCHECK endpoint...">>/var/log/onearth/config.log 2>&1; 
while [[ "$(curl -s -m 3 -o /dev/null -w ''%{http_code}'' "$TILES_HEALTHCHECK")" != "200" ]]; do 
  if [[ $time_out -lt 0 ]]; then
	echo "ERROR: Timed out waiting for endpoint">>/var/log/onearth/config.log 2>&1; break;
  else 
  	echo "waiting for $TILES_HEALTHCHECK endpoints...">>/var/log/onearth/config.log 2>&1; 
  	sleep 5; #curl in 5 second intervals
  	time_out=$(($time_out-5));
  fi
done

# Make endpoint configurations
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

# Setup Apache with no-cache
cat >> /etc/httpd/conf/httpd.conf <<EOS

#
# Turn off caching
#
Header Set Pragma "no-cache"
Header Set Expires "Thu, 1 Jan 1970 00:00:00 GMT"
Header Set Cache-Control "max-age=0, no-store, no-cache, must-revalidate"
Header Unset ETag
FileETag None
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