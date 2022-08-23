# This Dockerfile must be run from source root
FROM nasagibs/onearth-deps:2.6.3

ARG GDAL_VERSION=2.4.4
ARG GDAL_RELEASE=3

# Install mrfgen and OnEarth utils dependencies
RUN yum install -y proj-4.8.0 proj-devel-4.8.0
RUN yum install -y python-backports-1.0 python-backports-ssl_match_hostname-3.5.0.1
RUN yum install -y sqlite-3.7.17 turbojpeg-1.2.90 turbojpeg-devel-1.2.90 agg-2.5 agg-devel-2.5
RUN pip3.6 install apacheconfig==0.2.8 numpy==1.16.6 matplotlib==2.2.5 parse_apache_configs==0.0.2 wheel==0.37.1

# Install wms dependencies
RUN yum install -y fribidi-devel-1.0.2 cairo-devel-1.15.12 cmake-2.8.12.2 geos-devel-3.4.2 harfbuzz-devel-1.7.5 fcgi-devel-2.4.0 protobuf-c-devel-1.0.2

# Install GDAL
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GDAL_RELEASE}.el7.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-devel-${GDAL_VERSION}-${GDAL_RELEASE}.el7.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-apps-${GDAL_VERSION}-${GDAL_RELEASE}.el7.x86_64.rpm"
RUN pip3.6 install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

# Install vectorgen dependencies
RUN yum install -y libxslt-devel-1.1.28 chrpath-0.16 && \
	yum clean all
WORKDIR /tmp
RUN wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig
RUN pip3.6 install protobuf==3.19.4 Fiona==1.8.13 Shapely==1.8.2 Rtree==0.9.7 mapbox-vector-tile==1.2.1

WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/AHTSE/
RUN bash bootstrap.bash

WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_retile/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_twms/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
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
RUN wget http://download.osgeo.org/mapserver/mapserver-7.4.3.tar.gz
RUN tar xf mapserver-7.4.3.tar.gz
WORKDIR /tmp/mapserver-7.4.3
RUN mkdir build
WORKDIR /tmp/mapserver-7.4.3/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 -DWITH_KML=1 -DWITH_PROTOBUFC=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v
RUN rm -rf /tmp/*

# Install GC Service configs
WORKDIR /home/oe2/onearth/src/modules/gc_service
RUN luarocks make onearth_gc_gts-0.1-1.rockspec

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Build RGBApng2Palpng
WORKDIR /home/oe2/onearth/src/mrfgen
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

# Pillow at least 8.1.0 
RUN pip3 install --user Pillow==8.1.0

RUN python3 -m pip install --user --upgrade cython
RUN python3.6 setup.py build_ext --inplace

# Install OnEarth utilties, etc.
WORKDIR /home/oe2/onearth/
RUN install -m 755 src/empty_tile/oe_generate_empty_tile.py -D /usr/bin/oe_generate_empty_tile.py
RUN install -m 755 src/generate_legend/oe_generate_legend.py -D /usr/bin/oe_generate_legend.py
RUN install -m 755 src/mrfgen/mrfgen.py -D /usr/bin/mrfgen
RUN install -m 755 src/mrfgen/RgbPngToPalPng.py -D /usr/bin/RgbPngToPalPng.py
RUN install -m 755 src/mrfgen/RgbToPalLib.pyx -D /usr/bin/RgbToPalLib.pyx
RUN install -m 755 src/mrfgen/setup.py -D /usr/bin/setup.py
RUN install -m 755 src/mrfgen/RgbToPalLib.cpython-36m-x86_64-linux-gnu.so -D /usr/bin/RgbToPalLib.cpython-36m-x86_64-linux-gnu.so
RUN install -m 755 src/mrfgen/colormap2vrt.py -D /usr/bin/colormap2vrt.py
RUN install -m 755 src/mrfgen/overtiffpacker.py -D /usr/bin/overtiffpacker.py
RUN install -m 755 src/mrfgen/RGBApng2Palpng -D /usr/bin/RGBApng2Palpng
RUN install -m 755 src/mrfgen/oe_validate_palette.py -D /usr/bin/oe_validate_palette.py
RUN install -m 755 src/scripts/oe_utils.py -D /usr/bin/oe_utils.py
RUN install -m 755 src/scripts/twmsbox2wmts.py -D /usr/bin/twmsbox2wmts.py
RUN install -m 755 src/scripts/wmts2twmsbox.py -D /usr/bin/wmts2twmsbox.py
RUN install -m 755 src/colormaps/bin/colorMaptoHTML_v1.0.py -D /usr/bin/colorMaptoHTML_v1.0.py
RUN install -m 755 src/colormaps/bin/colorMaptoHTML_v1.3.py -D /usr/bin/colorMaptoHTML_v1.3.py
RUN install -m 755 src/colormaps/bin/colorMaptoSLD.py -D /usr/bin/colorMaptoSLD.py
RUN install -m 755 src/colormaps/bin/SLDtoColorMap.py -D /usr/bin/SLDtoColorMap.py
RUN install -m 755 src/vectorgen/oe_vectorgen.py -D /usr/bin/oe_vectorgen
RUN install -m 755 src/vectorgen/oe_create_mvt_mrf.py -D /usr/bin/oe_create_mvt_mrf.py
RUN install -m 755 src/scripts/oe_sync_s3_idx.py -D /usr/bin/oe_sync_s3_idx.py
RUN install -m 755 src/scripts/oe_sync_s3_configs.py -D /usr/bin/oe_sync_s3_configs.py
RUN install -m 755 docker/wms_service/oe2_wms_configure.py -D /usr/bin/oe2_wms_configure.py
RUN install -m 755 src/modules/time_service/utils/oe_periods_configure.py -D /usr/bin/oe_periods_configure.py

# Copy WMS setups
COPY docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/
RUN cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi
RUN mkdir -p /etc/onearth/config/mapserver
COPY docker/wms_service/fonts.txt /etc/onearth/config/mapserver/
COPY docker/wms_service/symbols.sym /etc/onearth/config/mapserver/
COPY docker/wms_service/fonts/* /usr/share/fonts/
RUN mkdir /var/log/mapserver && touch /var/log/mapserver/error.log && chmod 777 /var/log/mapserver/error.log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log
RUN mkdir /usr/share/proj/ && cp /usr/local/lib64/python3.6/site-packages/fiona/proj_data/epsg /usr/share/proj/

# Set Apache to Debug mode for performance logging
RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
RUN perl -pi -e 's/LogFormat "%h %l %u %t \"%r\" %>s %b/LogFormat "%h %l %u %t \"%r\" %>s %b %D /g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
RUN cp /home/oe2/onearth/ci/00-mpm.conf /etc/httpd/conf.modules.d/
RUN cp /home/oe2/onearth/ci/10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/src/test
RUN pip3.6 install --upgrade pip
RUN pip3.6 install -r requirements.txt

ENV ONEARTH_VERSION=2.6.3

WORKDIR /home/oe2/onearth/ci
CMD sh start_ci2.sh
