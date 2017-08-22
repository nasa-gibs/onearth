#!/bin/sh

set -evx

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

for DIR in /mnt/config /oe_layers_config; do
  if [ ! -d "$DIR" ]; then
    echo "${DIR} does not exist" >&2
    exit 1
  fi
done

# Copy the config to the image
rsync -av /mnt/config/ /

echo 'Running Initial Layer Configuration for OnEarth'
/usr/bin/oe_configure_layer --lcdir /oe_layers_config

echo 'Starting Apache server'
/usr/sbin/apachectl

# Make sure that the Apache logs exist before tailing them
touch /etc/httpd/logs/access.log /etc/httpd/logs/error.log

# Tail the apache logs
exec tail -qF /etc/httpd/logs/access.log /etc/httpd/logs/error.log
