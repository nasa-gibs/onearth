FROM centos:7
RUN yum install -y epel-release
RUN yum groupinstall -y "Development Tools"
RUN yum install -y httpd-devel libpng-devel libjpeg-devel proj-epsg proj-devel fribidi-devel cairo-devel cmake geos-devel libcurl-devel libxml2-devel harfbuzz-devel fcgi-devel wget python-pip gdal-devel

# FastCGI module
WORKDIR /tmp
RUN wget http://download.nextag.com/apache//httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz
RUN tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install

# Mapserver
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-7.0.7.tar.gz
RUN tar xf mapserver-7.0.7.tar.gz
COPY mapwms.patch /tmp/mapserver-7.0.7
WORKDIR /tmp/mapserver-7.0.7
RUN patch < mapwms.patch
RUN mkdir build
WORKDIR /tmp/mapserver-7.0.7/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v

# Copy setups
COPY oe2_wms.conf /etc/httpd/conf.d/
RUN cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi

# Build demo configuration
COPY header.map /tmp
COPY template.map /tmp
COPY make_wms.py /tmp
WORKDIR /tmp
RUN pip install requests lxml
RUN python make_wms.py /var/www/demo.map

RUN mkdir -p /home/wms_service
COPY start_wms_service.sh /home/wms_service
WORKDIR /home/wms_service
CMD sh start_wms_service.sh