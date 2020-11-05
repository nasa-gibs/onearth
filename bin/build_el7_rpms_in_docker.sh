#!/bin/sh

set -e

rm -rf dist && mkdir -p dist

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y epel-release

yum install -y \
  @buildsys-build \
  gcc-c++ \
  geos-devel \
  giflib-devel \
  git \
  libcurl-devel \
  libjpeg-turbo-devel \
  libtool \
  libxml++-devel \
  pcre-devel \
  rsync \
  swig \
  wget \
  yum-utils \
  apr-devel \
  proj-devel \
  python3-devel
  
yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-2.4.4-1.el7.x86_64.rpm" \
  "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-devel-2.4.4-1.el7.x86_64.rpm"
 

mkdir -p /build
rsync -av \
  /source/ /build/

chown -R root:root /build

(
  set -evx
  cd /build
  git submodule update --init --recursive
  yum-builddep -y deploy/onearth/onearth.spec
  make download
  make onearth-rpm
)

cp /build/dist/onearth-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/onearth-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  centos:7 /dist/build_rpms.sh

rm dist/build_rpms.sh
