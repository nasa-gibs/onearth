# This Dockerfile must be run from source root

FROM centos:7

# Install HTTPD and mod_ssl
RUN yum install -y httpd-2.4.6 mod_ssl

# Copy Apache configs
COPY ./docker/demo/oe2_demo.conf /etc/httpd/conf.d/
COPY ./docker/demo/oe2_status.conf /etc/httpd/conf.d/

# Set Apache configuration for optimized threading
COPY ./docker/00-mpm.conf /etc/httpd/conf.modules.d/
COPY ./docker/10-worker.conf /etc/httpd/conf.modules.d/

# Copy demo files
COPY ./src/demo /var/www/html/demo

# Start HTTPD server
CMD ["/usr/sbin/httpd", "-D", "FOREGROUND"]
EXPOSE 80