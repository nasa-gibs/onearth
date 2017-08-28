#!/bin/sh

set -evx

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Copy the config to the image
if [ ! -d "/mnt/config" ]; then
  echo "The /mnt/config directory does not exist" >&2
  exit 1
fi
rsync -av /mnt/config/ /

echo 'Running Initial Layer Configuration for OnEarth'
if [ ! -d "/oe_layers_config" ]; then
  echo "The /oe_layers_config directory does not exist" >&2
  exit 1
fi
/usr/bin/oe_configure_layer --lcdir /oe_layers_config

echo 'Starting Apache server'
/usr/sbin/apachectl

# Make sure that the Apache logs exist before tailing them
touch /etc/httpd/logs/access.log /etc/httpd/logs/error.log

# Tail the apache logs
exec tail -qF /etc/httpd/logs/access.log /etc/httpd/logs/error.log
