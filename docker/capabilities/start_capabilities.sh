#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
DEBUG_LOGGING=${3:-false}
S3_CONFIGS=$4

echo "[$(date)] Starting capabilities service" >> /var/log/onearth/config.log

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

# Copy OnEarth configs from S3 or from local samples
if [ -z "$S3_CONFIGS" ]
then
  echo "[$(date)] S3_CONFIGS not set for OnEarth configs, using sample data" >> /var/log/onearth/config.log

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/

  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/
else
  echo "[$(date)] S3_CONFIGS set for OnEarth configs, downloading from S3" >> /var/log/onearth/config.log

  python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf >>/var/log/onearth/config.log 2>&1

  for f in $(grep -L 'reproject:' /etc/onearth/config/endpoint/*.yaml); do
    CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
    CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

    mkdir -p $CONFIG_SOURCE

    python3.6 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

# Replace with S3 URL
find /etc/onearth/config/layers/ -type f -name "*.yaml" -exec sed -i -e 's@/{S3_URL}@'$S3_URL'@g' {} \; # in case there is a preceding slash
find /etc/onearth/config/layers/ -type f -name "*.yaml" -exec sed -i -e 's@{S3_URL}@'$S3_URL'@g' {} \;

echo "[$(date)] OnEarth configs copy/download completed" >> /var/log/onearth/config.log

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/oe-status.yaml /etc/onearth/config/endpoint/
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/

# Data for oe-status
mkdir -p /etc/onearth/config/layers/oe-status/
cp ../oe-status/layers/*.yaml /etc/onearth/config/layers/oe-status/

# Create internal endpoint directories for WMTS and TWMS endpoints and build the GC services
for f in $(grep -l 'gc_service:' /etc/onearth/config/endpoint/*.yaml); do
  # WMTS Endpoint
  mkdir -p $(yq eval ".wmts_service.internal_endpoint" $f)

  # TWMS Endpoint
  mkdir -p $(yq eval ".twms_service.internal_endpoint" $f)

  lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua $f >>/var/log/onearth/config.log 2>&1
done

echo "[$(date)] GC endpoint configuration completed" >> /var/log/onearth/config.log

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

# Setup Apache to cache for 10 minutes
cat >> /etc/httpd/conf/httpd.conf <<EOS

#
# Turn on caching for 10 minutes
#
Header Always Set Cache-Control "public, max-age=600"
EOS

echo "[$(date)] Starting Apache server" >> /var/log/onearth/config.log
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