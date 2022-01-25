#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
IDX_SYNC=${3:-false}
DEBUG_LOGGING=${4:-false}
S3_CONFIGS=$5

echo "[$(date)] Starting tile service" >> /var/log/onearth/config.log

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Sync IDX files if true
if [ "$IDX_SYNC" = true ]; then
    echo "[$(date)] Starting IDX file sync" >> /var/log/onearth/config.log
    python3.6 /usr/bin/oe_sync_s3_idx.py -b $S3_URL -d /onearth/idx -p epsg >>/var/log/onearth/config.log 2>&1
    python3.6 /usr/bin/oe_sync_s3_idx.py -b $S3_URL -d /onearth/idx -p oe-status >>/var/log/onearth/config.log 2>&1
    echo "[$(date)] Completed IDX file sync" >> /var/log/onearth/config.log
fi

# Set Apache logs to debug log level
if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
    perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf
fi

# Create config directories
chmod 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/

# Set up empty tiles
mkdir -p /etc/onearth/empty_tiles/

# Set up colormaps
mkdir -p /etc/onearth/colormaps/
mkdir -p /etc/onearth/colormaps/v1.0/
mkdir -p /etc/onearth/colormaps/v1.0/output
mkdir -p /etc/onearth/colormaps/v1.3/
mkdir -p /etc/onearth/colormaps/v1.3/output

# Set up legends
mkdir -p /etc/onearth/legends/

# Set up layer-metadata
mkdir -p /etc/onearth/layer-metadata/
mkdir -p /etc/onearth/layer-metadata/v1.0/

# Set up vector-metadata
mkdir -p /etc/onearth/vector-metadata/
mkdir -p /etc/onearth/vector-metadata/v1.0/

# Set up vector-styles
mkdir -p /etc/onearth/vector-styles/
mkdir -p /etc/onearth/vector-styles/v1.0/

# Copy OnEarth configs from S3 or from local samples
if [ -z "$S3_CONFIGS" ]
then
  echo "[$(date)] S3_CONFIGS not set for OnEarth configs, using sample data" >> /var/log/onearth/config.log

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/
  cp ../sample_configs/empty_tiles/* /etc/onearth/empty_tiles/
  cp -R ../sample_configs/colormaps/* /etc/onearth/colormaps/
  cp -R ../sample_configs/legends/* /etc/onearth/legends/
  cp -R ../sample_configs/layer-metadata/* /etc/onearth/layer-metadata/
  cp -R ../sample_configs/vector-metadata/* /etc/onearth/vector-metadata/
  cp -R ../sample_configs/vector-styles/* /etc/onearth/vector-styles/

  cd /home/oe2/onearth/docker/tile_services

  # Copy example Apache configs for OnEarth
  mkdir -p /var/www/html/mrf_endpoint/static_test/default/tms
  cp ../test_configs/imagery/static_test* /var/www/html/mrf_endpoint/static_test/default/tms/
  cp oe2_test_mod_mrf_static.conf /etc/httpd/conf.d
  cp ../test_configs/layers/oe2_test_mod_mrf_static_layer.config /var/www/html/mrf_endpoint/static_test/default/tms/

  mkdir -p /var/www/html/mrf_endpoint/date_test/default/tms
  cp ../test_configs/imagery/*date_test* /var/www/html/mrf_endpoint/date_test/default/tms
  cp oe2_test_mod_mrf_date.conf /etc/httpd/conf.d
  cp ../test_configs/layers/oe2_test_mod_mrf_date_layer.config /var/www/html/mrf_endpoint/date_test/default/tms/

  mkdir -p /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/{2015,2016,2017}
  cp ../test_configs/imagery/*date_test_year_dir-2015* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2015
  cp ../test_configs/imagery/*date_test_year_dir-2016* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2016
  cp ../test_configs/imagery/*date_test_year_dir-2017* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2017
  cp oe2_test_mod_mrf_date_year_dir.conf /etc/httpd/conf.d
  cp ../test_configs/layers/oe2_test_mod_mrf_date_layer_year_dir.config /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/

else
	echo "[$(date)] S3_CONFIGS set for OnEarth configs, downloading from S3" >> /var/log/onearth/config.log

  # empty tiles
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/empty_tiles/' -b $S3_CONFIGS -p empty_tiles >>/var/log/onearth/config.log 2>&1

  # colormaps
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/colormaps/v1.0' -b $S3_CONFIGS -p colormaps/v1.0 >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/colormaps/v1.3' -b $S3_CONFIGS -p colormaps/v1.3 >>/var/log/onearth/config.log 2>&1

  # legends
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/legends/' -b $S3_CONFIGS -p legends >>/var/log/onearth/config.log 2>&1
  
  # layer-metadata
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/layer-metadata/index.html' -b $S3_CONFIGS -p layer-metadata/index.html >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/layer-metadata/v1.0' -b $S3_CONFIGS -p layer-metadata/v1.0 >>/var/log/onearth/config.log 2>&1
  
  # vector-metadata
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/vector-metadata/index.html' -b $S3_CONFIGS -p vector-metadata/index.html >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/vector-metadata/v1.0' -b $S3_CONFIGS -p vector-metadata/v1.0 >>/var/log/onearth/config.log 2>&1
  
  # vector-styles
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/vector-styles/index.html' -b $S3_CONFIGS -p vector-styles/index.html >>/var/log/onearth/config.log 2>&1
  python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/vector-styles/v1.0' -b $S3_CONFIGS -p vector-styles/v1.0 >>/var/log/onearth/config.log 2>&1

  # main configs
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

# Generate Colormap HTML
ln -s /etc/onearth/colormaps /var/www/html/
for f in /etc/onearth/colormaps/v1.0/*.xml
do
  echo "Generating HTML for $f"
  base=$(basename $f)
  html=${base/"xml"/"html"}
  /usr/bin/colorMaptoHTML_v1.0.py -c $f > /etc/onearth/colormaps/v1.0/output/$html
done

for f in /etc/onearth/colormaps/v1.3/*.xml
do
  echo "Generating HTML for $f"
  base=$(basename $f)
  html=${base/"xml"/"html"}
  /usr/bin/colorMaptoHTML_v1.3.py -c $f > /etc/onearth/colormaps/v1.3/output/$html
done

echo "[$(date)] Colormap HTML generation completed" >> /var/log/onearth/config.log

# Link legends
ln -s /etc/onearth/legends /var/www/html/

# Link layer-metadata
ln -s /etc/onearth/layer-metadata /var/www/html/

# Link vector-metadata
ln -s /etc/onearth/vector-metadata /var/www/html/

# Link vector-styles
ln -s /etc/onearth/vector-styles /var/www/html/

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/oe-status.yaml /etc/onearth/config/endpoint/
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/
# Data for oe-status
mkdir -p /etc/onearth/config/layers/oe-status/
mkdir -p /onearth/idx/oe-status/Raster_Status
mkdir -p /onearth/layers/oe-status/Raster_Status
cp ../oe-status/layers/*.yaml /etc/onearth/config/layers/oe-status/
cp ../oe-status/data/*.idx /onearth/idx/oe-status/Raster_Status/
cp ../oe-status/data/*.pjg /onearth/layers/oe-status/Raster_Status/

# Create internal endpoint directories for WMTS and TWMS endpoints and configure WMTS
for f in $(grep -L 'reproject:' /etc/onearth/config/endpoint/*.yaml); do
  # WMTS Endpoint
  mkdir -p $(yq eval ".wmts_service.internal_endpoint" $f)

  # TWMS Endpoint
  mkdir -p $(yq eval ".twms_service.internal_endpoint" $f)

  python3.6 /usr/bin/oe2_wmts_configure.py $f >>/var/log/onearth/config.log 2>&1
done

echo "[$(date)] WMTS/TWMS configuration completed" >> /var/log/onearth/config.log

# Start Redis if running locally
if [ "$REDIS_HOST" = "127.0.0.1" ]; then
	echo 'Starting Redis server'
	/usr/bin/redis-server &
	sleep 2
	# Turn off the following line for production systems
	/usr/bin/redis-cli -n 0 CONFIG SET protected-mode no

	# Add time metadata to Redis for sample data
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test:default "2015-01-01"
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test:periods "2015-01-01/2017-01-01/P1Y"
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test_year_dir
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test_year_dir:default "2015-01-01"
  /usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test_year_dir:periods "2015-01-01/2017-01-01/P1Y"
fi

# Add Raster_Status time metadata to Redis for status
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:Raster_Status
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:Raster_Status:default "2004-08-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:Raster_Status:periods "2004-08-01/2004-08-01/P1M"

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