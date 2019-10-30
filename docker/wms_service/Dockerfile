FROM nasagibs/onearth-deps:2.2.2

RUN yum install -y proj-epsg-4.8.0 proj-devel-4.8.0 fribidi-devel-1.0.2 cairo-devel-1.15.12 cmake-2.8.12.2 geos-devel-3.4.2 harfbuzz-devel-1.7.5 fcgi-devel-2.4.0 gdal-devel-1.11.4
RUN pip3 install requests==2.21.0 lxml==4.3.0

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
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 -DWITH_KML=1 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v

# Install layer configuration tools
RUN cp /home/oe2/onearth/docker/wms_service/oe2_wms_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/

# Copy setups
COPY docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/
RUN cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi

# Setup cron for logrotate
RUN mkdir -p /etc/cron.hourly &&mv /etc/cron.daily/logrotate /etc/cron.hourly/logrotate && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

WORKDIR /home/oe2/onearth/docker/wms_service
CMD sh start_wms_service.sh $S3_CONFIGS