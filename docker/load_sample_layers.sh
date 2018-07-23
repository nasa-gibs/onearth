#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# WMTS endpoints
mkdir -p /var/www/html/profiler/
mkdir -p /var/www/html/profiler_reproject/
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

# Copy empty tiles
mkdir -p /onearth/empty_tiles/
cp empty_tiles/* /onearth/empty_tiles/

# Copy sample configs
chmod -R 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/
cp sample_configs/endpoint/* /etc/onearth/config/endpoint/
cp -R sample_configs/layers/* /etc/onearth/config/layers/
# Replace with S3 URL
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml

# Make GC Service
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/profiler_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/profiler_reproject_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg4326_best_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg4326_std_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg4326_all_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg3857_best_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg3857_std_gc.yaml --make_gts
lua /home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua /etc/onearth/config/endpoint/epsg3857_all_gc.yaml --make_gts

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

# Run layer config tools
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/profiler.yaml
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/epsg4326_best.yaml
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/epsg4326_std.yaml
python3.6 /usr/bin/oe2_wmts_configure.py /etc/onearth/config/endpoint/epsg4326_all.yaml

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2

# Performance Test Data

mkdir -p /onearth/idx/profiler/BlueMarble
wget -O /onearth/idx/profiler/BlueMarble/BlueMarble.idx https://s3.amazonaws.com/gitc-test-imagery/BlueMarble.idx

mkdir -p /onearth/idx/profiler/MOGCR_LQD_143_STD
f=$(../src/test/oe_gen_hash_filename.py -l MOGCR_LQD_143_STD -t 1293840000 -e .idx)
wget -O /onearth/idx/profiler/MOGCR_LQD_143_STD/$f https://s3.amazonaws.com/gitc-test-imagery/$f

mkdir -p /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT
wget -O /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/VNGCR_LQD_I1-M4-M3_NRT.idx https://s3.amazonaws.com/gitc-test-imagery/VNGCR_LQD_I1-M4-M3_NRT.idx
d=1516060800
until [ $d -gt 1524614400 ]; do
    f=$(../src/test/oe_gen_hash_filename.py -l VNGCR_LQD_I1-M4-M3_NRT -t $d -e .idx)
    ln -s /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/VNGCR_LQD_I1-M4-M3_NRT.idx /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/$f
    let d+=86400
done

mkdir -p /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT
wget -O /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/MOG13Q4_LQD_NDVI_NRT.idx https://s3.amazonaws.com/gitc-test-imagery/MOG13Q4_LQD_NDVI_NRT.idx
d=1514764800
until [ $d -gt 1523318400 ]; do
    f=$(../src/test/oe_gen_hash_filename.py -l MOG13Q4_LQD_NDVI_NRT -t $d -e .idx)
    ln -s /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/MOG13Q4_LQD_NDVI_NRT.idx /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/$f
    let d+=86400
done

# ASTER_L1T_Radiance_Terrain_Corrected for gibs-status

cp oe2_gibs_status.conf /etc/httpd/conf.d
mkdir -p /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970
mkdir -p /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/4642-ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/5978-ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz https://s3.amazonaws.com/gitc-test-imagery/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/3b5c-ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx


# Sample MODIS configs
# cp oe2_test_MODIS.conf /etc/httpd/conf.d
# sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/httpd/conf.d/oe2_test_MODIS.conf

# Alias endpoints
mkdir -p /var/www/html/wmts/epsg3857/all/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/GoogleMapsCompatible_Level9
mkdir -p /var/www/html/wmts/epsg3857/best/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/GoogleMapsCompatible_Level9
mkdir -p /var/www/html/wmts/epsg3857/std/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/GoogleMapsCompatible_Level9
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg4326/best/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg4326/std/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg3857/all/MODIS_Aqua_Sea_Ice_v6_STD/default/GoogleMapsCompatible_Level7
mkdir -p /var/www/html/wmts/epsg3857/best/MODIS_Aqua_Sea_Ice_v6_STD/default/GoogleMapsCompatible_Level7
mkdir -p /var/www/html/wmts/epsg3857/std/MODIS_Aqua_Sea_Ice_v6_STD/default/GoogleMapsCompatible_Level7
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_Sea_Ice_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg4326/best/MODIS_Aqua_Sea_Ice_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg4326/std/MODIS_Aqua_Sea_Ice_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3031/all/MODIS_Aqua_Sea_Ice_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3413/all/MODIS_Aqua_Sea_Ice_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3031/all/MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg3413/all/MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3031/all/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3413/all/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3031/all/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg3413/all/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/default/1km
mkdir -p /var/www/html/wmts/epsg4326/all/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg3031/all/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/default/250m
mkdir -p /var/www/html/wmts/epsg3413/all/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/default/250m

# Index file directories
mkdir -p /onearth/idx/epsg4326/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD/2012
mkdir -p /onearth/idx/epsg4326/MODIS_Aqua_Sea_Ice_v6_STD/2012
mkdir -p /onearth/idx/epsg3031/MODIS_Aqua_Sea_Ice_v6_STD/2012
mkdir -p /onearth/idx/epsg3413/MODIS_Aqua_Sea_Ice_v6_STD/2012
mkdir -p /onearth/idx/epsg3031/MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD/2012/
mkdir -p /onearth/idx/epsg3413/MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD/2012/
mkdir -p /onearth/idx/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/2012
mkdir -p /onearth/idx/epsg3031/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/2012
mkdir -p /onearth/idx/epsg3413/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/2012
mkdir -p /onearth/idx/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/2012
mkdir -p /onearth/idx/epsg3031/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/2012
mkdir -p /onearth/idx/epsg3413/MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD/2012
mkdir -p /onearth/idx/epsg4326/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/2012
mkdir -p /onearth/idx/epsg3031/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/2012
mkdir -p /onearth/idx/epsg3413/MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD/2012

# TWMS configs and endpoints
mkdir -p /var/www/html/twms/epsg4326/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
mkdir -p /var/www/html/twms/epsg3857/configs/MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
mkdir -p /var/www/html/twms/epsg4326/configs/MODIS_Aqua_Sea_Ice_v6_STD
mkdir -p /var/www/html/twms/epsg3857/configs/MODIS_Aqua_Sea_Ice_v6_STD

# WMTS GetCapabilities
mkdir /var/www/html/wmts/epsg4326/all/1.0.0
wget -O /var/www/html/wmts/epsg4326/all/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg4326/all/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg4326/best/1.0.0
wget -O /var/www/html/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg4326/std/1.0.0
wget -O /var/www/html/wmts/epsg4326/std/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg4326/std/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg3857/all/1.0.0
wget -O /var/www/html/wmts/epsg3857/all/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg3857/all/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg3857/best/1.0.0
wget -O /var/www/html/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg3857/std/1.0.0
wget -O /var/www/html/wmts/epsg3857/std/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg3857/std/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg3031/all/1.0.0
wget -O /var/www/html/wmts/epsg3031/all/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg3031/all/1.0.0/WMTSCapabilities.xml
mkdir /var/www/html/wmts/epsg3413/all/1.0.0
wget -O /var/www/html/wmts/epsg3413/all/1.0.0/WMTSCapabilities.xml https://gibs.earthdata.nasa.gov/wmts/epsg3413/all/1.0.0/WMTSCapabilities.xml

# Initial layers
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

# Copy configs
cp layer_configs/MODIS_*4326.config /var/www/html/wmts/epsg4326/configs/
cp layer_configs/MODIS_*3031.config /var/www/html/wmts/epsg3031/configs/
cp layer_configs/MODIS_*3413.config /var/www/html/wmts/epsg3413/configs/

# Start Redis if running locally
if [ "$REDIS_HOST" = "127.0.0.1" ]; then
	echo 'Starting Redis server'
	/usr/bin/redis-server &
	sleep 2
	# Turn off the following line for production systems
	/usr/bin/redis-cli -n 0 CONFIG SET protected-mode no
fi

# Add time metadata to Redis
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

/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg4326:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:best:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:std:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:default "1970-01-01T00:00:00Z"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD epsg3857:all:layer:ASTER_L1T_Radiance_Terrain_Corrected_v3_STD:periods "1970-01-01T00:00:00Z/2100-01-01T00:00:00Z/PT1S"

/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_SurfaceReflectance_Bands121_v6_STD:periods "2012-09-10/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_Sea_Ice_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_Sea_Ice_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_Sea_Ice_v6_STD:periods "2012-09-10/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_CorrectedReflectance_TrueColor_v6_STD:periods "2012-09-10/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD:periods "2012-09-10/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_Brightness_Temp_Band31_Night_v6_STD:periods "2012-09-10/2018-12-31/P1D"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:default "2012-09-10"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:periods "2012-09-10/2018-12-31/P1D"

# Run reproject config tools
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/profiler_reproject.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_best.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_std.yaml
python3.6 /usr/bin/oe2_reproject_configure.py /etc/onearth/config/endpoint/epsg3857_all.yaml

echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2

sh build_demo.sh