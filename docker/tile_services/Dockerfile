# This Dockerfile must be run from source root

ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

RUN mkdir -p /var/www

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_twms/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_convert/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2
RUN git clone https://github.com/lucianpls/libahtse.git
WORKDIR /home/oe2/libahtse
RUN git checkout 709d15cbc7100daa02640a42c82f0eec6e85df6b
WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_png/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_brunsli/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/
RUN cp /home/oe2/onearth/src/colormaps/bin/colorMaptoHTML_v1.0.py /usr/bin/
RUN cp /home/oe2/onearth/src/colormaps/bin/colorMaptoHTML_v1.3.py /usr/bin/

# Copy Apache configs
COPY ./docker/tile_services/oe2_proxy.conf /etc/httpd/conf.d/
COPY ./docker/tile_services/oe2_status.conf /etc/httpd/conf.d/
COPY ./docker/tile_services/oe2_ancillary.conf /etc/httpd/conf.d/

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/ && \
    cp oe2_ssl.conf /etc/httpd/conf.d/
    
# Create OnEarth config log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

# Setup cron for logrotate
RUN cp /home/oe2/onearth/docker/logrotate /etc/cron.hourly/ && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

RUN mkdir /onearth && mkdir -p /etc/onearth

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
    dnf clean all
RUN pip uninstall -y pip

# SSL certs
WORKDIR /home/oe2/onearth/
RUN /usr/libexec/httpd-ssl-gencerts
RUN touch /etc/pki/tls/private/onearth.crt && \
    touch /etc/pki/tls/private/onearth.key && \
    touch /etc/pki/tls/private/onearth.pass
RUN chown www-data:www-data /etc/pki/tls/private/* && chmod 755 /etc/pki/tls/private/*
# Prepare pass phrase process
RUN echo '#!/bin/sh' >> /usr/bin/pass.sh && \
	echo 'cat /etc/pki/tls/private/onearth.pass' >> /usr/bin/pass.sh && \
    chmod +x /usr/bin/pass.sh

# Change user
USER www-data

WORKDIR /home/oe2/onearth/docker/tile_services
CMD sh start_tile_services.sh "$S3_URL" "$REDIS_HOST" "$REDIS_HOST_READER" "$IDX_SYNC" "$DEBUG_LOGGING" "$S3_CONFIGS" "$GENERATE_COLORMAP_HTML" "$SERVER_STATUS" "$USE_SSL" "$SERVER_NAME"

#interval:30s, timeout:30s, start-period:30s, retries:3
HEALTHCHECK --start-period=30s \
  CMD curl --fail http://localhost/oe-status/Raster_Status/default/2004-08-01/16km/0/0/0.jpeg || exit 1 