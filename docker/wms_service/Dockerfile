FROM nasagibs/onearth-deps:latest

RUN yum install -y proj-epsg-4.8.0 proj-devel-4.8.0 fribidi-devel-1.0.2 cairo-devel-1.15.12 cmake-2.8.12.2 geos-devel-3.4.2 harfbuzz-devel-1.7.5 fcgi-devel-2.4.0 gdal-devel-1.11.4 python2-pip-8.1.2

COPY ./ /home/oe2/onearth/

# FastCGI module
WORKDIR /tmp
RUN wget https://www.apache.org/dist/httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz
RUN tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install

# Mapserver
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-7.0.7.tar.gz
RUN tar xf mapserver-7.0.7.tar.gz
COPY docker/wms_service/mapwms.patch /tmp/mapserver-7.0.7
WORKDIR /tmp/mapserver-7.0.7
RUN patch < mapwms.patch
RUN mkdir build
WORKDIR /tmp/mapserver-7.0.7/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v

# Copy setups
COPY docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/
RUN cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi

# Setup cron for logrotate
RUN mkdir -p /etc/cron.hourly &&mv /etc/cron.daily/logrotate /etc/cron.hourly/logrotate && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

# Build demo configuration
COPY docker/wms_service/header.map /tmp
COPY docker/wms_service/template.map /tmp
COPY docker/wms_service/make_wms.py /tmp
WORKDIR /tmp
RUN pip install requests==2.21.0 lxml==3.8.0
RUN python make_wms.py /var/www/demo.map

RUN mkdir -p /home/wms_service
COPY docker/wms_service/start_wms_service.sh /home/wms_service
WORKDIR /home/wms_service
CMD sh start_wms_service.sh