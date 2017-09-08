#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

echo 'Starting Apache server'
/usr/sbin/apachectl

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log
