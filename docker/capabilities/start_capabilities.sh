#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
DEBUG_LOGGING=${3:-false}
S3_CONFIGS=$4

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Create config directories
chmod 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/layers/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
  echo "S3_CONFIGS not set for OnEarth configs, using sample data"

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/
else
  echo "S3_CONFIGS set for OnEarth configs, downloading from S3"

  python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf >>/var/log/onearth/config.log 2>&1

  # TODO Could remove `epsg` if oe-status endpoint was not in S3
  for f in $(grep -l layer_config_source /etc/onearth/config/endpoint/epsg*.yaml); do
    CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
    CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

    mkdir -p $CONFIG_SOURCE

    # WMTS Endpoint
    mkdir -p $(yq eval ".wmts_service.internal_endpoint" $f)

    # TWMS Endpoint
    mkdir -p $(yq eval ".twms_service.internal_endpoint" $f)

    python3.6 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

# Replace with S3 URL
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml # in case there is a preceding slash
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml # in case there is a preceding slash
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/* /etc/onearth/config/endpoint/

# Data for oe-status
mkdir -p /etc/onearth/config/layers/oe-status/
cp ../oe-status/layers/BlueMarble16km.yaml /etc/onearth/config/layers/oe-status/

# Make GC Service
for f in $(grep -l 'gc_service:' /etc/onearth/config/endpoint/*.yaml); do
  lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua $f >>/var/log/onearth/config.log 2>&1
done

# Set Apache logs to debug log level
if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
    perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf
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
/usr/sbin/httpd -k start
sleep 2

# Run logrotate daily at 1am
echo "0 1 * * * /etc/cron.daily/logrotate" >> /etc/crontab

# Start cron
supercronic -debug /etc/crontab > /var/log/cron_jobs.log 2>&1 &

# Tail the logs
exec tail -qFn 10000 \
 /var/log/cron_jobs.log \
  /var/log/onearth/config.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log