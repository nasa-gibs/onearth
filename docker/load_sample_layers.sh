#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# GIBS sample configs

mkdir -p /var/www/html/reproject_endpoint/BlueMarble/default/500m/
cp layer_configs/BlueMarble_reproject.config /var/www/html/reproject_endpoint/BlueMarble/default/500m/
cp layer_configs/BlueMarble_source.config /var/www/html/reproject_endpoint/BlueMarble/default/500m//

mkdir -p /var/www/html/mrf_endpoint/BlueMarble/default/500m/
wget -O /var/www/html/mrf_endpoint/BlueMarble/default/500m/BlueMarble.idx https://s3.amazonaws.com/gitc-test-imagery/BlueMarble.idx
cp layer_configs/BlueMarble.config /var/www/html/mrf_endpoint/BlueMarble/default/500m/

mkdir -p /var/www/html/mrf_endpoint/MOGCR_LQD_143_STD/default/250m/
wget -O /var/www/html/mrf_endpoint/MOGCR_LQD_143_STD/default/250m/MOG13Q4_LQD_NDVI_NRT1514764800.idx https://s3.amazonaws.com/gitc-test-imagery/MOG13Q4_LQD_NDVI_NRT1514764800.idx
cp layer_configs/MOGCR_LQD_143_STD.config /var/www/html/mrf_endpoint/MOGCR_LQD_143_STD/default/250m/

mkdir -p /var/www/html/mrf_endpoint/VNGCR_LQD_I1-M4-M3_NRT/default/250m/2018
wget -O /var/www/html/mrf_endpoint/VNGCR_LQD_I1-M4-M3_NRT/default/250m/VNGCR_LQD_I1-M4-M3_NRT.idx https://s3.amazonaws.com/gitc-test-imagery/VNGCR_LQD_I1-M4-M3_NRT.idx
d=1516060800
until [ $d -gt 1524614400 ]; do
    ln -s /var/www/html/mrf_endpoint/VNGCR_LQD_I1-M4-M3_NRT/default/250m/VNGCR_LQD_I1-M4-M3_NRT.idx /var/www/html/mrf_endpoint/VNGCR_LQD_I1-M4-M3_NRT/default/250m/2018/VNGCR_LQD_I1-M4-M3_NRT$d.idx
    let d+=86400
done
cp layer_configs/VNGCR_LQD_I1-M4-M3_NRT*.config /var/www/html/mrf_endpoint/VNGCR_LQD_I1-M4-M3_NRT/default/250m/

mkdir -p /var/www/html/mrf_endpoint/MOG13Q4_LQD_NDVI_NRT/default/250m/2018
wget -O /var/www/html/mrf_endpoint/MOG13Q4_LQD_NDVI_NRT/default/250m/MOG13Q4_LQD_NDVI_NRT.idx https://s3.amazonaws.com/gitc-test-imagery/MOG13Q4_LQD_NDVI_NRT.idx
d=1514764800
until [ $d -gt 1523318400 ]; do
    ln -s /var/www/html/mrf_endpoint/MOG13Q4_LQD_NDVI_NRT/default/250m/MOG13Q4_LQD_NDVI_NRT.idx /var/www/html/mrf_endpoint/MOG13Q4_LQD_NDVI_NRT/default/250m/2018/MOG13Q4_LQD_NDVI_NRT$d.idx
    let d+=86400
done
cp layer_configs/MOG13Q4_LQD_NDVI_NRT.config /var/www/html/mrf_endpoint/MOG13Q4_LQD_NDVI_NRT/default/250m/

# AST_L1T sample configs

# Copy AST_L1T conf and replace {S3_URL} in conf
cp oe2_test_AST_L1T.conf /etc/httpd/conf.d
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_AST_L1T.conf

# Alias endpoints
mkdir -p /var/www/html/wmts/epsg3857/all/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/default/GoogleMapsCompatible_Level13
mkdir -p /var/www/html/wmts/epsg3857/best/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/default/GoogleMapsCompatible_Level13
mkdir -p /var/www/html/wmts/epsg3857/std/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/default/GoogleMapsCompatible_Level13
mkdir -p /var/www/html/wmts/epsg3857/all/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/default/GoogleMapsCompatible_Level13
mkdir -p /var/www/html/wmts/epsg4326/all/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/default/15.625m/2016
mkdir -p /var/www/html/wmts/epsg4326/best/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/default/15.625m/2016
mkdir -p /var/www/html/wmts/epsg4326/std/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/default/15.625m/2016
mkdir -p /var/www/html/wmts/epsg4326/all/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/default/15.625m/2016

# Index file directories
mkdir -p /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016
mkdir -p /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970

# TWMS configs and endpoints
mkdir -p /var/www/html/twms/epsg4326/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD
mkdir -p /var/www/html/twms/epsg3857/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD
mkdir -p /var/www/html/twms/epsg4326/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily
mkdir -p /var/www/html/twms/epsg3857/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily

cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected.config /var/www/html/wmts/epsg4326/configs/
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_source.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_reproject.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_4326_twms.config /var/www/html/twms/epsg4326/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/twms.config
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_3857_twms.config /var/www/html/twms/epsg3857/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily/twms.config
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_4326_twms.config /var/www/html/twms/epsg4326/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/twms.config
cp layer_configs/ASTER_L1T_Radiance_Terrain_Corrected_3857_twms.config /var/www/html/twms/epsg3857/configs/ASTER_L1T_Radiance_Terrain_Corrected_Subdaily_v3_STD/twms.config
cp empty_tiles/ASTER_L1T_Radiance_Terrain_Corrected.png /var/www/html/wmts/epsg4326/empty_tiles/

wget -O /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz
tar -zxf /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz -C /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx
wget -O /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz
tar -zxf /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz -C /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx
wget -O /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz
tar -zxf /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz -C /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/
mv /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/out/out.idx /var/www/html/wmts/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx

# Sample MODIS configs
cp oe2_test_MODIS.conf /etc/httpd/conf.d
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_MODIS.conf

# Alias endpoints
mkdir -p /var/www/html/wmts/epsg3857/all/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/GoogleMapsCompatible_Level9
mkdir -p /var/www/html/wmts/epsg3857/best/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/GoogleMapsCompatible_Level9
mkdir -p /var/www/html/wmts/epsg3857/std/MODIS_Aqua_Sea_Ice_v6_STD/default/GoogleMapsCompatible_Level7
mkdir -p /var/www/html/wmts/epsg3857/all/MODIS_Aqua_Sea_Ice_v6_STD/default/GoogleMapsCompatible_Level7
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/250m/2012
mkdir -p /var/www/html/wmts/epsg4326/best/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/250m/2012
mkdir -p /var/www/html/wmts/epsg4326/std/MODIS_Aqua_Sea_Ice_v6_STD/default/1km/2012
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_Sea_Ice_v6_STD/default/1km/2012

# Index file directories
mkdir -p /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012
mkdir -p /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012

# TWMS configs and endpoints
mkdir -p /var/www/html/twms/epsg4326/configs/MODIS_Aqua_Sea_Ice_v6_STD
mkdir -p /var/www/html/twms/epsg3857/configs/MODIS_Aqua_Sea_Ice_v6_STD
mkdir -p /var/www/html/twms/epsg4326/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
mkdir -p /var/www/html/twms/epsg3857/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD

cp layer_configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD.config /var/www/html/wmts/epsg4326/configs/
cp layer_configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD_source.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD_reproject.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD_4326_twms.config /var/www/html/twms/epsg4326/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/twms.config
cp layer_configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD_3857_twms.config /var/www/html/twms/epsg3857/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/twms.config

cp layer_configs/MODIS_Aqua_Sea_Ice_v6_STD.config /var/www/html/wmts/epsg4326/configs/
cp layer_configs/MODIS_Aqua_Sea_Ice_v6_STD_source.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/MODIS_Aqua_Sea_Ice_v6_STD_reproject.config /var/www/html/wmts/epsg3857/configs/
cp layer_configs/MODIS_Aqua_Sea_Ice_v6_STD_4326_twms.config /var/www/html/twms/epsg4326/configs/MODIS_Aqua_Sea_Ice_v6_STD/twms.config
cp layer_configs/MODIS_Aqua_Sea_Ice_v6_STD_3857_twms.config /var/www/html/twms/epsg3857/configs/MODIS_Aqua_Sea_Ice_v6_STD/twms.config

wget -O /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz
tar -zxf /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz -C /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/
mv /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/tmp/gitc_mrfGen_1524512832545/output/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254003000.idx /var/www/html/wmts/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx
wget -O /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz
tar -zxf /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx.tgz -C /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/
mv /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/tmp/gitc_mrfGen_1524512832545/output/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254003000.idx /var/www/html/wmts/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012/afeb-MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD-2012254000000.idx



# Add time metadata to redis
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test:default "2015-01-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test:periods "2015-01-01/2017-01-01/P1Y"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:date_test_year_dir
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:date_test_year_dir:default "2015-01-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:date_test_year_dir:periods "2015-01-01/2017-01-01/P1Y"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MOGCR_LQD_143_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MOGCR_LQD_143_STD:default "2011-01-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MOGCR_LQD_143_STD:periods "2011-01-01/2011-01-02/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:VNGCR_LQD_I1-M4-M3_NRT
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:VNGCR_LQD_I1-M4-M3_NRT:default "2018-01-16"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:VNGCR_LQD_I1-M4-M3_NRT:periods "2018-01-16/2019-01-16/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MOG13Q4_LQD_NDVI_NRT
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MOG13Q4_LQD_NDVI_NRT:default "2018-01-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MOG13Q4_LQD_NDVI_NRT:periods "2018-01-01/2019-01-01/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_Sea_Ice_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_Sea_Ice_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_Sea_Ice_v6_STD:periods "2012-01-01/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD:periods "2012-01-01/2018-12-31/P1D"

/usr/bin/redis-cli -h $REDIS_HOST -n 0 SAVE

# Tail the apache logs
exec tail -qF \
  /etc/httpd/logs/access.log \
  /etc/httpd/logs/error.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log