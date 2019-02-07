# This Dockerfile must be run from source root

FROM nasagibs/onearth-deps:2.2.1

RUN mkdir -p /var/www

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

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/
RUN cp 10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/docker/capabilities
CMD sh start_capabilities.sh $S3_URL $REDIS_HOST
RUN cp -R /home/oe2/onearth/src/demo /var/www/html/