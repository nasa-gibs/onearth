#!/bin/sh

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# rm -rf /run/httpd/* /tmp/httpd*
# rm -f /etc/httpd/conf.d/onearth-demo.conf
#
# echo 'Setting log locations to write to stdout/stderr'
# ln -sf /dev/stdout /etc/httpd/logs/access.log
# ln -sf /dev/stderr /etc/httpd/logs/error.log
#
# rm -rf /var/www/html/
# echo 'Creating dummy index.html for ALB'
# mkdir -p /var/www/html
# cd /var/www/html
# cp -a /mnt/config/apache/www/index.html .
# echo 'Dummy index.html created'
#
# echo 'Configuring OnEarth Apache server'
# mkdir -p /usr/share/onearth/gitc
# cd /usr/share/onearth/gitc
# cp /mnt/config/apache/server/httpd.conf /etc/httpd/conf/
# cp /mnt/config/apache/conf.d/*.conf /etc/httpd/conf.d/
# #TODO: Should delete the endpoints from git and just manipulate the demo endpoints in the docker container
# cp -a /mnt/config/apache/wmts .
# cp -a /mnt/config/apache/twms .
# for endpoint in wmts twms; do
#   cp -a ../empty_tiles/. $endpoint
#   for proj in geo arctic antarctic; do cp -a $endpoint/. $endpoint-$proj; done
# done
# echo 'OnEarth Apache WMTS/TWMS services configured'
#
# echo 'Mounting S3 bucket for MRF data'
# mkdir -p /onearth/data /mnt/cache/data
# # N.B. Current cache path is inside the docker container and not to a mount point on instance hosting docker. This may produce performance issues
# # Should we make the cache-mem-size and cache-disk-size params that are passed to script?
# yas3fs \
#   --new-queue "s3://${MRF_BUCKET}" \
#   --region "$AWS_DEFAULT_REGION" \
#   --topic "$CACHE_TOPIC_ARN" \
#   --log /var/log/yas3fs.log \
#   --no-metadata \
#   --recheck-s3 \
#   --cache-mem-size 2048 \
#   --cache-disk-size 20480 \
#   --cache-check 10 \
#   --cache-path /mnt/cache/data \
#   --s3-num 40 \
#   --buffer-size 20480 \
#   --buffer-prefetch 0 \
#   --download-num 40 \
#   /onearth/data
# echo 'S3 Bucket for MRF mounted'
#
# echo 'Running Initial Layer Configuration for OnEarth'
# /usr/bin/oe_configure_layer --lcdir /mnt/config/onearth
#
# echo 'Restarting Apache Server'
# exec /usr/sbin/apachectl -DFOREGROUND
