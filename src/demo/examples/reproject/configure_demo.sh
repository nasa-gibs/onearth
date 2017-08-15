#!/bin/sh

#Copy reproject apache config
/bin/cp /usr/share/onearth/demo/examples/reproject/demo-reproject.conf /etc/httpd/conf.d/

#Comment out conflicting configurations
sed -i 's/Alias \/onearth\/twms\/epsg3857/#Alias \/onearth\/twms\/epsg3857/g' /etc/httpd/conf.d/onearth-demo.conf

#Move conflicting .cgi files
mv /usr/share/onearth/demo/examples/default/wmts/epsg3857/wmts.cgi /usr/share/onearth/demo/examples/default/wmts/epsg3857/wmts.cgi.bak
mv /usr/share/onearth/demo/examples/default/twms/epsg3857/wmts.cgi /usr/share/onearth/demo/examples/default/twms/epsg3857/twms.cgi.bak

#Uncomment sample reproject layer config
mv /etc/onearth/config/layers/layer_configuration_file_reproject.xml.sample /etc/onearth/config/layers/layer_configuration_file_reproject.xml

#Run layer config tool
oe_configure_layer --create_mapfile --layer_dir=/etc/onearth/config/layers/ --lcdir=/etc/onearth/config --skip_empty_tiles --generate_links
/usr/sbin/httpd -k restart