# Building and Deploying OE2

## Docker Setup

OnEarth uses Docker images for its services. The main OnEarth Docker image
contains WMTS/TWMS and GetCapabilities services and is configured with several
test layers. It requires the Time Service, which is a separate Docker image,
in order to support time dynamic layers. A WMS Service is also available as a
separate Docker image.

To build the Docker images and deploy the OnEarth stack, run:
`./deploy_oe2_containers.sh`

Alternatively, you can run each Docker image individually by building the
image: `docker build -t onearth .`, and then starting a container using 
that image. Make sure to expose the appropriate ports (e.g., port 80) on the 
container to access the image server.

By default, the containers use a Docker network `oe2` to communicate with each other.

## Configuration Options

Several environment variables may be set to specify the location of configuration items.

* **REDIS_HOST**: Redis endpoint URL
* **S3_URL**: http URL to the S3 bucket containing MRFs
* **EMPTY_TILES_URL**: URL to S3 bucket or web link containing empty tiles
* **LEGENDS_URL**: URL to S3 bucket or web link containing legend images
* **COLORMAPS_URL**: URL to S3 bucket or web link containing colormaps
* **STYLESHEETS_URL**: URL to S3 bucket or web link containing stylesheets

### Test Layers

`localhost/mrf_endpoint/static_test/default/tms/{level}/{row}/{col}.jpg` --
Tests functionality of mod_mrf. Layer is a static layer without a TIME
dimension.

`localhost/mrf_endpoint/date_test/default/{time}/tms/{level}/{row}/{col}.jpg` --
Same as previous, except this layer exists with the period
2015-01-01/2017-01-01/P1Y. Default date is 2015-01-01

`localhost/reproject_endpoint/static_test/default/tms/{level}/{row}/{col}.jpg`
-- Tests functionality of mod_reproject, reprojecting the static layer served by
mod_mrf.

`localhost/reproject_endpoint/date_test/default/{time}/tms/{level}/{row}/{col}.jpg`
-- Same as previous, with a TIME dimension.

If the Time Service is running, it will be available at `localhost/time_service/time?`

## Notes

The Time Service also determines the filenames mod_mrf will look for
when trying to find data for a specific date or time. Currently, it formats them as
`{layer}-{%Y%j%H%M%S}.(idx|pjg)` but may be configured differently.
