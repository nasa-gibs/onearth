# This Dockerfile must be run from source root

# This version of the Dockerfile packs commands together to minimize layers and
# to minimize image size.

FROM almalinux:9.3

# Install dependencies
RUN dnf -y update && \
    dnf groupinstall -y "Development Tools" && \
    dnf clean all && \
    dnf config-manager --set-enabled crb && \
	dnf install -y epel-release-9-5.el9 && \
    dnf install -y \
        lua-devel-5.4.4 \
        jansson-devel-2.14 \
        libpng-devel-1.6.37 \
        pcre-devel-8.44 \
        wget-1.21.1 \
        libyaml-devel-0.2.5 \
        libcurl-devel-7.76.1 \
        libjpeg-turbo-devel-2.0.90 \
        libxml2-devel-2.9.13 \
        mod_ssl-2.4.57-11.el9_4.1 \
        openssl-devel-3.0.7 \
        luarocks-3.9.2 \
        redis-6.2.7 \
        cronie-1.5.7 \
        logrotate-3.18.0 \
        python3-devel-3.9.18 \
        cmake-3.26.5 \
        parallel && \
    dnf clean all

# Silence the parallel citation
RUN echo 'will cite' | parallel --citation || true

# Install yq
WORKDIR /tmp
RUN wget https://github.com/mikefarah/yq/releases/download/v4.44.3/yq_linux_amd64.tar.gz -O - |\
  tar xz && mv yq_linux_amd64 /usr/bin/yq && rm -rf *

# Install supercronic
WORKDIR /tmp
RUN wget https://go.dev/dl/go1.23.2.linux-amd64.tar.gz && \
    tar xf go1.23.2.linux-amd64.tar.gz && \
    mv go /usr/local/ && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    wget https://github.com/aptible/supercronic/archive/refs/tags/v0.2.33.tar.gz && \
    tar xf v0.2.33.tar.gz && \
    cd supercronic-0.2.33 && \
    sed -i 's/386 arm arm64//g' build.sh && \
    go mod tidy && \
    go mod vendor && \
    sh build.sh && \
    mv dist/supercronic-linux-amd64 /usr/local/bin/ && \
    ln -s /usr/local/bin/supercronic-linux-amd64 /usr/local/bin/supercronic

# Clean prometheus client_golang
WORKDIR /root/go/pkg/mod/github.com/prometheus/
RUN cd client_golang@v1.20.2 && \
    go mod tidy && \
    go clean -modcache && \
    cd /tmp/ && \
    rm -rf /tmp/* && \
    rm -rf /usr/local/go /usr/local/bin/go

# Install brunsli dependency
WORKDIR /tmp
RUN git clone --depth=1 https://github.com/google/brunsli.git && \
    cd brunsli && \
    git submodule update --init --recursive && \
    cmake -DCMAKE_PREFIX_PATH=/usr/local/ -DCMAKE_INSTALL_PREFIX=/usr/local/ -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release -B out && \
    cmake --build out --config Release && \
    cd out && make && make install && \
    export LD_LIBRARY_PATH=:/usr/local/lib && \
    ldconfig && \
    cd /tmp/ && rm -rf /tmp/brunsli

# Download RPM source for Apache
WORKDIR /tmp
RUN dnf install -y yum-utils-4.3.0 rpm-build-4.16.1.3 && \
    dnf clean all && \
    yumdownloader --source httpd-2.4.57-11.el9_4.1.x86_64 && \
    HOME="/tmp" rpm -ivh httpd-*.src.rpm && \
    yum-builddep -y httpd-2.4.57-11.el9_4.1.x86_64

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install -r onearth/docker/deps/requirements.txt

WORKDIR /tmp

# Install APR patch
RUN wget http://archive.apache.org/dist/apr/apr-1.7.4.tar.gz && \
    tar xf apr-1.7.4.tar.gz && \
    cd /tmp/apr-1.7.4 && \
    patch  -p2 < /home/oe2/onearth/src/modules/mod_mrf/apr_FOPEN_RANDOM.patch && \
    ./configure --prefix=/usr/local/apr && \
    make && make install

WORKDIR /tmp
RUN wget http://archive.apache.org/dist/apr/apr-util-1.6.3.tar.gz && \
    tar xf apr-util-1.6.3.tar.gz && \
    cd /tmp/apr-util-1.6.3 && \
    ./configure --prefix=/usr/local/apr --with-apr=/usr/local/apr --with-ldap && \
    make && make install
    
# Configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp/rpmbuild/SPECS
RUN sed -i 's:--with-apr=%{_prefix}:--with-apr=/usr/local/apr/bin/apr-1-config:g' httpd.spec && \
    sed -i 's:--with-apr-util=%{_prefix}:--with-apr-util=/usr/local/apr/bin/apu-1-config:g' httpd.spec && \
    sed -i 's/{?dist}.1/{?dist}_4.1/g' httpd.spec && \
    HOME="/tmp" rpmbuild -bp httpd.spec && \
    ls /home/oe2/onearth && \
    cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES && \
    cp /home/oe2/onearth/docker/proxypass_nomain_flag.patch /tmp/rpmbuild/SOURCES && \
    patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch && \
    HOME="/tmp" rpmbuild -ba httpd.spec && \
    yum -y remove httpd httpd-devel httpd-tools && \
    yum -y install system-logos-httpd /etc/mime.types sscg && \
    yum clean all && \
    rpm -ivh /tmp/rpmbuild/RPMS/*/httpd*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_lua*.rpm && \
    cd / && rm -rf /tmp/apr-1.7.4* /tmp/apr-util-1.6.3* /tmp/httpd-2.4.57* /tmp/rpmbuild*

# Install mod_receive
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/ci/Makefile.lcl .
RUN make && make install

# Generate SSL certs for bootstrap to complete
RUN /usr/libexec/httpd-ssl-gencerts

# Install AHTSE dependencies
WORKDIR /home/oe2/onearth/src/modules/AHTSE/
RUN bash bootstrap.bash

RUN dnf remove -y cmake && \
    dnf clean all

WORKDIR /home/oe2
RUN rm -rf ./onearth /tmp/*
