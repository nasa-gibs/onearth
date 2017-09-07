ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY rpms/*.rpm /rpms/
RUN yum install -y /rpms/*.rpm && yum clean all

WORKDIR /usr/share/onearth/demo/examples/default
RUN ./configure_demo.sh
WORKDIR /
