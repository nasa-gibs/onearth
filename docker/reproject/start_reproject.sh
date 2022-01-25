#!/bin/sh
DEBUG_LOGGING=${1:-false}
TILES_HEALTHCHECK=${2:-http://172.17.0.1/oe-status/Raster_Status/default/2004-08-01/16km/0/0/0.jpeg}
GC_HEALTHCHECK=${3:-http://172.17.0.1/oe-status/1.0.0/WMTSCapabilities.xml}
S3_CONFIGS=$4

echo "[$(date)] Starting reproject service" >> /var/log/onearth/config.log

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

cd /home/oe2/onearth/docker/reproject

# Create config directories
mkdir -p /onearth
chmod 755 /onearth
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/layers/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
  echo "[$(date)] S3_CONFIGS not set for OnEarth configs, using sample data" >> /var/log/onearth/config.log

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/

  # Load test layers
  mkdir -p /var/www/html/reproject_endpoint/date_test/default/tms
  cp oe2_test_mod_reproject_date.conf /etc/httpd/conf.d
  cp ../test_configs/layers/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/date_test/default/tms/oe2_test_mod_reproject_date_layer_source.config
  cp ../test_configs/layers/oe2_test_mod_reproject_date*.config /var/www/html/reproject_endpoint/date_test/default/tms/

  mkdir -p /var/www/html/reproject_endpoint/static_test/default/tms
  cp oe2_test_mod_reproject_static.conf /etc/httpd/conf.d
  cp ../test_configs/layers/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/static_test/default/tms/oe2_test_mod_reproject_static_layer_source.config
  cp ../test_configs/layers/oe2_test_mod_reproject_static*.config /var/www/html/reproject_endpoint/static_test/default/tms/

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

echo "[$(date)] OnEarth configs copy/download completed" >> /var/log/onearth/config.log

# Copy tilematrixsets config file
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

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

# Turn off indexes
<Location />
      Options -Indexes
</Location>
EOS

# Copy oe-status layers
mkdir -p /etc/onearth/config/layers/oe-status/
cp ../oe-status/layers/*.yaml /etc/onearth/config/layers/oe-status/

# Now configure oe-status and start apache for reproject health checks
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/
mkdir -p $(yq eval ".twms_service.internal_endpoint" /etc/onearth/config/endpoint/oe-status_reproject.yaml)
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/oe-status_reproject.yaml >>/var/log/onearth/config.log 2>&1

echo "[$(date)] Starting Apache server" >> /var/log/onearth/config.log
/usr/sbin/httpd -k restart
sleep 2

# Wait for GC and Tile services to be ready
time_out=600
echo "[$(date)] Begin checking $GC_HEALTHCHECK and $TILES_HEALTHCHECK endpoints...">>/var/log/onearth/config.log 2>&1;
while [[ "$(curl -s -m 10 -o /dev/null -w ''%{http_code}'' "$TILES_HEALTHCHECK")" != "200" || 
         "$(curl -s -m 15 -o /dev/null -w ''%{http_code}'' "$GC_HEALTHCHECK")" != "200" ]]; do 
  if [[ $time_out -lt 0 ]]; then
    echo "[$(date)] ERROR: Timed out waiting for endpoint $GC_HEALTHCHECK or $TILES_HEALTHCHECK">>/var/log/onearth/config.log 2>&1;
    /usr/sbin/httpd stop; cat /var/log/onearth/config.log; exit 1;
  else
  	echo "[$(date)] Waiting for $GC_HEALTHCHECK or $TILES_HEALTHCHECK endpoints...">>/var/log/onearth/config.log 2>&1;
  	sleep 5; #curl in 5 second intervals
  	time_out=$(($time_out-5));
  fi
done

echo "[$(date)] Completed healthcheck wait" >> /var/log/onearth/config.log

# Load additional endpoints
echo "[$(date)] Loading additional endpoints" >> /var/log/onearth/config.log

# Create reproject configuration directories
for f in $(grep -l 'reproject:' /etc/onearth/config/endpoint/*.yaml); do
  # WMTS Endpoint
  mkdir -p $(yq eval ".wmts_service.internal_endpoint" $f)

  # TWMS Endpoint
  mkdir -p $(yq eval ".twms_service.internal_endpoint" $f)
done

# Run endpoint configuration in parallel
grep -l 'reproject:' /etc/onearth/config/endpoint/*.yaml | parallel -j 4 python3.6 /usr/bin/oe2_reproject_configure.py {} >>/var/log/onearth/config.log 2>&1

echo "[$(date)] Completed reproject configuration" >> /var/log/onearth/config.log

echo "[$(date)] Restarting Apache server" >> /var/log/onearth/config.log
/usr/sbin/httpd -k restart
sleep 2

# Run logrotate hourly
echo "0 * * * * /etc/cron.hourly/logrotate" >> /etc/crontab

# Start cron
supercronic -debug /etc/crontab > /var/log/cron_jobs.log 2>&1 &

# Tail the logs
exec tail -qFn 10000 \
  /var/log/cron_jobs.log \
  /var/log/onearth/config.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log