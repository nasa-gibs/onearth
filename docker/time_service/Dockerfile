# This Dockerfile must be run from source root

FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release-7-11 lua-devel-5.1.4 jansson-devel-2.10 libpng-devel-1.5.13 pcre-devel-8.32 wget-1.14 libjpeg-turbo-devel-1.2.90 httpd-devel-2.4.6
RUN yum install -y mod_ssl
RUN yum install -y luarocks-2.3.0
RUN yum install -y redis-3.2.12

RUN mkdir /home/oe2
RUN mkdir -p /var/www

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

WORKDIR /home/oe2/onearth/src/modules/mod_ahtse_lua/src/
RUN cp /home/oe2/onearth/docker/Makefile.lcl .
RUN make && make install

# Install Lua module for time snapping
WORKDIR /home/oe2/onearth/src/modules/time_service/redis-lua
RUN luarocks make rockspec/redis-lua-2.0.5-0.rockspec
WORKDIR /home/oe2/onearth/src/modules/time_service
RUN luarocks make onearth_time_service-0.1-1.rockspec

# Set Apache to Debug mode for performance logging
# RUN perl -pi -e "s/LogLevel warn/LogLevel debug/g" /etc/httpd/conf/httpd.conf
# RUN perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf

# Set Apache configuration for optimized threading
WORKDIR /home/oe2/onearth/docker/time_service
RUN cp 00-mpm.conf /etc/httpd/conf.modules.d/
RUN cp 10-worker.conf /etc/httpd/conf.modules.d/

CMD sh start_time_service.sh $REDIS_HOST