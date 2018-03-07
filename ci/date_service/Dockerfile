FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release lua-devel jansson-devel httpd-devel libpng-devel libjpeg-devel pcre-devel mod_proxy mod_ssl wget
RUN yum install -y luarocks
RUN yum install -y redis

RUN mkdir /home/oe2
#RUN mkdir -p /var/www

# Clone OnEarth repo
WORKDIR /home/oe2
RUN git clone https://github.com/nasa-gibs/onearth.git
WORKDIR /home/oe2/onearth
RUN git checkout 2.0.0

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
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

WORKDIR /home/oe2/onearth/docker/date_service
CMD sh start_date_service.sh