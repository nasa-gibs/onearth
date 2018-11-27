#!/bin/sh
REDIS_HOST=${1:-onearth}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# copy config stuff
cp onearth_time_service.conf /etc/httpd/conf.d
mkdir -p /var/www/html/time_service
cp time_service.lua /var/www/html/time_service/time_service.lua
sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' /var/www/html/time_service/time_service.lua

sed -i 's@{REDIS_HOST}@'$REDIS_HOST'@g' onearth-time-service.yaml
echo 'Starting twemproxy'
nutcracker -d -c onearth-time-service.yaml

echo 'Starting Apache server'
/usr/sbin/apachectl
sleep 2

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log