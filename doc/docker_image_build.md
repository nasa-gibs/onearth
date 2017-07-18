# Docker Image Build

A Docker image that's configured to run OnEarth can be built using the **./bin/build_el7_docker_image.sh** script.  The script takes a single parameter, the tag to apply to the image.

The new images is built from a Docker image that has the gibs-gdal RPMs installed already. The name of that image is set in the **docker/el7/gibs-gdal-image.txt** file.

Example of building an OnEarth Docker image:

`./bin/build_el7_docker_image.sh gibs/onearth:v1.3.1`

The generated image will start Apache when it is run.  The image will expect
the configuration to be located at **/mnt/config**.
