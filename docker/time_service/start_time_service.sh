#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
DEBUG_LOGGING=${3:-false}
FORCE_TIME_SCRAPE=${4:-false}
S3_CONFIGS=$5

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# copy config stuff
cp onearth_time_service.conf /etc/httpd/conf.d
mkdir -p /var/www/html/time_service
cp time_service.lua /var/www/html/time_service/time_service.lua
sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' /var/www/html/time_service/time_service.lua

# Set Apache logs to debug log level
if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
    perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf
fi

echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

# Create config directories
chmod -R 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/endpoint/
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

	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint  >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf  >>/var/log/onearth/config.log 2>&1

	for f in $(grep -l /etc/onearth/config/endpoint/epsg{3031,3413,4326}*.yaml); do
	  CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
	  CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

	  mkdir -p $CONFIG_SOURCE

    python3.6 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

# Replace with S3 URL
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml # in case there is a preceding slash
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml # in case there is a preceding slash
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml

# Start Redis and load sample data if running locally
if [ "$REDIS_HOST" = "127.0.0.1" ]; then
	echo 'Starting Redis server'
	/usr/bin/redis-server &
	sleep 2

	# Turn off the following line for production systems
	/usr/bin/redis-cli -n 0 CONFIG SET protected-mode no

	# Load extra sample data
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test:default "2015-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test:periods "2015-01-01/2017-01-01/P1Y"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test_year_dir
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test_year_dir:default "2015-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test_year_dir:periods "2015-01-01/2017-01-01/P1Y"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:BlueMarble16km
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:BlueMarble16km:default "2004-08-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:BlueMarble16km:periods "2004-08-01/2004-08-01/P1M"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MOGCR_LQD_143_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MOGCR_LQD_143_STD:default "2011-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MOGCR_LQD_143_STD:periods "2011-01-01/2011-01-02/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:VNGCR_LQD_I1-M4-M3_NRT
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:VNGCR_LQD_I1-M4-M3_NRT:default "2018-01-16"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:VNGCR_LQD_I1-M4-M3_NRT:periods "2018-01-16/2019-01-16/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MOG13Q4_LQD_NDVI_NRT
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MOG13Q4_LQD_NDVI_NRT:default "2018-01-01"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MOG13Q4_LQD_NDVI_NRT:periods "2018-01-01/2019-01-01/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:best:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:best:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:all:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands143_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands143_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands143_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands721_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands721_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_NDSI_Snow_Cover_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Land_Surface_Temp_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Ice_Surface_Temp_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Sea_Ice_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_Sea_Ice_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_Sea_Ice_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_Sea_Ice_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3031:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:periods "2012-09-10/2018-12-31/P1D"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3413:std:layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:MODIS_Aqua_Data_No_Data_v6_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:MODIS_Aqua_Data_No_Data_v6_STD:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:MODIS_Aqua_Data_No_Data_v6_STD:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:AMSRU2_Soil_Moisture_NPD_Day
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:AMSRU2_Soil_Moisture_NPD_Day:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:AMSRU2_Soil_Moisture_NPD_Day:periods "2012-09-10/2018-12-31/P1D"

	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:default "2012-09-10"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:periods "2012-09-10/2018-12-31/P1D"
	
	# Load custom time period configurations and generate periods
	for i in /etc/onearth/config/endpoint/epsg{3031,3413,4326}*.yaml; do
		python3 /usr/bin/oe_periods_configure.py -e "$i" -r $REDIS_HOST -g
	done

else
	# Load custom time period configurations
	for i in /etc/onearth/config/endpoint/epsg{3031,3413,4326}*.yaml; do
		python3 /usr/bin/oe_periods_configure.py -e "$i" -r $REDIS_HOST
	done

	# Load time periods by scraping S3 bucket
	if [ "$FORCE_TIME_SCRAPE" = true ]; then
		python3 /usr/bin/oe_scrape_time.py -r -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -r -t all -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -r -t best -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -r -t std -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -r -t nrt -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
	else
		python3 /usr/bin/oe_scrape_time.py -c -r -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -c -r -t all -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -c -r -t best -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -c -r -t std -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
		python3 /usr/bin/oe_scrape_time.py -c -r -t nrt -b $S3_URL $REDIS_HOST >>/var/log/onearth/config.log 2>&1
	fi
fi

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