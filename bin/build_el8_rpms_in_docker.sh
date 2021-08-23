#!/bin/sh

set -e

rm -rf dist && mkdir -p dist

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y epel-release

dnf install -y 'dnf-command(config-manager)'
dnf config-manager --set-enabled powertools
dnf group install -y "Development Tools"
dnf install -y python3

yum install -y \
  gcc-c++ \
  geos-devel \
  git \
  libcurl-devel \
  libjpeg-turbo-devel \
  libtool \
  pcre-devel \
  rsync \
  swig \
  wget \
  yum-utils \
  apr-devel \
  proj-devel \
  python3-devel \
  rpmdevtools \
  libnsl \
  libxml2-devel

wget "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-4/gibs-gdal-2.4.4-4.el8.x86_64.rpm" -P /dist/ 
wget "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-4/gibs-gdal-devel-2.4.4-4.el8.x86_64.rpm" -P /dist/
wget "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-4/gibs-gdal-apps-2.4.4-4.el8.x86_64.rpm" -P /dist/
yum install -y /dist/gibs-gdal-2.4.4-4.el8.x86_64.rpm \
  dist/gibs-gdal-devel-2.4.4-4.el8.x86_64.rpm \
  dist/gibs-gdal-apps-2.4.4-4.el8.x86_64.rpm

mkdir -p /build
rsync -av \
  /source/ /build/

chown -R root:root /build

(
  set -evx
  cd /build
  git submodule update --init --recursive
  dnf builddep -y deploy/onearth/onearth.spec
  make download
  make onearth-rpm
)

rm -f /build/dist/*bz2 /build/dist/*debug*
cp /build/dist/onearth-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/onearth-*.rpm
cd /dist
tar -cvzf onearth-1.4.1-1.el8.tar.gz *.rpm

EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  centos:8 /dist/build_rpms.sh

rm dist/build_rpms.sh
