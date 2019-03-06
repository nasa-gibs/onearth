#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

cd /home/oe2/onearth/docker/tile_services

# Copy example Apache configs for OnEarth
mkdir -p /var/www/html/mrf_endpoint/static_test/default/tms
cp ../test_imagery/static_test* /var/www/html/mrf_endpoint/static_test/default/tms/
cp oe2_test_mod_mrf_static.conf /etc/httpd/conf.d
cp ../layer_configs/oe2_test_mod_mrf_static_layer.config /var/www/html/mrf_endpoint/static_test/default/tms/

mkdir -p /var/www/html/mrf_endpoint/date_test/default/tms
cp ../test_imagery/*date_test* /var/www/html/mrf_endpoint/date_test/default/tms
cp oe2_test_mod_mrf_date.conf /etc/httpd/conf.d
cp ../layer_configs/oe2_test_mod_mrf_date_layer.config /var/www/html/mrf_endpoint/date_test/default/tms/

mkdir -p /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/{2015,2016,2017}
cp ../test_imagery/*date_test_year_dir-2015* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2015
cp ../test_imagery/*date_test_year_dir-2016* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2016
cp ../test_imagery/*date_test_year_dir-2017* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2017
cp oe2_test_mod_mrf_date_year_dir.conf /etc/httpd/conf.d
cp ../layer_configs/oe2_test_mod_mrf_date_layer_year_dir.config /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/

# Load GIBS sample layers
sh load_sample_layers.sh $S3_URL $REDIS_HOST

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log