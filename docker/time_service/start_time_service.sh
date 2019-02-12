#!/bin/sh
REDIS_HOST=${1:-127.0.0.1}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# copy config stuff
cp onearth_time_service.conf /etc/httpd/conf.d
mkdir -p /var/www/html/time_service
cp time_service.lua /var/www/html/time_service/time_service.lua
sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' /var/www/html/time_service/time_service.lua

echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

# Start Redis and load sample data if running locally
if [ "$REDIS_HOST" = "127.0.0.1" ]; then
	echo 'Starting Redis server'
	/usr/bin/redis-server &
	sleep 2
	
	# Turn off the following line for production systems
	/usr/bin/redis-cli -n 0 CONFIG SET protected-mode no
	
	# Load sample data
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
	
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
	/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
	
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
fi

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log