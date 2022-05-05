# Docker Image Build

## Building the onearth image

A Docker image that's configured to run OnEarth can be built using the **./bin/build_el7_docker_image.sh** script.  The script takes a single parameter, the tag to apply to the image.

Example of building an OnEarth Docker image:

`./bin/build_el7_docker_image.sh nasagibs/onearth:1.4.3`

The generated image will start Apache when it is run.

## Building the onearth-demo image

A Docker image that's configured to run OnEarth with a demo configuration can be
built using the **./bin/build_el7_demo_docker_image.sh** script.  The script
takes two parameters:

* BASE_IMAGE - the onearth image to build on top of
* TAG - the tag to be applied to the newly generated image

Example of building an onearth-demo Docker image using the
"nasagibs/onearth:1.4.3":

`./bin/build_el7_demo_docker_image.sh nasagibs/onearth:1.4.3 onearth-demo:1.4.3`
