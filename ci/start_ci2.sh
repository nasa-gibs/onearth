#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

source ../version.sh

cp httpd.conf /etc/httpd/conf/
mkdir -p /build/test/ci_tests

# Copy time_service config
cp ../docker/time_service/onearth_time_service.conf /etc/httpd/conf.d
sed -i 's@/var/www/html@/build/test/ci_tests@g' /etc/httpd/conf.d/onearth_time_service.conf
mkdir -p /build/test/ci_tests/time_service/
cp ../docker/time_service/time_service.lua /build/test/ci_tests/time_service/
sed -i 's@{REDIS_HOST}@'127.0.0.1'@g' /build/test/ci_tests/time_service/time_service.lua

# Configs for services
mkdir -p /etc/onearth/config/conf/
cp ../src/modules/gc_service/conf/* /etc/onearth/config/conf/
mkdir -p /etc/onearth/empty_tiles/
cp ../docker/sample_configs/empty_tiles/* /etc/onearth/empty_tiles/
mkdir -p /etc/onearth/config/mapserver/
cp ../src/test/mapserver_test_data/test.header /etc/onearth/config/mapserver/
mkdir -p /build/test/ci_tests/wms/test
cp /var/www/cgi-bin/mapserv.fcgi /build/test/ci_tests/wms/test/wms.cgi
cp ../docker/wms_service/template.map .

mkdir -p /build/test/ci_tests/mapserver/test
cp /var/www/cgi-bin/mapserv.fcgi /build/test/ci_tests/mapserver/test/wms.cgi

python3.6 /usr/bin/oe2_wmts_configure.py ../src/test/mapserver_test_data/test_endpoint.yaml
lua ../src/modules/gc_service/make_gc_endpoint.lua ../src/test/mapserver_test_data/test_endpoint.yaml
lua /home/oe2/onearth/src/modules/wms_time_service/make_wms_time_endpoint.lua ../src/test/mapserver_test_data/test.yaml

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

echo 'Starting Redis server'
/usr/bin/redis-server &
sleep 2

# Add some test data to redis for tests
/usr/bin/redis-cli  -n 0 DEL layer:test_daily_png
/usr/bin/redis-cli  -n 0 SET layer:test_daily_png:default "2012-02-29"
/usr/bin/redis-cli  -n 0 SADD layer:test_daily_png:periods "2012-02-29/2012-02-29/P1D"
/usr/bin/redis-cli  -n 0 DEL layer:test_legacy_subdaily_jpg
/usr/bin/redis-cli  -n 0 SET layer:test_legacy_subdaily_jpg:default "2012-02-29T14:00:00Z"
/usr/bin/redis-cli  -n 0 SADD layer:test_legacy_subdaily_jpg:periods "2012-02-29T12:00:00Z/2012-02-29T14:00:00Z/PT2H"
/usr/bin/redis-cli  -n 0 DEL layer:test_nonyear_jpg
/usr/bin/redis-cli  -n 0 SET layer:test_nonyear_jpg:default "2012-02-29"
/usr/bin/redis-cli  -n 0 SADD layer:test_nonyear_jpg:periods "2012-02-29/2012-02-29/P1D"
/usr/bin/redis-cli  -n 0 DEL layer:test_weekly_jpg
/usr/bin/redis-cli  -n 0 SET layer:test_weekly_jpg:default "2012-02-29"
/usr/bin/redis-cli  -n 0 SADD layer:test_weekly_jpg:periods "2012-02-22/2012-02-29/P7D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_1a
/usr/bin/redis-cli  -n 0 SET layer:snap_test_1a:default "2016-02-29"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_1a:periods "2015-01-01/2016-12-31/P1D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_2a
/usr/bin/redis-cli  -n 0 SET layer:snap_test_2a:default "2015-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_2a:periods "2015-01-01/2015-01-10/P1D"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_2a:periods "2015-01-12/2015-01-31/P1D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_3a
/usr/bin/redis-cli  -n 0 SET layer:snap_test_3a:default "2015-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_3a:periods "2015-01-01/2016-01-01/P1M"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_3a:periods "1948-01-01/1948-03-01/P1M"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_3b
/usr/bin/redis-cli  -n 0 SET layer:snap_test_3b:default "2015-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_3b:periods "2015-01-01/2016-01-01/P3M"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_3c
/usr/bin/redis-cli  -n 0 SET layer:snap_test_3c:default "2000-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_3c:periods "1990-01-01/2016-01-01/P1Y"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_3d
/usr/bin/redis-cli  -n 0 SET layer:snap_test_3d:default "2010-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_3d:periods "2010-01-01/2012-03-11/P8D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_4a
/usr/bin/redis-cli  -n 0 SET layer:snap_test_4a:default "2000-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4a:periods "2000-01-01/2000-06-01/P1M"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4a:periods "2000-07-03/2000-07-03/P1M"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4a:periods "2000-08-01/2000-12-01/P1M"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_4b
/usr/bin/redis-cli  -n 0 SET layer:snap_test_4b:default "2001-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4b:periods "2001-01-01/2001-12-27/P8D"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4b:periods "2002-01-01/2002-12-27/P8D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_4c
/usr/bin/redis-cli  -n 0 SET layer:snap_test_4c:default "2010-01-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_4c:periods "2010-01-01/2010-01-01/P385D"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_5a
/usr/bin/redis-cli  -n 0 SET layer:snap_test_5a:default "2011-12-01"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_5a:periods "2002-12-01/2011-12-01/P1Y"
/usr/bin/redis-cli  -n 0 DEL layer:snap_test_year_boundary
/usr/bin/redis-cli  -n 0 SET layer:snap_test_year_boundary:default "2000-09-03"
/usr/bin/redis-cli  -n 0 SADD layer:snap_test_year_boundary:periods "2000-09-03/2000-09-03/P144D"
# Load oe-status data
/usr/bin/redis-cli -n 0 DEL layer:Raster_Status
/usr/bin/redis-cli -n 0 SET layer:Raster_Status:default "2004-08-01"
/usr/bin/redis-cli -n 0 SADD layer:Raster_Status:periods "2004-08-01/2004-08-01/P1M"
/usr/bin/redis-cli  -n 0 SAVE

# MapServer configs
python3.6 /usr/bin/oe2_wms_configure.py ../src/test/mapserver_test_data/test.yaml

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2