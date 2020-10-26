FROM centos:7

COPY rpms/onearth-*.el7.*.rpm /rpms/
COPY run-onearth.sh /usr/local/bin/run-onearth.sh

RUN yum -y install epel-release && yum clean all
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-2.4.4-1.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-devel-2.4.4-1.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4/gibs-gdal-apps-2.4.4-1.el7.x86_64.rpm" && \
	yum clean all
RUN yum -y install proj-devel python-pip python3-devel && yum clean all

RUN groupadd -g 1000 gibs && useradd -u 1000 -g gibs -s /bin/sh gibs
RUN yum -y install /rpms/onearth-*.el7.*.rpm && yum clean all

# Update pip and install requirements
WORKDIR /pip/
COPY pip-requirements.txt .
RUN pip install --upgrade pip && pip install -r pip-requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r pip-requirements.txt
RUN pip3 install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

ENV LCDIR=/etc/onearth/config

# Set the locale
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

RUN sed -i 's/Order allow,deny/Require all granted/g' /etc/httpd/conf.d/onearth-demo.conf

# Start HTTPD server
CMD sh /usr/local/bin/run-onearth.sh