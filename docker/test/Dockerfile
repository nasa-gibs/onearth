# This Dockerfile must be run from source root
FROM nasagibs/onearth-deps:2.8.10

ARG MRF_VERSION=3.0.1
ARG GDAL_VERSION=3.6.4
ENV GDAL_VERSION=$GDAL_VERSION
ARG GIBS_GDAL_RELEASE=1
ENV GIBS_GDAL_RELEASE=$GIBS_GDAL_RELEASE

# Install dependencies
RUN dnf install -y \
        proj-8.2.0 \
        proj-devel-8.2.0 \
        fribidi-devel-1.0.10 \
        cairo-devel-1.17.4 \
        cmake-3.26.5 \
        geos-3.13.1 \
        geos-devel-3.13.1 \
        harfbuzz-devel-2.7.4 \
        fcgi-devel-2.4.0 \
        protobuf-c-devel-1.3.3 && \
	dnf clean all

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/tiye/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-4.rockspec && \
    luarocks make json-lua-0.1-4.rockspec

WORKDIR /tmp
RUN git clone https://github.com/lunarmodules/luafilesystem.git
WORKDIR /tmp/luafilesystem/
RUN luarocks make luafilesystem-scm-1.rockspec && \
    cp lfs.so /usr/lib64/lua/5.4/posix && cp lfs.so /usr/lib64/lua/5.4/

RUN luarocks install lpeg && luarocks install cqueues && luarocks install openssl

# FastCGI module
WORKDIR /tmp
RUN wget https://downloads.apache.org/httpd/mod_fcgid/mod_fcgid-2.3.9.tar.gz && \
    tar xf mod_fcgid-2.3.9.tar.gz
WORKDIR /tmp/mod_fcgid-2.3.9
RUN APXS=/usr/bin/apxs ./configure.apxs
RUN make && make install

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2/onearth
WORKDIR /home/oe2/onearth
COPY requirements.txt .

# Install pip dependencies
RUN pip install -r requirements.txt

# libspatialindex
WORKDIR /tmp
RUN wget https://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz
RUN cd /tmp/spatialindex-src-1.8.5 && \
    ./configure --libdir=/usr/lib64 && \
    make && make install && \
    ldconfig && \
    cd ..

# Install GDAL
#RUN pip install --force-reinstall numpy
ENV LD_LIBRARY_PATH=:/usr/local/lib
WORKDIR /tmp
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el9.x86_64.rpm && \
    rpm -i gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el9.x86_64.rpm && \
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
WORKDIR /tmp
RUN wget http://download.osgeo.org/mapserver/mapserver-8.2.2.tar.gz && \
    tar xf mapserver-8.2.2.tar.gz
WORKDIR /tmp/mapserver-8.2.2
RUN mkdir build
WORKDIR /tmp/mapserver-8.2.2/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_POSTGIS=0 -DWITH_GIF=0 -DWITH_KML=1 -DWITH_PROTOBUFC=0 ../
RUN make && make install
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/mapserver.conf
RUN ldconfig -v

RUN rm -rf /tmp/*
WORKDIR /home/oe2/onearth
COPY . .

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_retile/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_twms/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_brunsli/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl . && \
    make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_convert/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl . && \
    make && make install

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_service/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_service
RUN luarocks make onearth_time_service-0.1-2.rockspec

# Install wms_time_service module
RUN mkdir -p /etc/onearth/config/endpoint
WORKDIR /home/oe2/onearth/src/modules/wms_time_service
RUN luarocks make onearth_wms_time-0.1-1.rockspec

# Install GC Service configs
WORKDIR /home/oe2/onearth/src/modules/gc_service
RUN luarocks make onearth_gc_gts-0.1-1.rockspec

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin && \
    cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Build RGBApng2Palpng
WORKDIR /home/oe2/onearth/src/mrfgen
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

# pip updates
RUN python3 -m pip install --user cython==3.0.11 
RUN python3 setup.py build_ext --inplace
#Removed Shapely as it is already installed
RUN python3 -m pip install moto[server]==4.2.7 werkzeug==3.0.1

# Install OnEarth utilties, etc.
WORKDIR /home/oe2/onearth/
RUN install -m 755 src/empty_tile/oe_generate_empty_tile.py -D /usr/bin/oe_generate_empty_tile.py && \
    install -m 755 src/generate_legend/oe_generate_legend.py -D /usr/bin/oe_generate_legend.py && \
    install -m 755 src/mrfgen/mrfgen.py -D /usr/bin/mrfgen && \
    install -m 755 src/mrfgen/RgbPngToPalPng.py -D /usr/bin/RgbPngToPalPng.py && \
    install -m 755 src/mrfgen/RgbToPalLib.pyx -D /usr/bin/RgbToPalLib.pyx && \
    install -m 755 src/mrfgen/setup.py -D /usr/bin/setup.py && \
    install -m 755 src/mrfgen/RgbToPalLib.cpython-39-x86_64-linux-gnu.so -D /usr/bin/RgbToPalLib.cpython-39-x86_64-linux-gnu.so && \
    install -m 755 src/mrfgen/colormap2vrt.py -D /usr/bin/colormap2vrt.py && \
    install -m 755 src/mrfgen/overtiffpacker.py -D /usr/bin/overtiffpacker.py && \
    install -m 755 src/mrfgen/RGBApng2Palpng -D /usr/bin/RGBApng2Palpng && \
    install -m 755 src/mrfgen/oe_validate_palette.py -D /usr/bin/oe_validate_palette.py && \
    install -m 755 src/scripts/oe_utils.py -D /usr/bin/oe_utils.py && \
    install -m 755 src/scripts/twmsbox2wmts.py -D /usr/bin/twmsbox2wmts.py && \
    install -m 755 src/scripts/wmts2twmsbox.py -D /usr/bin/wmts2twmsbox.py && \
    install -m 755 src/colormaps/bin/colorMaptoHTML_v1.0.py -D /usr/bin/colorMaptoHTML_v1.0.py && \
    install -m 755 src/colormaps/bin/colorMaptoHTML_v1.3.py -D /usr/bin/colorMaptoHTML_v1.3.py && \
    install -m 755 src/colormaps/bin/colorMaptoSLD.py -D /usr/bin/colorMaptoSLD.py && \
    install -m 755 src/colormaps/bin/colorMaptoTXT.py -D /usr/bin/colorMaptoTXT.py && \
    install -m 755 src/colormaps/bin/SLDtoColorMap.py -D /usr/bin/SLDtoColorMap.py && \
    install -m 755 src/vectorgen/oe_vectorgen.py -D /usr/bin/oe_vectorgen && \
    install -m 755 src/vectorgen/oe_create_mvt_mrf.py -D /usr/bin/oe_create_mvt_mrf.py && \
    install -m 755 src/vectorgen/oe_json_to_uvtile.py -D /usr/bin/oe_json_to_uvtile && \
    install -m 755 src/scripts/oe_sync_s3_idx.py -D /usr/bin/oe_sync_s3_idx.py && \
    install -m 755 src/scripts/oe_sync_s3_configs.py -D /usr/bin/oe_sync_s3_configs.py && \
    install -m 755 src/scripts/oe_sync_s3_shapefiles.py -D /usr/bin/oe_sync_s3_shapefiles.py && \
    install -m 755 docker/wms_service/oe2_wms_configure.py -D /usr/bin/oe2_wms_configure.py && \
    install -m 755 src/modules/time_service/utils/oe_periods_configure.py -D /usr/bin/oe_periods_configure.py

# Copy WMS setups
RUN cp /home/oe2/onearth/docker/wms_service/oe2_wms.conf /etc/httpd/conf.d/ && \
    cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi && \
    cp /home/oe2/onearth/docker/wms_service/mapserver.conf /usr/local/etc/mapserver.conf
RUN mkdir -p /etc/onearth/config/mapserver
RUN cp /home/oe2/onearth/docker/wms_service/fonts.txt /etc/onearth/config/mapserver/ && \
    cp /home/oe2/onearth/docker/wms_service/symbols.sym /etc/onearth/config/mapserver/ && \
    cp /home/oe2/onearth/docker/wms_service/fonts/* /usr/share/fonts/
RUN mkdir /var/log/mapserver && touch /var/log/mapserver/error.log && chmod 777 /var/log/mapserver/error.log
RUN mkdir /var/log/onearth && touch /var/log/onearth/config.log && chmod 777 /var/log/onearth/config.log

# Set Apache to Debug mode for performance logging
RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf && \
    perl -pi -e 's/LogFormat "%h %l %u %t \"%r\" %>s %b/LogFormat "%h %l %u %t \"%r\" %>s %b %D /g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
RUN cp /home/oe2/onearth/docker/00-mpm.conf /etc/httpd/conf.modules.d/ && \
    cp /home/oe2/onearth/docker/10-worker.conf /etc/httpd/conf.modules.d/

ENV ONEARTH_VERSION=2.8.10

# Generate SSL certs
RUN /usr/libexec/httpd-ssl-gencerts

WORKDIR /home/oe2/onearth/ci
CMD sh start_ci2.sh
