#!/bin/sh

#Copy reproject apache config
/bin/cp /usr/share/onearth/demo/examples/reproject/reproject-demo.conf /etc/httpd/conf.d/

#Uncomment sample reproject layer config
mv /etc/onearth/config/layers/layer_configuration_file_reproject.xml.sample /etc/onearth/config/layers/layer_configuration_file_reproject.xml

#Run layer config tool
oe_configure_layer --create_mapfile --layer_dir=/etc/onearth/config/layers/ --lcdir=/etc/onearth/config --skip_empty_tiles --generate_links
apachectl restart