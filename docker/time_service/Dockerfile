# This Dockerfile must be run from source root

ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:$ONEARTH_VERSION

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/tiye/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-4.rockspec
RUN luarocks make json-lua-0.1-4.rockspec

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_service/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_service
RUN luarocks make onearth_time_service-0.1-2.rockspec

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/
WORKDIR /home/oe2/onearth/docker/time_service

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/time_service/utils/oe_periods_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/time_service/utils/oe_scrape_time.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/time_service/utils/periods.lua /usr/bin/
RUN cp /home/oe2/onearth/src/modules/time_service/utils/best.lua /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/

# Create OnEarth config log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

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

# Remove unneeded kernel headers
RUN yum remove -y kernel-headers kernel-debug-devel

# Remove python2 and link python3
RUN rm /usr/bin/python && \
    ln -s /usr/bin/python3 /usr/bin/python

# Change user
USER www-data

CMD sh start_time_service.sh $S3_URL $REDIS_HOST $DEBUG_LOGGING $FORCE_TIME_SCRAPE $S3_CONFIGS

#interval:30s, timeout:30s, start-period:30s, retries:3
HEALTHCHECK --start-period=30s \
  CMD curl --fail http://localhost/oe2-time-service-proxy-onearth-time-service || exit 1 