#!/bin/sh
S3_URL=${1:-http://gitc-test-imagery.s3.amazonaws.com}
REDIS_HOST=${2:-127.0.0.1}
S3_CONFIGS=$3

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# WMTS endpoints
mkdir -p /var/www/html/profiler/
mkdir -p /var/www/html/profiler_reproject/

# Create config directories
chmod -R 755 /onearth
mkdir -p /onearth/layers
mkdir -p /etc/onearth/config/conf/
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/

# Set up colormaps
mkdir -p /etc/onearth/colormaps/
mkdir -p /etc/onearth/colormaps/v1.0/
mkdir -p /etc/onearth/colormaps/v1.0/output
mkdir -p /etc/onearth/colormaps/v1.3/
mkdir -p /etc/onearth/colormaps/v1.3/output

ln -s /etc/onearth/colormaps /var/www/html/colormaps

# Data for oe-status
mkdir -p /onearth/idx/oe-status/BlueMarble16km
mkdir -p /onearth/layers/oe-status/BlueMarble16km
cp ../test_imagery/BlueMarble16km*.idx /onearth/idx/oe-status/BlueMarble16km/
cp ../test_imagery/BlueMarble16km*.pjg /onearth/layers/oe-status/BlueMarble16km/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "S3_CONFIGS not set for OnEarth configs, using sample data"

  # Copy empty tiles
  mkdir -p /etc/onearth/empty_tiles/
  cp ../empty_tiles/* /etc/onearth/empty_tiles/

  # Copy sample configs
  cp ../sample_configs/conf/* /etc/onearth/config/conf/
  cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
  cp -R ../sample_configs/layers/* /etc/onearth/config/layers/

else
	echo "S3_CONFIGS set for OnEarth configs, downloading from S3"

	python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/colormaps/v1.0' -b $S3_CONFIGS -p colormaps/v1.0
	python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/colormaps/v1.3' -b $S3_CONFIGS -p colormaps/v1.3

	for f in /etc/onearth/colormaps/v1.0/*
	do
		echo "Generating HTML for $f"
		base=$(basename $f)
		html=${base/"xml"/"html"}
		/usr/bin/colorMaptoHTML_v1.0.py -c $f > /etc/onearth/colormaps/v1.0/output/$html
	done

	for f in /etc/onearth/colormaps/v1.3/*
	do
		echo "Generating HTML for $f"
		base=$(basename $f)
		html=${base/"xml"/"html"}
		/usr/bin/colorMaptoHTML_v1.3.py -c $f > /etc/onearth/colormaps/v1.3/output/$html
	done

	python3.6 /usr/bin/oe_sync_s3_configs.py -d '/etc/onearth/empty_tiles/' -b $S3_CONFIGS -p empty_tiles
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint
	python3.6 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/conf/' -b $S3_CONFIGS -p config/conf

	for f in $(grep -l gc_service /etc/onearth/config/endpoint/*.yaml); do
	  CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
	  CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

	  mkdir -p $CONFIG_SOURCE

	  # WMTS Endpoint
	  mkdir -p $(yq eval ".wmts_service.internal_endpoint" $f)

	  # TWMS Endpoint
	  mkdir -p $(yq eval ".twms_service.internal_endpoint" $f)

    python3.6 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

# Replace with S3 URL
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml # in case there is a preceding slash
sed -i 's@/{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml # in case there is a preceding slash
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*/*.yaml
sed -i 's@{S3_URL}@'$S3_URL'@g' /etc/onearth/config/layers/*/*.yaml

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

# Run layer config tools
for f in $(grep -l gc_service /etc/onearth/config/endpoint/*.yaml); do
  python3.6 /usr/bin/oe2_wmts_configure.py $f
done

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

# Performance Test Data
mkdir -p /onearth/idx/profiler/BlueMarble
wget -O /onearth/idx/profiler/BlueMarble/BlueMarble.idx $S3_URL/profiler/BlueMarble.idx

mkdir -p /onearth/idx/profiler/MOGCR_LQD_143_STD/2011
f=$(../../src/test/oe_gen_hash_filename.py -l MOGCR_LQD_143_STD -t 1293840000 -e .idx)
wget -O /onearth/idx/profiler/MOGCR_LQD_143_STD/2011/$f $S3_URL/profiler/MOGCR_LQD_143_STD/2011/$f

mkdir -p /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/2018
wget -O /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/VNGCR_LQD_I1-M4-M3_NRT.idx $S3_URL/profiler/VNGCR_LQD_I1-M4-M3_NRT/2018/VNGCR_LQD_I1-M4-M3_NRT-2018016000000.idx
d=1516060800
until [ $d -gt 1524614400 ]; do
    f=$(../../src/test/oe_gen_hash_filename.py -l VNGCR_LQD_I1-M4-M3_NRT -t $d -e .idx)
    ln -s /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/VNGCR_LQD_I1-M4-M3_NRT.idx /onearth/idx/profiler/VNGCR_LQD_I1-M4-M3_NRT/2018/$f
    let d+=86400
done

mkdir -p /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/2018
wget -O /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/MOG13Q4_LQD_NDVI_NRT.idx $S3_URL/profiler/MOG13Q4_LQD_NDVI_NRT/2018/MOG13Q4_LQD_NDVI_NRT-2018001000000.idx
d=1514764800
until [ $d -gt 1523318400 ]; do
    f=$(../../src/test/oe_gen_hash_filename.py -l MOG13Q4_LQD_NDVI_NRT -t $d -e .idx)
    ln -s /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/MOG13Q4_LQD_NDVI_NRT.idx /onearth/idx/profiler/MOG13Q4_LQD_NDVI_NRT/2018/$f
    let d+=86400
done

# ASTER_L1T_Radiance_Terrain_Corrected subdaily example

mkdir -p /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970
mkdir -p /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz $S3_URL/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011844.idx
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz $S3_URL/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/2016/ASTER_L1T_Radiance_Terrain_Corrected-2016336011835.idx
wget -O /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz $S3_URL/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz
tar -zxf /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx.tgz -C /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/
mv /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/out/out.idx /onearth/idx/epsg4326/ASTER_L1T_Radiance_Terrain_Corrected/1970/ASTER_L1T_Radiance_Terrain_Corrected-1970001000000.idx

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
/usr/bin/redis-cli -h $REDIS_HOST -n 0 DEL layer:BlueMarble16km
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SET layer:BlueMarble16km:default "2004-08-01"
/usr/bin/redis-cli -h $REDIS_HOST -n 0 SADD layer:BlueMarble16km:periods "2004-08-01/2004-08-01/P1M"


echo 'Restarting Apache server'
/usr/sbin/httpd -k restart
sleep 2