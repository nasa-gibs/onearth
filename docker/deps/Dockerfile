# This Dockerfile must be run from source root

# This version of the Dockerfile packs commands together to minimize layers and
# to minimize image size.

FROM almalinux:10.0

# Install dependencies
RUN dnf -y update && \
    dnf groupinstall -y "Development Tools" && \
    dnf install -y 'dnf-command(config-manager)' && \
    dnf install -y 'almalinux-release-devel' && \
    dnf clean all && \
    dnf config-manager --set-enabled crb && \
    dnf config-manager --set-enabled devel && \
	dnf install -y epel-release-10-6.el10 && \
    dnf install -y \
        lua-devel-5.4.6 \
        jansson-devel-2.14 \
        libpng-devel-1.6.40 \
        pcre2-devel-10.44 \
        wget-1.24.5 \
        libyaml-devel-0.2.5 \
        libcurl-devel-8.9.1 \
        libjpeg-turbo-devel-3.0.2 \
        libxml2-devel-2.12.5 \
        mod_ssl-2.4.63-1.el10 \
        openssl-devel-3.2.2 \
        luarocks-3.9.2 \
        redis-7.2.4 \
        cronie-1.7.0 \
        logrotate-3.22.0 \
        python3-devel-3.12.9 \
        cmake-3.30.5 \
        parallel && \
    dnf clean all

# Silence the parallel citation
RUN echo 'will cite' | parallel --citation || true

# Install supercronic
WORKDIR /tmp
RUN wget https://go.dev/dl/go1.24.5.linux-amd64.tar.gz && \
    tar xf go1.24.5.linux-amd64.tar.gz && \
    mv go /usr/local/ && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    wget https://github.com/aptible/supercronic/archive/refs/tags/v0.2.34.tar.gz && \
    tar xf v0.2.34.tar.gz && \
    cd supercronic-0.2.34 && \
    sed -i 's/386 arm arm64//g' build.sh && \
    go mod tidy && \
    go mod vendor && \
    sh build.sh && \
    mv dist/supercronic-linux-amd64 /usr/local/bin/ && \
    ln -s /usr/local/bin/supercronic-linux-amd64 /usr/local/bin/supercronic

# Install yq
WORKDIR /tmp
RUN GOBIN=/usr/local/bin/ go install github.com/mikefarah/yq/v4@master

# Clean prometheus client_golang
WORKDIR /root/go/pkg/mod/github.com/prometheus/
RUN cd client_golang@v1.22.0 && \
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
RUN dnf install -y yum-utils-4.7.0 rpm-build-4.19.1.1 && \
    dnf clean all && \
    yumdownloader --source httpd-2.4.63-1.el10.x86_64 && \
    HOME="/tmp" rpm -ivh httpd-*.src.rpm && \
    yum-builddep -y httpd-2.4.63-1.el10.x86_64

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Install pip dependencies
RUN pip install -r onearth/docker/deps/requirements.txt

WORKDIR /tmp

# Install APR patch
RUN wget http://archive.apache.org/dist/apr/apr-1.7.5.tar.gz && \
    tar xf apr-1.7.5.tar.gz && \
    cd /tmp/apr-1.7.5 && \
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
    sed -i '/xmlto man/d' httpd.spec && \
    HOME="/tmp" rpmbuild -bp httpd.spec && \
    ls /home/oe2/onearth && \
    cp /home/oe2/onearth/docker/mod_proxy_http.patch /tmp/rpmbuild/SOURCES && \
    cp /home/oe2/onearth/docker/proxypass_nomain_flag.patch /tmp/rpmbuild/SOURCES && \
    patch -p2 < /home/oe2/onearth/docker/http_rpm_spec.patch && \
    HOME="/tmp" QA_RPATHS=$(( 0x0002 )) rpmbuild -ba httpd.spec && \
    yum -y remove httpd httpd-devel httpd-tools && \
    yum -y install system-logos-httpd /etc/mime.types sscg && \
    yum clean all && \
    rpm -ivh /tmp/rpmbuild/RPMS/*/httpd*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_ssl*.rpm && \
    rpm -ivh /tmp/rpmbuild/RPMS/x86_64/mod_lua*.rpm && \
    cd / && rm -rf /tmp/apr-1.7.4* /tmp/apr-util-1.6.3* /tmp/httpd-2.4.63* /tmp/rpmbuild*

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
