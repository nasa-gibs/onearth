#!/bin/sh

set -e

SCRIPT_NAME=$(basename "$0")
DOCKER_IMAGE="$1"

if [ -z "$DOCKER_IMAGE" ]; then
  echo "Usage: ${SCRIPT_NAME} DOCKER_IMAGE" >&2
  exit 1
fi

mkdir -p dist

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y centos-release-scl

yum install -y \
  @buildsys-build \
  devtoolset-3-toolchain \
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
  --exclude src/modules/mod_receive \
  --exclude src/modules/mod_reproject \
  --exclude src/modules/mod_twms \
  /source/ /build/

(
  set -evx
  cd /build
  git submodule update --init --recursive
  yum-builddep -y deploy/onearth/onearth.spec
  make download
  scl enable devtoolset-3 "make onearth-rpm"
)

cp /build/dist/onearth-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/onearth-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --env "DOCKER_UID=$(id -u)" \
  --env "DOCKER_GID=$(id -g)" \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  "$DOCKER_IMAGE" /dist/build_rpms.sh

rm dist/build_rpms.sh
