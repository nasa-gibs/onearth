# Note: Do not use this Dockerfile directly to create an image.  Instead, run
# ./bin/build_el7_demo_docker_image.sh.  That script will set the correct FROM
# image based on its arguments
FROM onearth

COPY rpms/*.rpm /rpms/
RUN yum reinstall -y /rpms/onearth-demo-*.el7.noarch.rpm && yum clean all

WORKDIR /usr/share/onearth/demo/examples/default
RUN ./configure_demo.sh
WORKDIR /
