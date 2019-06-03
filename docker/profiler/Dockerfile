FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release 
RUN yum install -y python-pip 

# Copy OnEarth to home directory
RUN mkdir -p /home/oe2
WORKDIR /home/oe2
COPY ./ /home/oe2/onearth/

# Get and install node
WORKDIR /home/oe2
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.8/install.sh | bash \
    && . /root/.nvm/nvm.sh \
    && nvm install 6.10 \
    && nvm install node \
    && nvm use node

# AWS CLI
WORKDIR /home/oe2
RUN pip install awscli --upgrade

# Install siege
RUN yum install -y siege

# Install numpy
WORKDIR /home/oe2
RUN pip install numpy

# Run performance test
WORKDIR /home/oe2/onearth/docker/profiler
#CMD sh start_profiler.sh $GROUP_NAME $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY $AWS_REGION
