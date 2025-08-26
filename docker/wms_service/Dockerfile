ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

ARG MRF_VERSION=3.0.1
ARG GDAL_VERSION=3.6.4
ARG ALMALINUX_VERSION=10
ENV GDAL_VERSION=$GDAL_VERSION
ARG GIBS_GDAL_RELEASE=3
ENV GIBS_GDAL_RELEASE=$GIBS_GDAL_RELEASE

RUN dnf install -y \
        proj-9.5.0 \
        proj-devel-9.5.0 \
        fribidi-devel-1.0.14 \
        cairo-devel-1.18.2 \
        cmake-3.30.5 \
        geos-3.13.0 \
        geos-devel-3.13.0 \
        harfbuzz-devel-8.4.0 \
        protobuf-c-devel-1.5.0 && \
	dnf clean all

# FastCGI
RUN cd /tmp && \
    wget https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/Packages/f/fcgi-2.4.0-52.el10_1.x86_64.rpm && \
    wget https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/Packages/f/fcgi-devel-2.4.0-52.el10_1.x86_64.rpm && \
    dnf install -y ./fcgi-2.4.0-52.el10_1.x86_64.rpm ./fcgi-devel-2.4.0-52.el10_1.x86_64.rpm && \
	dnf clean all

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/tiye/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-4.rockspec && \
  luarocks make json-lua-0.1-4.rockspec

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

# FastCGI module
WORKDIR /tmp
RUN wget https://downloads.apache.org/httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz
RUN tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install


COPY ./ /home/oe2/onearth/
WORKDIR /home/oe2/onearth

# Remove dependency that conflicts with older version in OnEarth requirements.txt
RUN dnf remove -y python3-dateutil

# Install pip dependencies
RUN pip install pip==25.1.1
RUN pip install -r requirements.txt

# Install GDAL
#RUN pip install --force-reinstall numpy
ENV LD_LIBRARY_PATH=:/usr/local/lib
WORKDIR /tmp
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}-${GIBS_GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rpm -i gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

# Fix outdated packaging installed in this environment. It does not support the "strip_trailing_zero" argument in
# canonicalize_version, which was causing GDAL build error
RUN dnf remove -y python3-packaging || echo "python3-packaging was not found or removal failed, attempting to continue."
RUN pip install --force-reinstall 'packaging>=25.0'

RUN pip install --global-option=build_ext --global-option="-I/usr/local/include/gdal" GDAL==`gdal-config --version`

# Install mrf_apps
RUN git clone --depth 1 --branch v${MRF_VERSION} https://github.com/nasa-gibs/mrf.git && \
    curl "https://raw.githubusercontent.com/OSGeo/gdal/v${GDAL_VERSION}/frmts/mrf/marfa.h" -o /usr/local/include/marfa.h && \
    cd mrf/mrf_apps/ && \
    echo $'PREFIX=/usr/local\nGDAL_ROOT=/usr/local/include/' >> Makefile.lcl && \
    sed -i 's/mrf_insert jxl/mrf_insert/g' Makefile && \
    sed -i 's/papszOptions) override/papszOptions)/g' /usr/local/include/marfa.h && \
    make && make install && \
    ldconfig && \
    cp *.py /usr/bin/ && \
    cd /tmp/ && \
    rm -rf /tmp/*

# Mapserver
RUN dnf install -y harfbuzz-devel-8.4.0 cairo-devel-1.18.2
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-8.2.2.tar.gz
RUN tar xf mapserver-8.2.2.tar.gz
WORKDIR /tmp/mapserver-8.2.2
RUN mkdir build
WORKDIR /tmp/mapserver-8.2.2/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 -DWITH_KML=1 -DWITH_PROTOBUFC=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v
RUN rm -rf /tmp/*

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Install wms_time_service module
RUN mkdir -p /etc/onearth/config/endpoint
WORKDIR /home/oe2/onearth/src/modules/wms_time_service
RUN luarocks make onearth_wms_time-0.1-1.rockspec

# Install layer configuration tools
RUN cp /home/oe2/onearth/docker/wms_service/oe2_wms_configure.py /usr/bin/
RUN cp /home/oe2/onearth/docker/wms_service/template.map /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_shapefiles.py /usr/bin/

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/ && \
    cp oe2_ssl.conf /etc/httpd/conf.d/

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
RUN dnf remove -y kernel-headers kernel-debug-devel python3-devel polkit polkit-libs webkit2gtk3-jsc emacs-filesystem && \
    dnf autoremove -y && \
    dnf clean all && \
    rm -rf /tmp/*
RUN pip uninstall -y pip

# SSL certs
WORKDIR /home/oe2/onearth/
RUN /usr/libexec/httpd-ssl-gencerts
RUN touch /etc/pki/tls/private/onearth.crt && \
    touch /etc/pki/tls/private/onearth.key && \
    touch /etc/pki/tls/private/onearth.pass
RUN chown www-data:www-data /etc/pki/tls/private/* && chmod 755 /etc/pki/tls/private/*
RUN echo '#!/bin/sh' >> /usr/bin/pass.sh && \
	echo 'cat /etc/pki/tls/private/onearth.pass' >> /usr/bin/pass.sh && \
    chmod +x /usr/bin/pass.sh

# Change user
USER www-data

WORKDIR /home/oe2/onearth/docker/wms_service
CMD sh start_wms_service.sh "$ENDPOINT_REFRESH" "$GC_HEALTHCHECK" "$S3_CONFIGS" "$SHAPEFILE_SYNC" "$USE_LOCAL_SHAPEFILES" "$SERVER_STATUS" "$USE_SSL" "$SERVER_NAME"

#interval:30s, timeout:30s, start-period:60s, retries:3
HEALTHCHECK --start-period=60s \
  CMD curl --fail "http://localhost/wms/oe-status_reproject/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=Raster_Status,Vector_Status&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34" || exit 1
