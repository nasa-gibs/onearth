FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release 
RUN yum install -y https://repo.ius.io/ius-release-el7.rpm
RUN yum install -y python36u python36u-devel python36u-pip httpd siege

# Copy OnEarth profiler source
RUN mkdir -p /home/oe2/onearth/profiler
WORKDIR /home/oe2
COPY ./profiler /home/oe2/onearth/profiler
    
# AWS CLI
RUN pip3.6 install awscli --upgrade

# Install python deps
RUN pip3.6 install numpy pyaml

# Run performance test
WORKDIR /home/oe2/onearth/profiler

EXPOSE 80

# Set the locale
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Add non-root user
RUN groupadd www-data && useradd -g www-data www-data
RUN chmod 755 -R /etc/pki && chown -hR www-data:www-data /etc/httpd/ && chown -hR www-data:www-data /run/httpd/ && \
    chown -hR www-data:www-data /var/www/ && chown -hR www-data:www-data /var/log/httpd/ && \
	chown -hR www-data:www-data /home/oe2

#setcap to bind to privileged ports as non-root
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/httpd && getcap /usr/sbin/httpd

# Change user
USER www-data

CMD ["/usr/sbin/httpd","-D", "FOREGROUND"]
