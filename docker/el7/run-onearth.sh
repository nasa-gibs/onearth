#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

oe_configure_layer --create_mapfile --layer_dir=/etc/onearth/config/layers/ --generate_links

echo 'Starting Apache server'
/usr/sbin/httpd -k start

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log