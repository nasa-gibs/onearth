# This Dockerfile must be run from source root

FROM centos:7

# Upgrade all existing packages
RUN yum -y update && yum clean all

# Install HTTPD and mod_ssl
RUN yum install -y httpd-2.4.6 mod_ssl perl && \
	yum clean all

RUN mkdir -p /home/oe2
COPY ./docker/demo/start_demo.sh /home/oe2/

# Copy Apache configs
COPY ./docker/demo/oe2_demo.conf /etc/httpd/conf.d/

# Set Apache configuration for optimized threading
COPY ./docker/00-mpm.conf /etc/httpd/conf.modules.d/
COPY ./docker/10-worker.conf /etc/httpd/conf.modules.d/
COPY ./docker/cors.conf /etc/httpd/conf.d/

# Copy demo files
COPY ./src/demo /var/www/html/demo

# Start HTTPD server
WORKDIR /home/oe2
CMD sh start_demo.sh $DEBUG_LOGGING