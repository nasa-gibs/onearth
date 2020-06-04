FROM centos:7

COPY rpms/onearth-*.el7.*.rpm /rpms/
COPY run-onearth.sh /usr/local/bin/run-onearth.sh

RUN yum -y install epel-release && yum clean all
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-2.4.4-1.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-devel-2.4.4-1.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-apps-2.4.4-1.el7.x86_64.rpm" && \
	yum clean all
RUN yum install -y /rpms/onearth-*.el7.*.rpm && yum clean all
RUN yum -y install numpy proj-devel && yum clean all

ENV LCDIR=/etc/onearth/config
RUN sed -i 's/Order allow,deny/Require all granted/g' /etc/httpd/conf.d/onearth-demo.conf

# Start HTTPD server
CMD sh /usr/local/bin/run-onearth.sh