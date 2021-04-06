FROM centos:8

COPY rpms/onearth-*.el8.*.rpm /rpms/
COPY run-onearth.sh /usr/local/bin/run-onearth.sh

RUN dnf install -y 'dnf-command(config-manager)'
RUN dnf config-manager --set-enabled powertools
RUN dnf install -y python3
RUN yum -y install epel-release && yum clean all
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-2/gibs-gdal-2.4.4-2.el8.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-2/gibs-gdal-devel-2.4.4-2.el8.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-2/gibs-gdal-apps-2.4.4-2.el8.x86_64.rpm" && \
	yum clean all
RUN yum -y install proj-devel httpd glibc-locale-source glibc-langpack-en && yum clean all

RUN groupadd -g 1000 gibs && useradd -u 1000 -g gibs -s /bin/sh gibs
RUN yum -y install /rpms/onearth-*.el8.*.rpm && yum clean all

# Update pip and install requirements
WORKDIR /pip/
COPY pip-requirements.txt .
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