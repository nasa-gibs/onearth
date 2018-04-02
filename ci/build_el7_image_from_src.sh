#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

rm -rf tmp && mkdir -p tmp

#DOCKER_UID=$(id -u)
#DOCKER_GID=$(id -g)

cat > tmp/Dockerfile <<EOS
FROM centos:7

RUN yum groupinstall -y "Development Tools"

RUN yum install -y epel-release lua-devel jansson-devel httpd-devel libpng-devel libjpeg-devel pcre-devel

RUN yum install -y luarocks redis libcurl-devel mod_proxy mod_ssl wget

RUN mkdir -p /home/oe2
#RUN mkdir -p /var/www

# Clone OnEarth repo
WORKDIR /home/oe2
RUN git clone https://github.com/nasa-gibs/onearth.git
WORKDIR /home/oe2/onearth
RUN git checkout test2.0

#chown -R root:root /home/oe2

# Install mod_proxy patch
WORKDIR /tmp
RUN wget https://archive.apache.org/dist/httpd/httpd-2.4.6.tar.gz
RUN tar xf httpd-2.4.6.tar.gz
WORKDIR /tmp/httpd-2.4.6
RUN patch -p0 < /home/oe2/onearth/ci/mod_proxy_http.patch
RUN ./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared
RUN make && make install
RUN cp /tmp/httpd/modules/mod_proxy* /etc/httpd/modules/

# Install APR patch
WORKDIR /tmp
RUN wget http://apache.osuosl.org//apr/apr-1.6.3.tar.gz
RUN tar xf apr-1.6.3.tar.gz
WORKDIR /tmp/apr-1.6.3
RUN patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch
RUN ./configure --prefix=/lib64
RUN make && make install
# libtoolT error (rm: no such file or directory)

# Install dependencies
WORKDIR /home/oe2/onearth
RUN git submodule update --init --recursive
RUN yum-builddep -y ci/onearth.spec
RUN make download

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

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_snap/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_snap
RUN luarocks make onearth-0.1-1.rockspec

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
#RUN install -m 755 src/mrfgen/RGBApng2Palpng -D /usr/bin/RGBApng2Palpng
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
  --no-cache \
  --tag "$TAG" \
  tmp

rm tmp/Dockerfile
