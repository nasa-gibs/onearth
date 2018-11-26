# OnEarth Time Service

## Docker Setup

The included Dockerfile will build an image with the OnEarth Time Service.

To run, simply build the image `docker build -t onearth-time-service .`, and then start a
container using that image. Make sure that the OE2 container can access the time service
via Docker network or another means.

For more information about the OnEarth Time Service, see [Time Snapping](../../src/modules/time_service/README.md)