FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release lua-devel jansson-devel httpd-devel libpng-devel libjpeg-devel pcre-devel mod_proxy mod_ssl wget
RUN yum install -y luarocks
RUN yum install -y redis

RUN mkdir /home/oe2
RUN mkdir -p /var/www

# Clone OnEarth repo
WORKDIR /home/oe2
RUN git clone https://github.com/nasa-gibs/onearth.git
WORKDIR /home/oe2/onearth
RUN git checkout 2.0.0

# Install mod_proxy patch
WORKDIR /tmp
RUN wget https://archive.apache.org/dist/httpd/httpd-2.4.6.tar.gz
RUN tar xf httpd-2.4.6.tar.gz
WORKDIR /tmp/httpd-2.4.6
RUN patch -p0 < /home/oe2/onearth/docker/mod_proxy_http.patch
RUN ./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared
RUN make && make install
RUN cp /tmp/httpd/modules/mod_proxy* /etc/httpd/modules/

# Install APR patch
WORKDIR /tmp
RUN wget http://apache.osuosl.org//apr/apr-1.6.3.tar.gz
RUN tar xf apr-1.6.3.tar.gz
WORKDIR /tmp/apr-1.6.3
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

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_snap/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_snap
RUN luarocks make onearth-0.1-1.rockspec

# Set Apache to Debug mode for performance logging
RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
RUN perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
COPY 00-mpm.conf /etc/httpd/conf.modules.d/
COPY 10-worker.conf /etc/httpd/conf.modules.d/

WORKDIR /home/oe2/onearth/docker
CMD sh start_oe2.sh