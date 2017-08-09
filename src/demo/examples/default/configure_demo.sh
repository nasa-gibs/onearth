#!/bin/sh

#Projections and their EPSG equivalents
declare -a PROJECTIONS=(epsg4326 epsg3857 epsg3413 epsg3031)
declare -a PROJEPSGS=(EPSG4326 EPSG3857 EPSG3413 EPSG3031)

#Download image files
curl -# -o /usr/share/onearth/demo/source_images/blue_marble.jpg https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73776/world.topo.bathy.200408.3x21600x10800.jpg \
				 --progress-bar

#Create MRF directories and copy source/empty tile images and config XML files, then create MRF, copy images to archive, copy MRF to header dir
#and copy layer config

#Blue marble - geographic and webmercator (using same source image)
declare -a MARBLE_PROJECTIONS=(geo webmerc)
for INDEX in {0..1}
do
	#Copy image files and set up MRF process dirs
	mkdir -p /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/{source_images,working_dir,logfile_dir,output_dir,empty_tiles}
	/bin/cp /usr/share/onearth/demo/source_images/blue_marble.* /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/source_images/
	/bin/cp /usr/share/onearth/demo/mrf_configs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}_config.xml /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/
	/bin/cp /usr/share/onearth/demo/examples/default/wmts/epsg4326/black.jpg /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/empty_tiles/
	cd /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/

	mrfgen -c /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}_config.xml

	#Create data archive directories and copy MRF files
	 mkdir -p /usr/share/onearth/demo/data/${PROJEPSGS[$INDEX]}/blue_marble/
	for f in /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/output_dir/*; do mv "$f" "${f//blue_marble2004336_/blue_marble}"; done
	 /bin/cp /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/output_dir/* /usr/share/onearth/demo/data/${PROJEPSGS[$INDEX]}/blue_marble/
	 /bin/cp /usr/share/onearth/demo/generated_mrfs/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}/output_dir/blue_marble.mrf /etc/onearth/config/headers/blue_marble_${MARBLE_PROJECTIONS[$INDEX]}.mrf
done

#MODIS data - right now, we're only using it in geo projection
declare -a MODIS_PROJECTIONS=(geo)
for INDEX in {0..0}
do
	#Copy image files and set up MRF process dirs
	mkdir -p /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/{source_images,working_dir,logfile_dir,output_dir,empty_tiles}
	/bin/cp /usr/share/onearth/demo/source_images/MYR4ODLOLLDY_global_2014277_10km.* /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/source_images/
	/bin/cp /usr/share/onearth/demo/mrf_configs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}_config.xml /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/
	/bin/cp /usr/share/onearth/demo/examples/default/wmts/epsg4326/transparent.png /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/empty_tiles/
	cd /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/

	mrfgen -c /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}_config.xml

	#Create data archive directories and copy MRF files
	 mkdir -p /usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km
	 mkdir -p /usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km/{2014,YYYY}
	 /bin/cp /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/output_dir/MYR4ODLOLLDY2014277_.* /usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km/2014/
	 find /usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km/2014 -name 'MYR4ODLOLLDY2014277*' -type f -exec bash -c 'ln -s "$1" "${1/2014277/TTTTTTT}"' -- {} \;
	 find /usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km/2014 -name 'MYR4ODLOLLDYTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/EPSG4326/MYR4ODLOLLDY_global_10km/YYYY/"' -- {} \;
	 /bin/cp /usr/share/onearth/demo/generated_mrfs/MYR4ODLOLLDY_global_2014277_10km_${MODIS_PROJECTIONS[$INDEX]}/output_dir/MYR4ODLOLLDY2014277_.mrf /etc/onearth/config/headers/MYR4ODLOLLDY_${MODIS_PROJECTIONS[$INDEX]}.mrf
done

#MODIS_C5_fires
	#Copy image files and set up MRF process dirs
	mkdir -p /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/{source_images,working_dir,logfile_dir,output_dir,empty_tiles}
	/bin/cp /usr/share/onearth/demo/source_images/MODIS_C5_fires_2016110.* /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/source_images/
	/bin/cp /usr/share/onearth/demo/vector_configs/MODIS_C5_fires*.xml /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/
	cd /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/
	# For Shapefile
	oe_vectorgen -c /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/MODIS_C5_fires.xml
	#Create data archive directories and copy MRF files
	mkdir -p /usr/share/onearth/demo/data/shapefiles/MODIS_C5_fires/{2016,YYYY}
	/bin/cp /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/output_dir/* /usr/share/onearth/demo/data/shapefiles/MODIS_C5_fires/2016/
	find /usr/share/onearth/demo/data/shapefiles/MODIS_C5_fires/2016/ -name 'MODIS_C5_fires2016110*' -type f -exec bash -c 'ln -s "$1" "${1/2016110/TTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/shapefiles/MODIS_C5_fires/2016/ -name 'MODIS_C5_firesTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/shapefiles/MODIS_C5_fires/YYYY/"' -- {} \;
	# For MVT MRF
	oe_vectorgen -c /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/MODIS_C5_fires_vt.xml
	#Create data archive directories and copy MRF files
	mkdir -p /usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/{2016,YYYY}
	/bin/cp /usr/share/onearth/demo/generated_mrfs/MODIS_C5_fires/output_dir/* /usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/2016
	find /usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/2016/ -name 'MODIS_C5_fires2016110*' -type f -exec bash -c 'ln -s "$1" "${1/2016110/TTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/2016/ -name 'MODIS_C5_firesTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/YYYY/"' -- {} \;
	/bin/cp /usr/share/onearth/demo/data/EPSG3857/MODIS_C5_fires/2016/MODIS_C5_fires2016110_.mrf /etc/onearth/config/headers/MODIS_C5_firesTTTTTTT_.mrf

#Terra_Orbit_Dsc_Dots
	#Copy image files and set up MRF process dirs
	mkdir -p /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/{source_images,working_dir,logfile_dir,output_dir,empty_tiles}
	/bin/cp /usr/share/onearth/demo/source_images/terra_2016-03-04_epsg4326_points_descending.* /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/source_images/
	/bin/cp /usr/share/onearth/demo/vector_configs/Terra_Orbit_Dsc_Dots*.xml /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/
	cd /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/
	# For Shapefile
	oe_vectorgen -c /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/Terra_Orbit_Dsc_Dots.xml
	#Create data archive directories and copy MRF files
	mkdir -p /usr/share/onearth/demo/data/shapefiles/Terra_Orbit_Dsc_Dots/{2016,YYYY}
	/bin/cp /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/output_dir/* /usr/share/onearth/demo/data/shapefiles/Terra_Orbit_Dsc_Dots/2016/
	find /usr/share/onearth/demo/data/shapefiles/Terra_Orbit_Dsc_Dots/2016/ -name 'Terra_Orbit_Dsc_Dots2016064*' -type f -exec bash -c 'ln -s "$1" "${1/2016064/TTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/shapefiles/Terra_Orbit_Dsc_Dots/2016/ -name 'Terra_Orbit_Dsc_DotsTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/shapefiles/Terra_Orbit_Dsc_Dots/YYYY/"' -- {} \;
	# For MVT MRF
	oe_vectorgen -c /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/Terra_Orbit_Dsc_Dots_vt.xml
	#Create data archive directories and copy MRF files
	mkdir -p /usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/{2016,YYYY}
	/bin/cp /usr/share/onearth/demo/generated_mrfs/Terra_Orbit_Dsc_Dots/output_dir/* /usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/2016
	find /usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/2016/ -name 'Terra_Orbit_Dsc_Dots2016064*' -type f -exec bash -c 'ln -s "$1" "${1/2016064/TTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/2016/ -name 'Terra_Orbit_Dsc_DotsTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/YYYY/"' -- {} \;
	/bin/cp /usr/share/onearth/demo/data/EPSG3857/Terra_Orbit_Dsc_Dots/2016/Terra_Orbit_Dsc_Dots2016064_.mrf /etc/onearth/config/headers/Terra_Orbit_Dsc_DotsTTTTTTT_.mrf

#Set up and copy the pre-made MRFs
declare -a MRF_PROJS=(arctic antarctic)
declare -a MRF_EPSGS=(EPSG3413 EPSG3031)
for INDEX in {0..1}
do
	 mkdir -p /usr/share/onearth/demo/data/${MRF_EPSGS[$INDEX]}/blue_marble
	 /bin/cp /usr/share/onearth/demo/data/${MRF_EPSGS[$INDEX]}/blue_marble/blue_marble.mrf /etc/onearth/config/headers/blue_marble_${MRF_PROJS[$INDEX]}.mrf
done

#ASCAT-L2-25km
	mkdir -p /usr/share/onearth/demo/data/EPSG3857/ASCATA-L2-25km/YYYY
	find /usr/share/onearth/demo/data/EPSG3857/ASCATA-L2-25km/2016 -name 'ASCATA-L2-25km2016188010000*' -type f -exec bash -c 'ln -s "$1" "${1/2016188010000/TTTTTTTTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/EPSG3857/ASCATA-L2-25km/2016 -name 'ASCATA-L2-25kmTTTTTTTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/EPSG3857/ASCATA-L2-25km/YYYY/"' -- {} \;
	/bin/cp /usr/share/onearth/demo/data/EPSG3857/ASCATA-L2-25km/2016/ASCATA-L2-25km2016188010000_.mrf /etc/onearth/config/headers/ASCATA-L2-25kmTTTTTTTTTTTTT_.mrf

#OSCAR
	mkdir -p /usr/share/onearth/demo/data/EPSG3857/oscar/YYYY
	find /usr/share/onearth/demo/data/EPSG3857/oscar/2016 -name 'oscar2016189*' -type f -exec bash -c 'ln -s "$1" "${1/2016189/TTTTTTT}"' -- {} \;
	find /usr/share/onearth/demo/data/EPSG3857/oscar/2016 -name 'oscarTTTTTTT*' -type l -exec bash -c 'mv "$1" "/usr/share/onearth/demo/data/EPSG3857/oscar/YYYY/"' -- {} \;
	/bin/cp /usr/share/onearth/demo/data/EPSG3857/oscar/2016/oscar2016189_.mrf /etc/onearth/config/headers/oscarTTTTTTT_.mrf

#Install and copy the Mapserver config files and endpoints
mkdir -p /etc/onearth/config/styles
/bin/cp /usr/share/onearth/demo/styles/* /etc/onearth/config/styles

#Compile the KML script and copy to TWMS dirs
cd /usr/share/onearth/apache/kml
for PROJECTION in "${PROJECTIONS[@]}"
do
	 make WEB_HOST=localhost:${HOST_PORT:-80}/onearth/twms/$PROJECTION
	 /bin/cp kmlgen.cgi /usr/share/onearth/demo/examples/default/twms/$PROJECTION/kmlgen.cgi
	 rm -f kmlgen.cgi
done

#Activate index.html and cache configurations
/bin/cp /usr/share/onearth/demo/examples/default/index.html.sample /usr/share/onearth/demo/examples/default/index.html
sed -i 's/#WMSCache/WMSCache/g' /etc/httpd/conf.d/onearth-demo.conf

#Copy layer config files, run config tool
/bin/cp /usr/share/onearth/demo/layer_configs/* /etc/onearth/config/layers/
LCDIR=/etc/onearth/config oe_configure_layer --create_mapfile --layer_dir=/etc/onearth/config/layers/ --skip_empty_tiles --generate_links
/usr/sbin/httpd -k restart
