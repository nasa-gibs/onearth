#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
BASE_IMG="$1"
TAG="$2"

if [ -z "$TAG" ] || [ -z "$BASE_IMG" ]; then
  echo "Usage: ${SCRIPT_NAME} BASE_IMG TAG" >&2
  exit 1
fi

rm -rf Dockerfile

#DOCKER_UID=$(id -u)
#DOCKER_GID=$(id -g)

cat > Dockerfile <<EOS
FROM ${BASE_IMG}

WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

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
WORKDIR /home/oe2/onearth/src/modules/time_service/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_service
RUN luarocks make onearth_time_service-0.1-1.rockspec

# Install GC Service configs
#RUN mkdir -p /etc/onearth/config/endpoint
#RUN cp -R /home/oe2/onearth/src/modules/gc_service/conf /etc/onearth/config/
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

WORKDIR /home/oe2/onearth/src/test
RUN pip install -r requirements.txt

WORKDIR /home/oe2/onearth/ci
CMD sh start_ci2.sh
EOS

docker build \
  --tag "$TAG" \
  ./

rm Dockerfile
