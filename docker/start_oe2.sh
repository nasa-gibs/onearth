#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Copy config stuff
cp oe2_test_date_service.conf /etc/httpd/conf.d
mkdir -p /var/www/html/date_service
cp date_service.lua /var/www/html/date_service/date_service.lua

mkdir -p /var/www/html/mrf_endpoint/static_test/default/tms
cp test_imagery/static_test* /var/www/html/mrf_endpoint/static_test/default/tms/
cp oe2_test_mod_mrf_static.conf /etc/httpd/conf.d
cp oe2_test_mod_mrf_static_layer.config /var/www/html/mrf_endpoint/static_test/default/tms/

mkdir -p /var/www/html/mrf_endpoint/date_test/default/tms
cp test_imagery/date_test* /var/www/html/mrf_endpoint/date_test/default/tms
cp oe2_test_mod_mrf_date.conf /etc/httpd/conf.d
cp oe2_test_mod_mrf_date_layer.config /var/www/html/mrf_endpoint/date_test/default/tms/

mkdir -p /var/www/html/reproject_endpoint/date_test/default/tms
cp oe2_test_mod_reproject_date.conf /etc/httpd/conf.d
cp oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/date_test/default/tms/oe2_test_mod_reproject_date_layer_source.config
cp oe2_test_mod_reproject_date*.config /var/www/html/reproject_endpoint/date_test/default/tms/

mkdir -p /var/www/html/reproject_endpoint/static_test/default/tms
cp oe2_test_mod_reproject_static.conf /etc/httpd/conf.d
cp oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/static_test/default/tms/oe2_test_mod_reproject_static_layer_source.config
cp oe2_test_mod_reproject_static*.config /var/www/html/reproject_endpoint/static_test/default/tms/

echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

echo 'Starting Redis server'
/usr/bin/redis-server &
sleep 2

# Add some test data to redis for profiling
/usr/bin/redis-cli -n 0 DEL layer:date_test
/usr/bin/redis-cli -n 0 SET layer:date_test:default "2015-01-01"
/usr/bin/redis-cli -n 0 SADD layer:date_test:periods "2015-01-01/2017-01-01/P1Y"
/usr/bin/redis-cli -n 0 SAVE

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log