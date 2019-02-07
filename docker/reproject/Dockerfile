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

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/
RUN cp 10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/docker/reproject
CMD sh start_reproject.sh