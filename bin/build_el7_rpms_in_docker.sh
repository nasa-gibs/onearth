#!/bin/sh

set -e

rm -rf dist && mkdir -p dist

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

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
  yum-utils

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
  "$(cat docker/el7/gibs-gdal-image.txt)" /dist/build_rpms.sh

rm dist/build_rpms.sh
