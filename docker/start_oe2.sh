#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Copy sample configs
chmod -R 755 /onearth
cp sample_configs/endpoint/* /etc/onearth/config/endpoint/
mkdir -p /onearth/layers
cp -R sample_configs/layers/* /etc/onearth/config/layers/
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/epsg4326/*

# Make GC Service
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg4326_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg4326_std_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg3857_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg3857_std_gc.yaml --make_gts

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

# Copy empty tiles
mkdir -p /onearth/empty_tiles/
cp empty_tiles/* /onearth/empty_tiles/

# Run layer config tools
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/epsg4326.yaml
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/epsg4326_std.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml

# Copy config stuff
mkdir -p /var/www/html/mrf_endpoint/static_test/default/tms
cp test_imagery/static_test* /var/www/html/mrf_endpoint/static_test/default/tms/
cp oe2_test_mod_mrf_static.conf /etc/httpd/conf.d
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_mod_mrf_static.conf
cp layer_configs/oe2_test_mod_mrf_static_layer.config /var/www/html/mrf_endpoint/static_test/default/tms/

mkdir -p /var/www/html/mrf_endpoint/date_test/default/tms
cp test_imagery/*date_test* /var/www/html/mrf_endpoint/date_test/default/tms
cp oe2_test_mod_mrf_date.conf /etc/httpd/conf.d
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_mod_mrf_date.conf
cp layer_configs/oe2_test_mod_mrf_date_layer.config /var/www/html/mrf_endpoint/date_test/default/tms/

mkdir -p /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/{2015,2016,2017}
cp test_imagery/*date_test_year_dir-2015* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2015
cp test_imagery/*date_test_year_dir-2016* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2016
cp test_imagery/*date_test_year_dir-2017* /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/2017
cp oe2_test_mod_mrf_date_year_dir.conf /etc/httpd/conf.d
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_mod_mrf_date_year_dir.conf
cp layer_configs/oe2_test_mod_mrf_date_layer_year_dir.config /var/www/html/mrf_endpoint/date_test_year_dir/default/tms/

mkdir -p /var/www/html/reproject_endpoint/date_test/default/tms
cp oe2_test_mod_reproject_date.conf /etc/httpd/conf.d
cp layer_configs/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/date_test/default/tms/oe2_test_mod_reproject_date_layer_source.config
cp layer_configs/oe2_test_mod_reproject_date*.config /var/www/html/reproject_endpoint/date_test/default/tms/

mkdir -p /var/www/html/reproject_endpoint/static_test/default/tms
cp oe2_test_mod_reproject_static.conf /etc/httpd/conf.d
cp layer_configs/oe2_test_mod_reproject_layer_source*.config /var/www/html/reproject_endpoint/static_test/default/tms/oe2_test_mod_reproject_static_layer_source.config
cp layer_configs/oe2_test_mod_reproject_static*.config /var/www/html/reproject_endpoint/static_test/default/tms/

# Empty tiles
mkdir -p /var/www/html/wmts/epsg4326/empty_tiles
mkdir -p /var/www/html/wmts/epsg3857/empty_tiles
mkdir -p /var/www/html/wmts/epsg3031/empty_tiles
mkdir -p /var/www/html/wmts/epsg3413/empty_tiles
cp empty_tiles/*512* /var/www/html/wmts/epsg4326/empty_tiles/
cp empty_tiles/*512* /var/www/html/wmts/epsg3031/empty_tiles/
cp empty_tiles/*512* /var/www/html/wmts/epsg3413/empty_tiles/
cp empty_tiles/*256* /var/www/html/wmts/epsg3857/empty_tiles/

# Config directories
mkdir -p /var/www/html/wmts/epsg4326/configs
mkdir -p /var/www/html/wmts/epsg3857/configs
mkdir -p /var/www/html/wmts/epsg3031/configs
mkdir -p /var/www/html/wmts/epsg3413/configs
mkdir -p /var/www/html/twms/epsg4326/configs
mkdir -p /var/www/html/twms/epsg3857/configs
mkdir -p /var/www/html/twms/epsg3031/configs
mkdir -p /var/www/html/twms/epsg3413/configs

# WMTS endpoints
mkdir -p /var/www/html/wmts/epsg4326/all
mkdir -p /var/www/html/wmts/epsg4326/best
mkdir -p /var/www/html/wmts/epsg4326/std
mkdir -p /var/www/html/wmts/epsg4326/nrt
mkdir -p /var/www/html/wmts/epsg3857/all
mkdir -p /var/www/html/wmts/epsg3857/best
mkdir -p /var/www/html/wmts/epsg3857/std
mkdir -p /var/www/html/wmts/epsg3857/nrt
mkdir -p /var/www/html/wmts/epsg3031/all
mkdir -p /var/www/html/wmts/epsg3031/best
mkdir -p /var/www/html/wmts/epsg3031/std
mkdir -p /var/www/html/wmts/epsg3031/nrt
mkdir -p /var/www/html/wmts/epsg3413/all
mkdir -p /var/www/html/wmts/epsg3413/best
mkdir -p /var/www/html/wmts/epsg3413/std
mkdir -p /var/www/html/wmts/epsg3413/nrt

# TWMS endpoints
mkdir -p /var/www/html/twms/epsg4326/all
mkdir -p /var/www/html/twms/epsg4326/best
mkdir -p /var/www/html/twms/epsg4326/std
mkdir -p /var/www/html/twms/epsg4326/nrt
mkdir -p /var/www/html/twms/epsg3857/all
mkdir -p /var/www/html/twms/epsg3857/best
mkdir -p /var/www/html/twms/epsg3857/std
mkdir -p /var/www/html/twms/epsg3857/nrt
mkdir -p /var/www/html/twms/epsg3031/all
mkdir -p /var/www/html/twms/epsg3031/best
mkdir -p /var/www/html/twms/epsg3031/std
mkdir -p /var/www/html/twms/epsg3031/nrt
mkdir -p /var/www/html/twms/epsg3413/all
mkdir -p /var/www/html/twms/epsg3413/best
mkdir -p /var/www/html/twms/epsg3413/std
mkdir -p /var/www/html/twms/epsg3413/nrt

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