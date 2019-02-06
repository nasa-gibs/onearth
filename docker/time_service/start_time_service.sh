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
fi

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log