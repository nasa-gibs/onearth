# This Dockerfile must be run from source root

# This version of the Dockerfile packs commands together to minimize layers and
# to minimize image size.

FROM centos:7

# Install dependencies
RUN yum -y update && \
    yum clean all && \
    yum groupinstall -y "Development Tools" && \
    yum install -y epel-release-7-11 https://repo.ius.io/ius-release-el7.rpm && \
    yum install -y \
        lua-devel-5.1.4 \
        jansson-devel-2.10 \
        libpng-devel-1.5.13 \
        pcre-devel-8.32 \
        wget-1.14 \
        libyaml-devel-0.1.4 \
        libcurl-devel-7.29.0 \
        libjpeg-turbo-devel-1.2.90 \
        libxml2-2.9.1 \
        libxml2-devel-2.9.1 \
        mod_ssl \
        openssl-devel \
        luarocks-2.3.0 \
        redis6 \
        python36-3.6.8 \
        python36-devel-3.6.8 \
        python36-pip-9.0.1 \
        cronie \
        logrotate \
        parallel && \
    pip3.6 install \
        requests==2.7.0 \
        pyaml==18.11.0 \
        lxml==4.9.1 \
        pypng==0.0.20 \
        boto3==1.9 \
        redis==3.5.3 \
        urllib3==1.26.6 && \
    yum clean all

# Silence the parallel citation
RUN parallel --citation <<< $'will cite\n'

# Install yq
WORKDIR /opt
RUN wget https://github.com/mikefarah/yq/releases/download/v4.2.0/yq_linux_amd64.tar.gz -O - |\
  tar xz && mv yq_linux_amd64 /usr/bin/yq

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Download RPM source for Apache, configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp
RUN yum install -y yum-utils-1.1.31 rpm-build-4.11.3 && \
    yum clean all && \
    yumdownloader --source httpd-2.4.6-97.el7.centos.5.x86_64 && \
    HOME="/tmp" rpm -ivh httpd-*.src.rpm && \
    yum-builddep -y httpd-2.4.6-97.el7.centos.5.x86_64

# Install APR patch
WORKDIR /tmp
RUN wget http://archive.apache.org/dist/apr/apr-1.7.0.tar.gz && \
    tar xf apr-1.7.0.tar.gz && \
    cd /tmp/apr-1.7.0 && \
    patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch && \
    ./configure --prefix=/usr/local/apr --with-ldap && \
    make && make install

WORKDIR /tmp
RUN wget http://archive.apache.org/dist/apr/apr-util-1.6.1.tar.gz && \
    tar xf apr-util-1.6.1.tar.gz && \
    cd /tmp/apr-util-1.6.1 && \
    ./configure --prefix=/usr/local/apr --with-apr=/usr/local/apr --with-ldap && \
    make && make install

WORKDIR /tmp/rpmbuild/SPECS
RUN sed -i 's/{?dist}.5/{?dist}_9.5/g' httpd.spec && \
    sed -i 's:--with-apr=%{_prefix}:--with-apr=/usr/local/apr/bin/apr-1-config:g' httpd.spec && \
    sed -i 's:--with-apr-util=%{_prefix}:--with-apr-util=/usr/local/apr/bin/apu-1-config:g' httpd.spec && \
    HOME="/tmp" rpmbuild -bp httpd.spec && \
    ls /home/oe2/onearth && \
    cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES && \
    cp /home/oe2/onearth/docker/proxypass_nomain_flag.patch /tmp/rpmbuild/SOURCES && \
    patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch && \
    HOME="/tmp" rpmbuild -ba httpd.spec && \
    yum -y remove httpd httpd-devel httpd-tools && \
    yum clean all && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/httpd*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm  && \
    cd / && rm -rf /tmp/apr-1.7.0* /tmp/apr-util-1.6.1* /tmp/httpd-2.4.6* /tmp/rpmbuild* 

# Set the locale
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /home/oe2
RUN rm -rf ./onearth
