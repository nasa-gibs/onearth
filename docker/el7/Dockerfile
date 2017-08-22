# Note: Do not use this Dockerfile directly to create an image.  Instead, run
# ./bin/build_el7_docker_image.sh.  That script will set the correct FROM
# image based on the contents of docker/el7/gibs-gdal-image.txt
FROM gibs-gdal

COPY rpms/onearth-*.el7.*.rpm /rpms/

RUN yum install -y /rpms/onearth-*.el7.*.rpm && yum clean all

# Clean up config files that are going to be overwritten
RUN rm -rf \
  /run/httpd/* \
  /tmp/httpd* \
  /etc/httpd/conf.d/onearth-demo.conf \
  /var/www/html/*

COPY run-onearth.sh /run-onearth.sh
CMD ["/run-onearth.sh"]
