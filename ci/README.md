# Building and Installing OE2 CI configuration

## Docker setup

The included build_el7_docker_image.sh will build an image with OE2. The build 
is configured for CI tests.

To run, simply build the image `./ci/build_el7_image_from_src.sh <tag name>`, and then start a
container using that image. Make sure to expose port 80 on the container to
access the image server.

### CI Tests

For more information on CI tests, refer [here](../src/test/README.md).


## Notes

The date-snapping service also determines the filenames mod_mrf will look for
when trying to find data for a specific date. Currently, it formats them as
`{layer}{UNIX_epoch}.(idx|pjg)`.
