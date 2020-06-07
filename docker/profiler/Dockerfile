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
CMD ["/usr/sbin/httpd","-D", "FOREGROUND"]
