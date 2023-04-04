ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

ARG GDAL_VERSION=2.4.4
ARG GDAL_RELEASE=5

RUN yum install -y proj-8.2.0 proj-devel-8.2.0 geos-3.10.1 fribidi-devel-1.0.10 cairo-devel-1.17.4 cmake-3.20.2 geos-devel-3.10.1 harfbuzz-devel-2.7.4 fcgi-devel-2.4.0 protobuf-c-devel-1.3.3 && \
	yum clean all

COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install --upgrade pip
RUN pip install -r onearth/requirements.txt

# Install GDAL
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-devel-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-apps-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm"
RUN pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

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

# Install lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/lunarmodules/luafilesystem.git
WORKDIR /tmp/luafilesystem/
RUN luarocks make luafilesystem-scm-1.rockspec
RUN cp lfs.so /usr/lib64/lua/5.4/posix && cp lfs.so /usr/lib64/lua/5.4/
RUN luarocks install lpeg && \
    luarocks install cqueues && \
    luarocks install openssl && \
    luarocks install md5 && \
    luarocks install luasocket
RUN cp /usr/lib/lua/5.4/lpeg.so /usr/lib64/lua/5.4/ && \
    cp /usr/lib/lua/5.4/_cqueues.so /usr/lib64/lua/5.4/

# Install wms_time_service module
RUN mkdir -p /etc/onearth/config/endpoint
WORKDIR /home/oe2/onearth/src/modules/wms_time_service
RUN luarocks make onearth_wms_time-0.1-1.rockspec
RUN cp /usr/lib/lua/5.4/_openssl.so /usr/lib64/lua/5.4/ && \
    cp -r /usr/lib/lua/5.4/md5 /usr/lib64/lua/5.4/ && \
    cp -r /usr/lib/lua/5.4/socket /usr/lib64/lua/5.4/

# FastCGI module
WORKDIR /tmp
RUN wget --no-check-certificate https://www.apache.org/dist/httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz
RUN tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install

# Mapserver
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-8.0.0.tar.gz
RUN tar xf mapserver-8.0.0.tar.gz
WORKDIR /tmp/mapserver-8.0.0
RUN mkdir build
WORKDIR /tmp/mapserver-8.0.0/build
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

# Copy WMS setups
RUN cp /home/oe2/onearth/docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/ && \
    cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi && \
    cp /home/oe2/onearth/docker/wms_service/mapserver.conf /usr/local/etc/mapserver.conf && \
    cp /home/oe2/onearth/docker/wms_service/oe2_status.conf /etc/httpd/conf.d/
RUN mkdir -p /etc/onearth/config/mapserver
RUN cp /home/oe2/onearth/docker/wms_service/fonts.txt /etc/onearth/config/mapserver/ && \
    cp /home/oe2/onearth/docker/wms_service/symbols.sym /etc/onearth/config/mapserver/ && \
    cp /home/oe2/onearth/docker/wms_service/fonts/* /usr/share/fonts/
RUN mkdir /var/log/mapserver && touch /var/log/mapserver/error.log && chmod 777 /var/log/mapserver/error.log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log


COPY docker/wms_service/logrotate.daily.mapserver /etc/logrotate.d/mapserver
COPY docker/logrotate.daily.onearth /etc/logrotate.d/onearth

# Setup cron for logrotate
RUN cp /home/oe2/onearth/docker/logrotate /etc/cron.hourly/ && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

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

# Remove unneeded packages
RUN yum remove -y kernel-headers kernel-debug-devel python3-devel polkit polkit-libs webkit2gtk3-jsc && \
    yum autoremove && \
    yum clean all

# Generate SSL certs
RUN /usr/libexec/httpd-ssl-gencerts
RUN chown www-data /etc/pki/tls/private/localhost.key

# Change user
USER www-data

WORKDIR /home/oe2/onearth/docker/wms_service
CMD sh start_wms_service.sh $ENDPOINT_REFRESH $GC_HEALTHCHECK $S3_CONFIGS

#interval:30s, timeout:30s, start-period:60s, retries:3
HEALTHCHECK --start-period=60s \
  CMD curl --fail "http://localhost/wms/oe-status_reproject/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=Raster_Status,Vector_Status&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34" || exit 1 