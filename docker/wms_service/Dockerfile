ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

RUN yum install -y proj-epsg-4.8.0 proj-devel-4.8.0 fribidi-devel-1.0.2 cairo-devel-1.15.12 cmake-2.8.12.2 geos-devel-3.4.2 harfbuzz-devel-1.7.5 fcgi-devel-2.4.0 protobuf-c-devel-1.0.2 && \
	yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-2/gibs-gdal-2.4.4-2.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-2/gibs-gdal-devel-2.4.4-2.el7.x86_64.rpm" && \
	yum clean all

COPY ./ /home/oe2/onearth/

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/tiye/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-4.rockspec
RUN luarocks make json-lua-0.1-4.rockspec

# Install wms_time_service module
RUN mkdir -p /etc/onearth/config/endpoint
WORKDIR /home/oe2/onearth/src/modules/wms_time_service
RUN luarocks make onearth_wms_time-0.1-1.rockspec

# FastCGI module
WORKDIR /tmp
RUN wget --no-check-certificate https://www.apache.org/dist/httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz
RUN tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install

# Mapserver
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-7.4.4.tar.gz
RUN tar xf mapserver-7.4.4.tar.gz
WORKDIR /tmp/mapserver-7.4.4
# Remove patch after upgrading to mapserver 8. Fix for seg faults https://github.com/MapServer/MapServer/pull/6385
COPY docker/wms_service/mapserv.patch /tmp/mapserver-7.4.4/
RUN patch mapserv.c mapserv.patch
RUN mkdir build
WORKDIR /tmp/mapserver-7.4.4/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 -DWITH_KML=1 -DWITH_PROTOBUFC=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v
RUN rm -rf /tmp/*

# Install layer configuration tools
RUN cp /home/oe2/onearth/docker/wms_service/oe2_wms_configure.py /usr/bin/
RUN cp /home/oe2/onearth/docker/wms_service/template.map /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/
	
# Copy setups
COPY docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/
COPY docker/wms_service/oe2_status.conf /etc/httpd/conf.d/
COPY docker/cors.conf /etc/httpd/conf.d/
RUN cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi
RUN mkdir -p /etc/onearth/config/mapserver
COPY docker/wms_service/fonts.txt /etc/onearth/config/mapserver/
COPY docker/wms_service/symbols.sym /etc/onearth/config/mapserver/
COPY docker/wms_service/fonts/* /usr/share/fonts/
RUN mkdir /var/log/mapserver && touch /var/log/mapserver/error.log && chmod 777 /var/log/mapserver/error.log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

COPY docker/wms_service/logrotate.daily.mapserver /etc/logrotate.d/mapserver
COPY docker/logrotate.daily.onearth /etc/logrotate.d/onearth

# Setup cron for logrotate
RUN mv /etc/cron.daily/logrotate /etc/cron.hourly/logrotate && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.12/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=048b95b48b708983effb2e5c935a1ef8483d9e3e

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

RUN mkdir /onearth

# Add non-root user
RUN groupadd www-data && useradd -g www-data www-data
RUN chmod 755 -R /etc/pki && chmod 1777 /tmp && chown -hR www-data:www-data /etc/httpd/ && chown -hR www-data:www-data /run/httpd/ && \
    chown -hR www-data:www-data /var/www/ && chown -hR www-data:www-data /var/log && \
	chown -hR www-data:www-data /home/oe2 && chown -hR www-data:www-data /onearth && \
	chown -hR www-data:www-data /etc/onearth && \
	chown -hR www-data:www-data /etc/crontab && chown -hR www-data:www-data /var/lib/logrotate

#setcap to bind to privileged ports as non-root
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/httpd && getcap /usr/sbin/httpd

# Remove unneeded kernel headers
RUN yum remove -y kernel-headers kernel-debug-devel

# Remove python2 and link python3
RUN rm /usr/bin/python && \
    ln -s /usr/bin/python3 /usr/bin/python

# Change user
USER www-data

WORKDIR /home/oe2/onearth/docker/wms_service
CMD sh start_wms_service.sh $ENDPOINT_REFRESH $GC_HEALTHCHECK $S3_CONFIGS

#interval:30s, timeout:30s, start-period:60s, retries:3
HEALTHCHECK --start-period=60s \
  CMD curl --fail "http://localhost/wms/oe-status_reproject/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=Raster_Status,Vector_Status&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34" || exit 1 