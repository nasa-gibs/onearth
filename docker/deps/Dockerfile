# This Dockerfile must be run from source root

# This version of the Dockerfile packs commands together to minimize layers and
# to minimize image size.

FROM rockylinux:9.1

# Install dependencies
RUN yum -y update && \
    yum groupinstall -y "Development Tools" && \
    yum clean all && \
    dnf config-manager --set-enabled crb && \
	dnf install -y epel-release && \
    dnf install -y \
        lua-devel-5.4.2 \
        jansson-devel-2.14 \
        libpng-devel-1.6.37 \
        pcre-devel-8.44 \
        wget-1.21.1 \
        libyaml-devel-0.2.5 \
        libcurl-devel-7.76.1 \
        libjpeg-turbo-devel-2.0.90 \
        libxml2-devel-2.9.13 \
        mod_ssl-2.4.53 \
        openssl-devel-3.0.1 \
        luarocks-3.9.1 \
        redis-6.2.7 \
        cronie-1.5.7 \
        logrotate-3.18.0 \
        python3-devel-3.9.14 \
        mod_lua-2.4.53 \
        parallel && \
    dnf clean all

# Silence the parallel citation
RUN echo 'will cite' | parallel --citation || true

# Install yq
WORKDIR /opt
RUN wget https://github.com/mikefarah/yq/releases/download/v4.2.0/yq_linux_amd64.tar.gz -O - |\
  tar xz && mv yq_linux_amd64 /usr/bin/yq

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install --upgrade pip
RUN pip install -r onearth/docker/deps/requirements.txt

# Download RPM source for Apache, configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp
RUN yum install -y yum-utils-4.1.0 rpm-build-4.16.1.3 && \
    yum clean all && \
    yumdownloader --source httpd-2.4.53-7.el9.x86_64 && \
    HOME="/tmp" rpm -ivh httpd-*.src.rpm && \
    yum-builddep -y httpd-2.4.53-7.el9.x86_64

# Install APR patch
RUN wget http://archive.apache.org/dist/apr/apr-1.7.0.tar.gz && \
    tar xf apr-1.7.0.tar.gz && \
    cd /tmp/apr-1.7.0 && \
    patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch && \
    ./configure --prefix=/usr/local/apr --with-ldap && \
    make && make install

RUN wget http://archive.apache.org/dist/apr/apr-util-1.6.1.tar.gz && \
    tar xf apr-util-1.6.1.tar.gz && \
    cd /tmp/apr-util-1.6.1 && \
    ./configure --prefix=/usr/local/apr --with-apr=/usr/local/apr --with-ldap && \
    make && make install

WORKDIR /tmp/rpmbuild/SPECS
RUN sed -i 's:--with-apr=%{_prefix}:--with-apr=/usr/local/apr/bin/apr-1-config:g' httpd.spec && \
    sed -i 's:--with-apr-util=%{_prefix}:--with-apr-util=/usr/local/apr/bin/apu-1-config:g' httpd.spec && \
    HOME="/tmp" rpmbuild -bp httpd.spec && \
    ls /home/oe2/onearth && \
    cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES && \
    cp /home/oe2/onearth/docker/proxypass_nomain_flag.patch /tmp/rpmbuild/SOURCES && \
    patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch && \
    HOME="/tmp" rpmbuild -ba httpd.spec && \
    yum -y remove httpd httpd-devel httpd-tools && \
    yum -y install system-logos-httpd /etc/mime.types sscg httpd-filesystem-2.4.53 && \
    yum clean all && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/httpd*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm  && \
    cd / && rm -rf /tmp/apr-1.7.0* /tmp/apr-util-1.6.1* /tmp/httpd-2.4.53* /tmp/rpmbuild*

WORKDIR /home/oe2
RUN rm -rf ./onearth
