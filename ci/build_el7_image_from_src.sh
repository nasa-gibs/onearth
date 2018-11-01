#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

rm -rf Dockerfile

#DOCKER_UID=$(id -u)
#DOCKER_GID=$(id -g)

cat > Dockerfile <<EOS
FROM centos:7

RUN yum groupinstall -y "Development Tools"

RUN yum install -y epel-release lua-devel jansson-devel libpng-devel libjpeg-devel pcre-devel mod_proxy mod_ssl wget openssl-devel libyaml-devel python-devel
RUN yum install -y luarocks
RUN yum install -y redis
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u python36u-pip python36u-devel
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v1.1.2/gibs-gdal-2.1.4-1.el7.centos.x86_64.rpm"
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v1.1.2/gibs-gdal-devel-2.1.4-1.el7.centos.x86_64.rpm"
RUN yum install -y ImageMagick

RUN pip3.6 install requests
RUN pip3.6 install pyaml
RUN pip3.6 install lxml
RUN pip3.6 install pypng

RUN yum install -y libcurl-devel mod_proxy mod_ssl python-pip sqlite libxml2 turbojpeg turbojpeg-devel agg agg-devel pyparsing python-tornado python-pycxx-devel python-dateutil python-pypng python-lxml python-nose python-unittest2 python-matplotlib

RUN pip install apacheconfig
RUN pip install numpy==1.10.4

# Install vectorgen dependencies
RUN yum install -y libxml2-devel libxslt-devel chrpath
WORKDIR /tmp
RUN wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig
RUN pip install Fiona==1.7.0 Shapely==1.5.16 Rtree==0.8.3 mapbox-vector-tile==0.4.0 lxml==3.8.0

# Install GDAL 2
# WORKDIR /tmp
# RUN wget http://download.osgeo.org/gdal/2.3.2/gdal-2.3.2.tar.gz
# RUN tar xzf gdal-2.3.2.tar.gz
# WORKDIR gdal-2.3.2
# RUN ./configure
# RUN make && make install

RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Download RPM source for Apache, configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp
RUN yum install -y yum-utils rpm-build
RUN yumdownloader --source httpd
RUN HOME="/tmp" rpm -ivh httpd-2.4.6-80.el7.centos.1.src.rpm
RUN yum-builddep -y httpd
WORKDIR /tmp/rpmbuild/SPECS
RUN HOME="/tmp" rpmbuild -bp httpd.spec
##COPY http_rpm_spec.patch /home/oe2/onearth/docker/http_rpm_spec.patch
##COPY mod_proxy_http.patch /tmp/rpmbuild/SOURCES
RUN cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES
RUN patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch
RUN HOME="/tmp" rpmbuild -ba httpd.spec
RUN yum -y remove httpd httpd-devel httpd-tools
#RUN ls /tmp/rpmbuild/RPMS/x86_64/
RUN rpm -ivh /tmp/rpmbuild/RPMS/x86_64/httpd*.rpm
RUN rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm

#RUN wget https://archive.apache.org/dist/httpd/httpd-2.4.6.tar.gz
#RUN tar xf httpd-2.4.6.tar.gz
#WORKDIR /tmp/httpd-2.4.6
#RUN patch -p0 < /home/oe2/onearth/ci/mod_proxy_http.patch
#RUN ./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared
#RUN make && make install
#RUN cp /tmp/httpd/modules/mod_proxy* /etc/httpd/modules/

# Install APR patch
WORKDIR /tmp
RUN wget http://apache.osuosl.org//apr/apr-1.6.5.tar.gz
RUN tar xf apr-1.6.5.tar.gz
WORKDIR /tmp/apr-1.6.5
RUN patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch
RUN ./configure --prefix=/lib64
RUN make && make install
# libtoolT error (rm: no such file or directory)

# Install dependencies
#WORKDIR /home/oe2/onearth

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_reproject/src/
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
RUN cp /home/oe2/onearth/src/modules/mod_reproject/src/mod_reproject.h .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

# Some environments don't like git:// links, so we need to workaround that with certain lua dependencies
WORKDIR /tmp
RUN git clone https://github.com/jiyinyiyong/json-lua.git
WORKDIR /tmp/json-lua/
RUN sed -i 's/git:/https:/' json-lua-0.1-3.rockspec
RUN luarocks make json-lua-0.1-3.rockspec

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_snap/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_snap
RUN luarocks make onearth-0.1-1.rockspec

# Install GC Service configs
RUN mkdir -p /etc/onearth/config/endpoint
RUN cp -R /home/oe2/onearth/src/modules/gc_service/conf /etc/onearth/config/
WORKDIR /home/oe2/onearth/src/modules/gc_service
RUN luarocks make onearth_gc_gts-0.1-1.rockspec

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Build RGBApng2Palpng
WORKDIR /home/oe2/onearth/src/mrfgen
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

# Install OnEarth utilties, etc.
WORKDIR /home/oe2/onearth/
#RUN install -m 755 -d /usr/lib64/httpd/bin
#RUN install -m 755 src/modules/mod_onearth/oe_create_cache_config /usr/bin/oe_create_cache_config
#RUN install -m 755 src/layer_config/bin/oe_configure_layer.py -D /usr/bin/oe_configure_layer
RUN install -m 755 src/empty_tile/oe_generate_empty_tile.py -D /usr/bin/oe_generate_empty_tile.py
#RUN install -m 755 src/onearth_logs/onearth_logs.py -D /usr/bin/onearth_metrics
RUN install -m 755 src/generate_legend/oe_generate_legend.py -D /usr/bin/oe_generate_legend.py
RUN install -m 755 src/mrfgen/mrfgen.py -D /usr/bin/mrfgen
RUN install -m 755 src/mrfgen/colormap2vrt.py -D /usr/bin/colormap2vrt.py
RUN install -m 755 src/mrfgen/overtiffpacker.py -D /usr/bin/overtiffpacker.py
RUN install -m 755 src/mrfgen/RGBApng2Palpng -D /usr/bin/RGBApng2Palpng
RUN install -m 755 src/mrfgen/oe_validate_palette.py -D /usr/bin/oe_validate_palette.py
RUN install -m 755 src/scripts/oe_utils.py -D /usr/bin/oe_utils.py
#RUN install -m 755 src/scripts/oe_configure_reproject_layer.py -D /usr/bin/oe_configure_reproject_layer.py
RUN install -m 755 src/scripts/oe_validate_configs.py -D /usr/bin/oe_validate_configs.py
RUN install -m 755 src/scripts/read_idx.py -D /usr/bin/read_idx.py
RUN install -m 755 src/scripts/read_mrf.py -D /usr/bin/read_mrf.py
RUN install -m 755 src/scripts/read_mrfdata.py -D /usr/bin/read_mrfdata.py
RUN install -m 755 src/scripts/twmsbox2wmts.py -D /usr/bin/twmsbox2wmts.py
RUN install -m 755 src/scripts/wmts2twmsbox.py -D /usr/bin/wmts2twmsbox.py
RUN install -m 755 src/colormaps/bin/colorMaptoHTML.py -D /usr/bin/colorMaptoHTML.py
RUN install -m 755 src/colormaps/bin/colorMaptoSLD.py -D /usr/bin/colorMaptoSLD.py
RUN install -m 755 src/colormaps/bin/SLDtoColorMap.py -D /usr/bin/SLDtoColorMap.py
RUN install -m 755 src/vectorgen/oe_vectorgen.py -D /usr/bin/oe_vectorgen
RUN install -m 755 src/vectorgen/oe_create_mvt_mrf.py -D /usr/bin/oe_create_mvt_mrf.py

# Set Apache to Debug mode for performance logging
RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
RUN perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D /g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
RUN cp /home/oe2/onearth/ci/00-mpm.conf /etc/httpd/conf.modules.d/
RUN cp /home/oe2/onearth/ci/10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/ci
CMD sh start_ci2.sh
EOS

docker build \
  --tag "$TAG" \
  ./

rm Dockerfile
