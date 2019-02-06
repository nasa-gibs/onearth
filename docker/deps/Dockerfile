# This Dockerfile must be run from source root

FROM centos:7

RUN yum groupinstall -y "Development Tools"

RUN yum install -y epel-release-7-11 lua-devel-5.1.4 jansson-devel-2.10 libpng-devel-1.5.13 pcre-devel-8.32 wget-1.14 libyaml-devel-0.1.4 libcurl-devel-7.29.0 python-devel-2.7.5 libjpeg-turbo-devel-1.2.90
RUN yum install -y mod_ssl openssl-devel
RUN yum install -y luarocks-2.3.0
RUN yum install -y redis-3.2.12
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u-3.6.7 python36u-devel-3.6.7 python36u-pip-9.0.1
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v1.1.2/gibs-gdal-2.1.4-1.el7.centos.x86_64.rpm"
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v1.1.2/gibs-gdal-devel-2.1.4-1.el7.centos.x86_64.rpm"

RUN pip3.6 install requests==2.21.0
RUN pip3.6 install pyaml==18.11.0
RUN pip3.6 install lxml==4.3.0
RUN pip3.6 install pypng==0.0.19

RUN yum install -y python-backports-1.0 python-backports-ssl_match_hostname-3.5.0.1
RUN yum install -y python2-pip-8.1.2 sqlite-3.7.17 libxml2-2.9.1 turbojpeg-1.2.90 turbojpeg-devel-1.2.90 agg-2.5 agg-devel-2.5 pyparsing-1.5.6 python-tornado-4.2.1 python-pycxx-devel-6.2.4 python-dateutil-1.5 python-pypng-0.0.16 python-lxml-3.2.1 python-nose-1.3.7 python-unittest2-1.1.0 python-matplotlib-1.2.0

RUN pip install apacheconfig==0.2.8
RUN pip install numpy==1.10.4

# Install vectorgen dependencies
RUN yum install -y libxml2-devel-2.9.1 libxslt-devel-1.1.28 chrpath-0.16
WORKDIR /tmp
RUN wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
RUN tar xzf spatialindex-src-1.8.5.tar.gz
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig
RUN pip install Fiona==1.7.0 Shapely==1.5.16 Rtree==0.8.3 mapbox-vector-tile==0.4.0 lxml==3.8.0

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Download RPM source for Apache, configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp
RUN yum install -y yum-utils-1.1.31 rpm-build-4.11.3
RUN yumdownloader --source httpd-2.4.6
RUN HOME="/tmp" rpm -ivh httpd-*.src.rpm
RUN yum-builddep -y httpd-2.4.6
WORKDIR /tmp/rpmbuild/SPECS
RUN HOME="/tmp" rpmbuild -bp httpd.spec
RUN cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES
RUN patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch
RUN HOME="/tmp" rpmbuild -ba httpd.spec
RUN yum -y remove httpd httpd-devel httpd-tools
RUN rpm -ivh /tmp/rpmbuild/RPMS/x86_64/httpd*.rpm
RUN rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm

# Install APR patch
WORKDIR /tmp
RUN wget http://archive.apache.org/dist/apr/apr-1.6.5.tar.gz
RUN tar xf apr-1.6.5.tar.gz
WORKDIR /tmp/apr-1.6.5
RUN patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch
RUN ./configure --prefix=/lib64
RUN make && make install

WORKDIR /home/oe2