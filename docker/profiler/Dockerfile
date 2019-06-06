FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release 
RUN yum install -y python-pip httpd

# Copy OnEarth profiler source
RUN mkdir -p /home/oe2/onearth/profiler
WORKDIR /home/oe2
COPY ./profiler /home/oe2/onearth/profiler

# Get and install node
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.8/install.sh | bash \
    && . /root/.nvm/nvm.sh \
    && nvm install 6.10 \
    && nvm install node \
    && nvm use node

# AWS CLI
RUN pip install awscli --upgrade

# Install siege
RUN yum install -y siege

# Install numpy
RUN pip install numpy

# Run performance test
WORKDIR /home/oe2/onearth/profiler

EXPOSE 80
CMD ["/usr/sbin/httpd","-D", "FOREGROUND"]
