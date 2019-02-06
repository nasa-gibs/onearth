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

RUN yum install -y python-backports python-backports-ssl_match_hostname
RUN yum install -y libcurl-devel python-pip sqlite libxml2 turbojpeg turbojpeg-devel agg agg-devel pyparsing python-tornado python-pycxx-devel python-dateutil python-pypng python-lxml python-nose python-unittest2 python-matplotlib

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
RUN yumdownloader --source httpd-2.4.6
RUN HOME="/tmp" rpm -ivh httpd-*.src.rpm
RUN yum-builddep -y httpd-2.4.6
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
#RUN patch -p0 < /home/oe2/onearth/docker/mod_proxy_http.patch
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

EOS

docker build \
  --tag "$TAG" \
  ./

rm Dockerfile
