# Creating Docker image with performance profiling test suite

## Docker setup

The included Dockerfile will build an image with Siege. The build is configured
with the performance test suite.  This Docker image assumes AWS instance has been 
deployed and configured and that it is accessible.

To build the image, copy the Dockerfile to the top directory `cp ./docker/profiler/Dockerfile/ .`, and then build using the Dockerfile `docker build -t nasagibs/onearth-profiler .` 

Environment variables for AWS CLI tools must be passed into the Docker container on startup:
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION

Run the container using the Docker image. To keep it simple use, use host networking with the docker run command.
For example, 
docker run -it --network host -e GROUP_NAME=$GROUP_NAME -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_REGION=$AWS_REGION nasagibs/onearth-profiler:latest /bin/bash

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
/home/perf/onearth/docker/profiler/start_profiler.sh $GROUP_NAME $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY $AWS_REGION

$GROUP_NAME is the AWS instance name where OnEarth is deployed
