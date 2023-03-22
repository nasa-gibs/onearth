# This Dockerfile must be run from source root

ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

RUN mkdir -p /var/www

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/tiye/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-4.rockspec
RUN luarocks make json-lua-0.1-4.rockspec

WORKDIR /tmp
RUN git clone https://github.com/lunarmodules/luafilesystem.git
WORKDIR /tmp/luafilesystem/
RUN luarocks make luafilesystem-scm-1.rockspec
RUN cp lfs.so /usr/lib64/lua/5.4/posix && cp lfs.so /usr/lib64/lua/5.4/

RUN luarocks install lpeg && luarocks install cqueues && luarocks install openssl
RUN cp /usr/lib/lua/5.4/lpeg.so /usr/lib64/lua/5.4/ && \
    cp /usr/lib/lua/5.4/_cqueues.so /usr/lib64/lua/5.4/

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Install GC Service configs
RUN mkdir -p /etc/onearth/config/endpoint
RUN cp -R /home/oe2/onearth/src/modules/gc_service/conf /etc/onearth/config/
WORKDIR /home/oe2/onearth/src/modules/gc_service
RUN luarocks make onearth_gc_gts-0.1-1.rockspec
RUN cp /usr/lib/lua/5.4/_openssl.so /usr/lib64/lua/5.4/ && \
    cp -r /usr/lib/lua/5.4/md5 /usr/lib64/lua/5.4/ && \
    cp -r /usr/lib/lua/5.4/socket /usr/lib64/lua/5.4/


# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/

# Install additional configuration tools
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/

# Create OnEarth config log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

# Setup cron for logrotate
RUN cp /home/oe2/onearth/docker/logrotate /etc/cron.daily/ && \
    chmod 755 /etc/cron.daily/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.daily.httpd /etc/logrotate.d/httpd

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

# Generate SSL certs
RUN /usr/libexec/httpd-ssl-gencerts
RUN chown www-data /etc/pki/tls/private/localhost.key

# Change user
USER www-data

WORKDIR /home/oe2/onearth/docker/capabilities
CMD sh start_capabilities.sh $S3_URL $REDIS_HOST $DEBUG_LOGGING $S3_CONFIGS
RUN cp -R /home/oe2/onearth/src/demo /var/www/html/

#interval:30s, timeout:30s, start-period:30s, retries:3
HEALTHCHECK --start-period=30s \
  CMD curl --fail http://localhost/wmts/oe-status/wmts.cgi?SERVICE=WMTS&request=GetCapabilities || exit 1