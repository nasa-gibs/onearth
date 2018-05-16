FROM centos:7

RUN yum groupinstall -y "Development Tools"
RUN yum install -y epel-release 
RUN yum install -y python-pip 

RUN mkdir /home/perf

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

# Run performance test
#WORKDIR 
#CMD sh 
