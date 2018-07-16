FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release 
RUN yum install -y python-pip 

RUN mkdir /home/perf

# Clone OnEarth repo
WORKDIR /home/perf
RUN git clone https://github.com/nasa-gibs/onearth.git
WORKDIR /home/perf/onearth
RUN git checkout 2.1.1

# Get and install node
WORKDIR /home/perf
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.8/install.sh | bash \
    && . /root/.nvm/nvm.sh \
    && nvm install 6.10 \
    && nvm install node \
    && nvm use node

# AWS CLI
WORKDIR /home/perf
RUN pip install awscli --upgrade
ARG AWS_ID
ARG AWS_SECRET
RUN aws configure set aws_access_key_id $AWS_ID
RUN aws configure set aws_secret_access_key $AWS_SECRET
RUN aws configure set output json
RUN aws configure set region us-east-1

# Install siege
RUN yum install -y siege

# Install numpy
WORKDIR /home/perf
RUN pip install numpy

# Run performance test
#WORKDIR /home/perf/onearth/docker/profiler
#CMD sh start_profiler.sh
