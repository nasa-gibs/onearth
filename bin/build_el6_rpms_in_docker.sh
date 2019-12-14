#!/bin/sh

set -evx

mkdir -p dist

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y epel-release centos-release-scl

curl -LO https://github.com/nasa-gibs/mrf/releases/download/v1.1.1/mrf-1.1.1.tar.gz
tar -xzf mrf-1.1.1.tar.gz

yum install -y \
  ./gibs-gdal-2.1.2-1.el6.x86_64.rpm \
  ./gibs-gdal-devel-2.1.2-1.el6.x86_64.rpm \
  @buildsys-build \
  devtoolset-7-toolchain \
  geos-devel \
  giflib-devel \
  git \
  libcurl-devel \
  libjpeg-turbo-devel \
  libtool \
  libxml++-devel \
  rsync \
  swig \
  wget \
  yum-utils

mkdir -p /build
rsync -av \
  /source/ /build/

(
  set -evx
  cd /build
  git submodule update --init --recursive
  yum-builddep -y deploy/onearth/onearth.spec
  make download
  scl enable devtoolset-7 "make onearth-rpm"
)

cp /build/dist/onearth-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/onearth-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  centos:6 /dist/build_rpms.sh

rm dist/build_rpms.sh
