# This Dockerfile must be run from source root
FROM nasagibs/onearth-deps:2.7.0

ARG GDAL_VERSION=2.4.4
ARG GDAL_RELEASE=5

# Install dependencies
RUN yum install -y proj-8.2.0 proj-devel-8.2.0 geos-3.10.1 mod_lua-2.4.53 fribidi-devel-1.0.10 cairo-devel-1.17.4 cmake-3.20.2 geos-devel-3.10.1 harfbuzz-devel-2.7.4 fcgi-devel-2.4.0 protobuf-c-devel-1.3.3 && \
	yum clean all

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install --upgrade pip
RUN pip install -r onearth/requirements.txt

# Install GDAL
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-devel-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm" \
                   "https://github.com/nasa-gibs/mrf/releases/download/v${GDAL_VERSION}-${GDAL_RELEASE}/gibs-gdal-apps-${GDAL_VERSION}-${GDAL_RELEASE}.el9.x86_64.rpm"
RUN pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

WORKDIR /tmp
RUN wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin && \
    cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Build RGBApng2Palpng
WORKDIR /home/oe2/onearth/src/mrfgen
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

# Pillow at least 8.1.0 
RUN pip install --user Pillow==8.1.0

RUN python3 -m pip install --user --upgrade cython
RUN python3 setup.py build_ext --inplace

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
    install -m 755 src/colormaps/bin/SLDtoColorMap.py -D /usr/bin/SLDtoColorMap.py && \
    install -m 755 src/vectorgen/oe_vectorgen.py -D /usr/bin/oe_vectorgen && \
    install -m 755 src/vectorgen/oe_create_mvt_mrf.py -D /usr/bin/oe_create_mvt_mrf.py && \
    install -m 755 src/scripts/oe_sync_s3_idx.py -D /usr/bin/oe_sync_s3_idx.py && \
    install -m 755 src/scripts/oe_sync_s3_configs.py -D /usr/bin/oe_sync_s3_configs.py && \
    install -m 755 docker/wms_service/oe2_wms_configure.py -D /usr/bin/oe2_wms_configure.py && \
    install -m 755 src/modules/time_service/utils/oe_periods_configure.py -D /usr/bin/oe_periods_configure.py

# Remove unneeded kernel headers
RUN yum remove -y kernel-headers kernel-debug-devel

ARG ONEARTH_VERSION
ENV ONEARTH_VERSION=$ONEARTH_VERSION
