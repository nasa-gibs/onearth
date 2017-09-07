ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY rpms/onearth-*.el7.*.rpm /rpms/
COPY run-onearth.sh /usr/local/bin/run-onearth.sh

RUN yum install -y /rpms/onearth-*.el7.*.rpm && yum clean all

CMD ["/usr/local/bin/run-onearth.sh"]
