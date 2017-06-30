FROM gibs-gdal:centos7-1

COPY rpms/onearth-*.el7.*.rpm /rpms/

RUN yum install -y /rpms/onearth-*.el7.*.rpm

COPY run-onearth.sh /run-onearth.sh
CMD ["/run-onearth.sh"]
