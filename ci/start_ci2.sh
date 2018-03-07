#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Change default dir to /build/test/ci_tests
cp httpd.conf /etc/httpd/conf/

# Copy date_service config
cp date_service/oe2_test_date_service.conf /etc/httpd/conf.d
mkdir -p /build/test/ci_tests/date_service
cp date_service/date_service.lua /build/test/ci_tests/date_service

# Copy config stuff
mkdir -p /build/test/ci_tests/mrf_endpoint/test_daily_png/default/EPSG4326_16km
cp -r ../src/test/ci_tests/test_imagery /build/test/ci_tests/
cp ../src/test/ci_tests/mrf_test.conf /etc/httpd/conf.d
cp layer_configs/test_mod_mrf_daily_png*.config /build/test/ci_tests/mrf_endpoint/test_daily_png/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/test_legacy_subdaily_jpg/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_legacy_subdaily_jpg*.config /build/test/ci_tests/mrf_endpoint/test_legacy_subdaily_jpg/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/test_nonyear_jpg/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_nonyear_jpg*.config /build/test/ci_tests/mrf_endpoint/test_nonyear_jpg/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/test_static_jpg/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_static_jpg*.config /build/test/ci_tests/mrf_endpoint/test_static_jpg/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/test_weekly_jpg/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_weekly_jpg*.config /build/test/ci_tests/mrf_endpoint/test_weekly_jpg/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_1a/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_1a*.config /build/test/ci_tests/mrf_endpoint/snap_test_1a/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_2a/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_2a*.config /build/test/ci_tests/mrf_endpoint/snap_test_2a/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_3a/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_3a*.config /build/test/ci_tests/mrf_endpoint/snap_test_3a/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_3b/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_3b*.config /build/test/ci_tests/mrf_endpoint/snap_test_3b/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_3c/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_3c*.config /build/test/ci_tests/mrf_endpoint/snap_test_3c/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_3d/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_3d*.config /build/test/ci_tests/mrf_endpoint/snap_test_3d/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_4a/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_4a*.config /build/test/ci_tests/mrf_endpoint/snap_test_4a/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_4b/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_4b*.config /build/test/ci_tests/mrf_endpoint/snap_test_4b/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_4c/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_4c*.config /build/test/ci_tests/mrf_endpoint/snap_test_4c/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_5a/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_5a*.config /build/test/ci_tests/mrf_endpoint/snap_test_5a/default/EPSG4326_16km/
mkdir -p /build/test/ci_tests/mrf_endpoint/snap_test_year_boundary/default/EPSG4326_16km
cp layer_configs/test_mod_mrf_snap_year_boundary*.config /build/test/ci_tests/mrf_endpoint/snap_test_year_boundary/default/EPSG4326_16km/

# GIBS sample configs


echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

echo 'Starting Redis server'
/usr/bin/redis-server &
sleep 2

# Add some test data to redis for profiling
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
/usr/bin/redis-cli  -n 0 SAVE

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log
