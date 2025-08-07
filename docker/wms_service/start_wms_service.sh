#!/bin/sh
ENDPOINT_REFRESH=$1 # Interval for refreshing the WMS endpoints in minutes
GC_HEALTHCHECK=${2:-http://onearth-tile-services/oe-status/1.0.0/WMTSCapabilities.xml}
S3_CONFIGS=$3
SHAPEFILE_SYNC=${4:-false}
USE_LOCAL_SHAPEFILES=${5:-false}
SERVER_STATUS=${6:-false}
USE_SSL=${7:-false}
SERVER_NAME=${8:-localhost}

echo "[$(date)] Starting wms service" >> /var/log/onearth/config.log

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

mkdir -p /etc/onearth/config/mapserver/
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/
mkdir -p /etc/onearth/mapfile-styles/

# Data for oe-status
mkdir -p /onearth/shapefiles/oe-status/Vector_Status/2021
cp ../oe-status/data/shapefiles/* /onearth/shapefiles/oe-status/Vector_Status/2021/
cp ../sample_configs/mapfile-styles/Vector_Status.txt /etc/onearth/mapfile-styles/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "[$(date)] S3_CONFIGS not set for OnEarth configs, checking for local configs" >> /var/log/onearth/config.log

  # Check if configs are already mounted (local development)
  # Look for any YAML endpoint config to detect local setup
  LOCAL_CONFIGS=$(find /etc/onearth/config/endpoint/ -name "*.yaml" 2>/dev/null | head -1)
  if [ -z "$LOCAL_CONFIGS" ]; then
    echo "[$(date)] No local configs detected, using sample data" >> /var/log/onearth/config.log
    # Copy sample configs
    cp ../sample_configs/mapserver/* /etc/onearth/config/mapserver/
    cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
    cp -R ../sample_configs/layers/* /etc/onearth/config/layers/
    cp -R ../sample_configs/mapfile-styles/* /etc/onearth/mapfile-styles/
  else
    echo "[$(date)] Local configs detected, skipping sample config copy" >> /var/log/onearth/config.log
    # Only copy conf files if they don't exist (needed for tilematrixsets.xml, etc.)
    find ../sample_configs/conf/ -name "*.xml" -exec sh -c 'test ! -f "/etc/onearth/config/conf/$(basename "$1")" && cp "$1" "/etc/onearth/config/conf/"' _ {} \; 2>/dev/null || true
    # Copy mapfile-styles if they don't exist
    find ../sample_configs/mapfile-styles/ -name "*" -exec sh -c 'test ! -f "/etc/onearth/mapfile-styles/$(basename "$1")" && cp "$1" "/etc/onearth/mapfile-styles/"' _ {} \; 2>/dev/null || true
  fi
else
	echo "[$(date)] S3_CONFIGS set for OnEarth configs, downloading from S3" >> /var/log/onearth/config.log

	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/mapserver/' -b $S3_CONFIGS -p config/mapserver >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/mapfile-styles/' -b $S3_CONFIGS -p mapfile-styles >>/var/log/onearth/config.log 2>&1
  # layer configs are endpoint specific
  for f in $(grep -L 'reproject:' /etc/onearth/config/endpoint/*.yaml); do
    CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
    CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

    mkdir -p $CONFIG_SOURCE

    python3 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

echo "[$(date)] OnEarth configs copy/download completed" >> /var/log/onearth/config.log

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/
mkdir -p $(yq eval ".layer_config_source" /etc/onearth/config/endpoint/oe-status_reproject.yaml)
cp ../oe-status/layers/* $(yq eval ".layer_config_source" /etc/onearth/config/endpoint/oe-status_reproject.yaml)/
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

  REDIRECT_ENDPOINT=$(yq eval ".mapserver.redirect_endpoint" $f)
  # Redirect Endpoint
  mkdir -p $REDIRECT_ENDPOINT

  cp /var/www/cgi-bin/mapserv.fcgi ${REDIRECT_ENDPOINT}/wms.cgi
done

time_out=600
echo "[$(date)] Begin checking $GC_HEALTHCHECK endpoint...">>/var/log/onearth/config.log 2>&1;
while [[ "$(curl -s -m 60 -o /dev/null -w ''%{http_code}'' "$GC_HEALTHCHECK")" != "200" ]]; do 
  if [[ $time_out -le 0 ]]; then
	echo "[$(date)] ERROR: Timed out waiting for endpoint">>/var/log/onearth/config.log 2>&1;
  cat /var/log/onearth/config.log; exit 1;
  else 
  	echo "[$(date)] Waiting for $GC_HEALTHCHECK endpoints...">>/var/log/onearth/config.log 2>&1;
  	sleep 60; #curl in 60 second intervals
  	time_out=$(($time_out-60));
  fi
done

echo "[$(date)] Completed healthcheck wait" >> /var/log/onearth/config.log

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
if [ "$SERVER_STATUS" = true ]; then
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
fi

# Comment out welcome.conf
sed -i -e 's/^\([^#].*\)/# \1/g' /etc/httpd/conf.d/welcome.conf

# Disable fancy indexing
sed -i -e '/^Alias \/icons\/ "\/usr\/share\/httpd\/icons\/"$/,/^<\/Directory>$/s/^/#/' /etc/httpd/conf.d/autoindex.conf

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

# Build wms_time service endpoints in parallel
grep -l 'mapserver:' /etc/onearth/config/endpoint/*.yaml | parallel -j 4 lua /home/oe2/onearth/src/modules/wms_time_service/make_wms_time_endpoint.lua >>/var/log/onearth/config.log 2>&1

if [ "$USE_SSL" = true ]; then
  cp /home/oe2/onearth/certs/* /etc/pki/tls/private/
  sed -i -e 's/SSLPassPhraseDialog/#SSLPassPhraseDialog/g' /etc/httpd/conf.d/ssl.conf
  sed -i -e 's/ServerName localhost/ServerName '"$SERVER_NAME"'/g' /etc/httpd/conf.d/oe2_ssl.conf
else
  rm -f /etc/httpd/conf.d/oe2_ssl.conf
fi

echo "[$(date)] Restarting Apache server" >> /var/log/onearth/config.log
/usr/sbin/httpd -k start
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