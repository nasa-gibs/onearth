# Note: Do not use this Dockerfile directly to create an image.  Instead, run
# ./bin/build_el7_docker_image.sh.  That script will set the correct FROM
# image based on the contents of docker/el7/gibs-gdal-image.txt
FROM gibs-gdal

COPY rpms/onearth-*.el7.*.rpm /rpms/
COPY run-onearth.sh /usr/local/bin/run-onearth.sh

RUN yum install -y /rpms/onearth-*.el7.*.rpm && yum clean all

CMD ["/usr/local/bin/run-onearth.sh"]
