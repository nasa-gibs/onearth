# This Dockerfile must be run from source root

FROM centos:7

# Upgrade all existing packages
RUN yum -y update && yum clean all

# Install dependencies
RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release-7-11 lua-devel-5.1.4 jansson-devel-2.10 libpng-devel-1.5.13 pcre-devel-8.32 wget-1.14 libyaml-devel-0.1.4 libcurl-devel-7.29.0 python-devel-2.7.5 libjpeg-turbo-devel-1.2.90 libxml2-2.9.1 libxml2-devel-2.9.1
RUN yum install -y mod_ssl openssl-devel
RUN yum install -y luarocks-2.3.0
RUN yum install -y https://repo.ius.io/ius-release-el7.rpm
RUN yum install -y redis5
RUN yum install -y python36-3.6.8 python36-devel-3.6.8 python36-pip-9.0.1
RUN yum install -y cronie

#Install pip 3.6 dependencies
RUN pip3.6 install requests==2.21.0
RUN pip3.6 install pyaml==18.11.0
RUN pip3.6 install lxml==4.3.0
RUN pip3.6 install pypng==0.0.19
RUN pip3.6 install boto3==1.9
RUN pip3.6 install redis==3.5.3

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
RUN ls /home/oe2/onearth
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
RUN rm -rf ./onearth
RUN rm -rf /tmp/