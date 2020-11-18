# This Dockerfile must be run from source root

FROM nasagibs/onearth-deps:2.3.1

RUN mkdir -p /var/www

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_twms/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_reproject/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN cp /home/oe2/onearth/src/modules/mod_reproject/src/mod_reproject.h .
RUN make && make install

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Install additional configuration tools
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp 10-worker.conf /etc/httpd/conf.modules.d/ && \
    cp cors.conf /etc/httpd/conf.d/

# Create OnEarth config log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

# Setup cron for logrotate
RUN mkdir -p /etc/cron.hourly && mv /etc/cron.daily/logrotate /etc/cron.hourly/logrotate && \
    chmod 755 /etc/cron.hourly/logrotate && \
    cp /home/oe2/onearth/docker/logrotate.hourly.httpd /etc/logrotate.d/httpd

RUN mkdir /onearth && mkdir -p /etc/onearth

# Add non-root user
RUN groupadd www-data && useradd -g www-data www-data
RUN chmod 755 -R /etc/pki && chown -hR www-data:www-data /etc/httpd/ && chown -hR www-data:www-data /run/httpd/ && \
    chown -hR www-data:www-data /var/www/ && chown -hR www-data:www-data /var/log/httpd/ && \
	chown -hR www-data:www-data /home/oe2 && chown -hR www-data:www-data /onearth && \
	chown -hR www-data:www-data /etc/onearth

#setcap to bind to privileged ports as non-root
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/httpd && getcap /usr/sbin/httpd

# Change user
USER www-data

ENV LANGUAGE=en_US:en

WORKDIR /home/oe2/onearth/docker/reproject
CMD sh start_reproject.sh $DEBUG_LOGGING $S3_CONFIGS