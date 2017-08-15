#!/bin/sh

set -evx

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

if [ ! -d /mnt/config ]; then
  echo "This script expects /mnt/config to exist" >&2
  exit 1
fi

echo 'Setting log locations to write to stdout/stderr'
ln -sf /dev/stdout /etc/httpd/logs/access.log
ln -sf /dev/stderr /etc/httpd/logs/error.log

rm -rf /run/httpd/* /tmp/httpd*
rm -f /etc/httpd/conf.d/onearth-demo.conf
rm -rf /var/www/html/

echo 'Creating dummy index.html for ALB'
mkdir -p /var/www/html
cd /var/www/html
cp -a /mnt/config/apache/www/index.html .
echo 'Dummy index.html created'

echo 'Configuring OnEarth Apache server'
mkdir -p /usr/share/onearth/gitc
cd /usr/share/onearth/gitc
cp /mnt/config/apache/server/httpd.conf /etc/httpd/conf/
cp /mnt/config/apache/conf.d/*.conf /etc/httpd/conf.d/
cp -a /mnt/config/apache/wmts .
cp -a /mnt/config/apache/twms .
for endpoint in wmts twms; do
  cp -a ../empty_tiles/. $endpoint
  for proj in geo arctic antarctic; do cp -a $endpoint/. $endpoint-$proj; done
done
echo 'OnEarth Apache WMTS/TWMS services configured'

echo 'Running Initial Layer Configuration for OnEarth'
/usr/bin/oe_configure_layer --lcdir /mnt/config/onearth

echo 'Starting Apache server'
exec /usr/sbin/httpd -DFOREGROUND
