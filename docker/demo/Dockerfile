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

# Set the locale
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Add non-root user
RUN groupadd www-data && useradd -g www-data www-data
RUN chmod 755 -R /etc/pki && chmod 1777 /tmp && chown -hR www-data:www-data /etc/httpd/ && chown -hR www-data:www-data /run/httpd/ && chown -hR www-data:www-data /var/www/ && chown -hR www-data:www-data /var/log/httpd/

#setcap to bind to privileged ports as non-root
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/httpd && getcap /usr/sbin/httpd

# Remove unneeded kernel headers
RUN yum remove -y kernel-headers kernel-debug-devel

# Remove python2 and link python3
RUN rm /usr/bin/python && \
    ln -s /usr/bin/python3 /usr/bin/python

# Change user
USER www-data

# Start HTTPD server
WORKDIR /home/oe2
CMD sh start_demo.sh $DEBUG_LOGGING

#interval:30s, timeout:30s, start-period:0s, retries:3
HEALTHCHECK CMD curl --fail http://localhost/demo/ || exit 1 