#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
DEBUG_LOGGING=${3:-false}
FORCE_TIME_SCRAPE=${4:-false}
S3_CONFIGS=$5

echo "[$(date)] Starting time service" >> /var/log/onearth/config.log

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Create config directories
chmod 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "[$(date)] S3_CONFIGS not set for OnEarth configs, using sample data" >> /var/log/onearth/config.log

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/

else
	echo "[$(date)] S3_CONFIGS set for OnEarth configs, downloading from S3" >> /var/log/onearth/config.log

	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint  >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf  >>/var/log/onearth/config.log 2>&1

	for f in $(grep -L 'EPSG:3857' /etc/onearth/config/endpoint/*.yaml); do
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

# copy config stuff
mkdir -p /var/www/html/time_service
cp time_service.lua /var/www/html/time_service/time_service.lua
sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' /var/www/html/time_service/time_service.lua

# Start Redis and load sample data if running locally
if [ "$REDIS_HOST" = "127.0.0.1" ]; then
	echo 'Starting Redis server'
	/usr/bin/redis-server &
	sleep 2

	# Turn off the following line for production systems
	/usr/bin/redis-cli -n 0 CONFIG SET protected-mode no

	# Load test data
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test:default "2015-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test:periods "2015-01-01/2017-01-01/P1Y"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test_year_dir
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test_year_dir:default "2015-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test_year_dir:periods "2015-01-01/2017-01-01/P1Y"

	# Load custom time period configurations in parallel
  ls /etc/onearth/config/endpoint/epsg{3031,3413,4326}*.yaml | parallel -j 4 python3 /usr/bin/oe_periods_configure.py -e "{}" -r $REDIS_HOST -g >> /var/log/onearth/config.log 2>&1

else
  # Load custom time period configurations in parallel
  grep -L 'EPSG:3857' /etc/onearth/config/endpoint/epsg*.yaml | parallel -j 4 python3 /usr/bin/oe_periods_configure.py -e "{}" -r $REDIS_HOST >> /var/log/onearth/config.log 2>&1
fi

# Load time periods by scraping S3 bucket, if requested
if [ "$FORCE_TIME_SCRAPE" = true ]; then
	python3 /usr/bin/oe_scrape_time.py -r -b $S3_URL $REDIS_HOST >> /var/log/onearth/config.log 2>&1
fi

# Load oe-status data
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:Raster_Status
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:Raster_Status:default "2004-08-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:Raster_Status:periods "2004-08-01/2004-08-01/P1M"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:Vector_Status
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:Vector_Status:default "2021-07-03"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:Vector_Status:periods "2021-07-03/2021-07-03/P1D"

echo "[$(date)] Time service configuration completed" >> /var/log/onearth/config.log

# Configure and startup apache
cp onearth_time_service.conf /etc/httpd/conf.d

if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
    perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf
fi

echo "[$(date)] Starting Apache server" >> /var/log/onearth/config.log
/usr/sbin/apachectl
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