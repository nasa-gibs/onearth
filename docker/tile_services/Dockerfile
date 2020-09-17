# This Dockerfile must be run from source root

FROM nasagibs/onearth-deps:2.3.0

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

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN cp /home/oe2/onearth/src/modules/mod_reproject/src/mod_reproject.h .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2
RUN git clone https://github.com/lucianpls/libahtse.git
WORKDIR /home/oe2/libahtse
RUN git checkout 709d15cbc7100daa02640a42c82f0eec6e85df6b
RUN /usr/bin/cp /usr/lib64/include/apr-1/* /usr/include/apr-1/
WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_png/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py /usr/bin/
RUN cp /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py /usr/bin/
RUN cp /home/oe2/onearth/src/colormaps/bin/colorMaptoHTML.py /usr/bin/

# Copy Apache configs
COPY ./docker/tile_services/oe2_proxy.conf /etc/httpd/conf.d/
COPY ./docker/tile_services/oe2_status.conf /etc/httpd/conf.d/

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

WORKDIR /home/oe2/onearth/docker/tile_services
CMD sh start_tile_services.sh $S3_URL $REDIS_HOST $IDX_SYNC $DEBUG_LOGGING $S3_CONFIGS