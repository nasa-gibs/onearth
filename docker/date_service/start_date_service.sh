#!/bin/sh
REDIS_HOST=${1:-gitc-jrod-redis.4fest7.ng.0001.use1.cache.amazonaws.com}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Copy config stuff
cp oe2_test_date_service.conf /etc/httpd/conf.d
mkdir -p /var/www/html/date_service
cp date_service.lua /var/www/html/date_service/date_service.lua
sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' /var/www/html/date_service/date_service.lua

echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log