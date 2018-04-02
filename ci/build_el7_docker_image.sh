#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
TAG="$1"

if [ -z "$TAG" ]; then
  echo "Usage: ${SCRIPT_NAME} TAG" >&2
  exit 1
fi

rm -rf dist && mkdir -p dist

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

#yum install -y centos-release-scl
yum groupinstall -y "Development Tools"

#yum install -y \
#  @buildsys-build \
#  devtoolset-3-toolchain \
#  gcc-c++ \
#  geos-devel \
#  giflib-devel \
#  git \
#  libcurl-devel \
#  libjpeg-turbo-devel \
#  libtool \
#  libxml++-devel \
#  pcre-devel \
#  rsync \
#  swig \
#  wget \
#  yum-utils

yum install -y \
  epel-release \
  lua-devel \
  jansson-devel \
  libpng-devel \
  libjpeg-devel \
  pcre-devel

yum install -y \
  luarocks \
  redis \
  libcurl-devel \
  wget

mkdir -p /build
rsync -av \
  /source/ /build/

chown -R root:root /build

# Install mod_proxy patch
cd /tmp
wget https://archive.apache.org/dist/httpd/httpd-2.4.6.tar.gz
tar xf httpd-2.4.6.tar.gz
cd /tmp/httpd-2.4.6
patch -p0 < /build/ci/mod_proxy_http.patch
./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared
make && make install

# Install APR patch
cd /tmp
wget http://apache.osuosl.org//apr/apr-1.6.3.tar.gz
tar xf apr-1.6.3.tar.gz
cd /tmp/apr-1.6.3
patch  -p2 < /build/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch
./configure --prefix=/lib64
make && make install
# libtoolT error (rm: no such file or directory)

(
  set -evx
  cd /build
  git submodule update --init --recursive
  yum-builddep -y ci/onearth.spec

  # Install Apache modules
  cd /build/src/modules/mod_receive/src/
  cp /build/ci/Makefile.lcl .
  make && make install

  cd /build/src/modules/mod_mrf/src/
  cp /build/ci/Makefile.lcl .
  make && make install

  cd /build/src/modules/mod_reproject/src/
  cp /build/ci/Makefile.lcl .
  make && make install

  cd /build/src/modules/mod_twms/src/
  cp /build/ci/Makefile.lcl .
  make && make install

  cd /build/src/modules/mod_ahtse_lua/src/
  cp /build/ci/Makefile.lcl .
  make && make install

  cd /build/src/modules/mod_wmts_wrapper
  cp /build/ci/Makefile.lcl .
  cp /build/src/modules/mod_reproject/src/mod_reproject.h .
  make && make install

# Install Lua module for time snapping
  cd /build/src/modules/time_snap/redis-lua
  luarocks make rockspec/redis-lua-2.0.5-0.rockspec
  cd /build/src/modules/time_snap
  luarocks make onearth-0.1-1.rockspec

# Set Apache to Debug mode for performance logging
  perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
  perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D /g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
  cp 00-mpm.conf /etc/httpd/conf.modules.d/
  cp 10-worker.conf /etc/httpd/conf.modules.d/
#  make download
#  scl enable devtoolset-3 "make onearth-rpm"
#  make onearth-rpm
)

cp /build/dist/onearth-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/onearth-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  "centos:7" /dist/build_rpms.sh
#  "$(cat docker/el7/gibs-gdal-image.txt)" /dist/build_rpms.sh

rm dist/build_rpms.sh
