FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release lua-devel jansson-devel libpng-devel libjpeg-devel pcre-devel mod_proxy mod_ssl wget openssl-devel libyaml-devel
RUN yum install -y luarocks
RUN yum install -y redis
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u python36u-pip python36u-devel
RUN pip3.6 install requests
RUN pip3.6 install pyaml
RUN pip3.6 install lxml
RUN pip3.6 install pypng

RUN mkdir /home/oe2
RUN mkdir -p /var/www

# Clone OnEarth repo
WORKDIR /home/oe2
RUN git clone https://github.com/nasa-gibs/onearth.git
WORKDIR /home/oe2/onearth
RUN git checkout 2.2.0

# Download RPM source for Apache, configure the mod_proxy patch, rebuild the RPM and install it
WORKDIR /tmp
RUN yum install -y yum-utils rpm-build
RUN yumdownloader --source httpd
RUN HOME="/tmp" rpm -ivh httpd-2.4.6-80.el7.centos.1.src.rpm
RUN yum-builddep -y httpd
WORKDIR /tmp/rpmbuild/SPECS
RUN HOME="/tmp" rpmbuild -bp httpd.spec
COPY http_rpm_spec.patch /home/oe2/onearth/docker/http_rpm_spec.patch
COPY mod_proxy_http.patch /tmp/rpmbuild/SOURCES
RUN patch -p2 <  /home/oe2/onearth/docker/http_rpm_spec.patch
RUN HOME="/tmp" rpmbuild -ba httpd.spec
RUN yum -y remove httpd httpd-devel httpd-tools
RUN ls /tmp/rpmbuild/RPMS/x86_64/
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

# Install Apache modules
WORKDIR /home/oe2/onearth/src/modules/mod_receive/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_mrf/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_reproject/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_twms/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_wmts_wrapper
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN cp /home/oe2/onearth/src/modules/mod_reproject/src/mod_reproject.h .
RUN make && make install

WORKDIR /home/oe2/onearth/src/modules/mod_sfim/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_service/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_service
RUN luarocks make onearth-0.1-1.rockspec

# Install GC Service configs
RUN mkdir -p /etc/onearth/config/endpoint
RUN cp -R /home/oe2/onearth/src/modules/gc_service/conf /etc/onearth/config/
WORKDIR /home/oe2/onearth/src/modules/gc_service
RUN luarocks make onearth_gc_gts-0.1-1.rockspec

# Install layer configuration tools
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_wmts_configure.py /usr/bin/
RUN cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/oe2_reproject_configure.py /usr/bin/

# Set Apache to Debug mode for performance logging
RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
RUN perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
COPY 00-mpm.conf /etc/httpd/conf.modules.d/
COPY 10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/docker
CMD sh start_oe2.sh $S3_URL $REDIS_HOST