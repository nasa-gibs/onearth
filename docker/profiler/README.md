# Creating Siege docker container with performance test suite

## Docker setup

The included Dockerfile will build an image with siege. The build is configured
with the performance test suite.  This Docker image assumes AWS instance has been 
deployed and configured and that it is accessible.

To allow access to the AWS instance, set up a SSH tunnel thru bastion to the host 
machine.  Run the following command.
ssh -L*:8080:<AWS instance IP address>:80 <bastion>

To run, simply build the image `docker build -t siege --build-arg AWS_ID={id} 
--build-arg AWS_SECRET={secret key} .`, and then start a container using that image. 

To keep it simple use, use host networking with the docker run command.
For example, 
docker run -it --network host siege:latest /bin/bash

Please note, docker host networking does not work as expected on MacOS.  Please refer
to https://forums.docker.com/t/should-docker-run-net-host-work/14215/29 for more 
information.

### Performance Test Suite

testP0 -- 100,000 Requests / 100 Users / 20 URLs / Single 500m JPEG MRF

testP1 -- 100,000 Requests / 100 Users / 20 URLs / Single 250m JPEG MRF with TIME

testP2 -- 100,000 Requests / 100 Users / 68,273 URLs / Single 250m JPEG MRF

testP3 -- 100,000 Requests / 100 Users / 100,000 URLs / 100 250m JPEG MRFs

testP4 -- 100,000 Requests / 1 Users / 68,273 URLs / Single 250m JPEG MRF

testP5 -- 100,000 Requests / 100 Users / 100,000 URLs / 100 250m PNG MRFs

testP6 -- Mod Reproject 100,000 Requests / 100 Users / 87,381 URLs / Single 500m JPEG MRF

To run the test suite, run the following command in the docker image.
/home/perf/onearth/docker/profiler/start_profiler.sh <GROUP NAME>

<GROUP NAME> is the AWS instance name where OnEarth is deployed
