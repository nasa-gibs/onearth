# This Dockerfile must be run from source root
FROM almalinux:9.5

ARG MRF_VERSION=3.0.1
ARG GDAL_VERSION=3.6.4
ENV GDAL_VERSION=$GDAL_VERSION
ARG GIBS_GDAL_RELEASE=1
ENV GIBS_GDAL_RELEASE=$GIBS_GDAL_RELEASE

# Install dependencies
RUN dnf -y update && \
    dnf install -y dnf-plugins-core && \
    dnf groupinstall -y "Development Tools" && \
    dnf install -y 'dnf-command(config-manager)' && \
    dnf clean all && \
    dnf config-manager --set-enabled crb && \
	dnf install -y epel-release-9-5.el9 && \
    dnf install -y \
        rpm-build \
        rpmdevtools \
        lua-devel-5.4.4 \
        jansson-devel-2.14 \
        libpng-devel-1.6.37 \
        pcre-devel-8.44 \
        wget-1.21.1 \
        libyaml-devel-0.2.5 \
        libcurl-devel-7.76.1 \
        libjpeg-turbo-devel-2.0.90 \
        libxml2-devel-2.9.13 \
        luarocks-3.9.2 \
        redis-6.2.7 \
        cronie-1.5.7 \
        logrotate-3.18.0 \
        fribidi-devel-1.0.10 \
        cairo-devel-1.17.4 \
        cmake-3.26.5 \
        harfbuzz-devel-2.7.4 \
        fcgi-devel-2.4.0 \
        proj-8.2.0 \
        proj-devel-8.2.0 \
        geos-3.10.1 \
        geos-devel-3.10.1 \
        python3-devel-3.9.19 \
        protobuf-c-devel-1.3.3 && \
	dnf clean all

# libspatialindex
WORKDIR /tmp
RUN wget https://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz 
RUN cd /tmp/spatialindex-src-1.8.5 && \
    ./configure --libdir=/usr/lib64 && \
    make && make install && \
    ldconfig && \
    cd .. && \
    rm -rf /tmp/*


# Install GDAL
ENV LD_LIBRARY_PATH=:/usr/local/lib
WORKDIR /tmp
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}/gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el9.x86_64.rpm && \
    rpm -i gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el9.x86_64.rpm && \
    rm -rf /tmp/*

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

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install -r onearth/docker/deps/requirements.txt
RUN pip install -r onearth/requirements.txt

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin && \
    cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Build RGBApng2Palpng
WORKDIR /home/oe2/onearth/src/mrfgen
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

# pip updates
RUN python3 -m pip install --user cython==3.0.11 
RUN python3 setup.py build_ext --inplace
RUN python3 -m pip install Shapely==2.0.1

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
    install -m 755 src/scripts/oe_sync_s3_idx.py -D /usr/bin/oe_sync_s3_idx.py && \
    install -m 755 src/scripts/oe_sync_s3_configs.py -D /usr/bin/oe_sync_s3_configs.py && \
    install -m 755 src/scripts/oe_sync_s3_shapefiles.py -D /usr/bin/oe_sync_s3_shapefiles.py && \
    install -m 755 docker/wms_service/oe2_wms_configure.py -D /usr/bin/oe2_wms_configure.py && \
    install -m 755 src/modules/time_service/utils/oe_periods_configure.py -D /usr/bin/oe_periods_configure.py && \
    install -m 755 src/modules/time_service/utils/oe_periods_key_converter.py -D /usr/bin/oe_periods_key_converter.py

# Remove unneeded packages
RUN dnf remove -y kernel-headers kernel-debug-devel python3-devel polkit polkit-libs webkit2gtk3-jsc emacs-filesystem && \
    dnf autoremove -y && \
    dnf clean all
RUN pip uninstall -y pip
RUN rm -rf /tmp/*

ARG ONEARTH_VERSION
ENV ONEARTH_VERSION=$ONEARTH_VERSION
