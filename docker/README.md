# Building and Deploying OE2

## Docker Setup

OnEarth uses Docker images for its services. The main OnEarth Docker image
contains WMTS/TWMS and GetCapabilities services and is configured with several
test layers. It requires the Time Service, which is a separate Docker image,
in order to support time dynamic layers. A WMS Service is also available as a
separate Docker image.

To build the Docker images and deploy the OnEarth stack,
Update the `ONEARTH_VERSION` and `ONEARTH_RELEASE` variables in `version.sh`
and source the file: `source version.sh`.
Then run: `build.sh` and `run.sh` from the source root.

Note that you may need to manually update the version numbers within the Dockerfiles.

Alternatively, you can run each Docker image individually by building the
image: `docker build -t onearth .`, and then starting a container using
that image. Make sure to expose the appropriate ports (e.g., port 80) on the
container to access the image server.

By default, the containers use a Docker network `oe2` to communicate with each other.

## Configuration Options

OnEarth Docker containers accept the following environment variables. Use the `--env`, `-e` or `--env-file` options when starting the container with Docker. Amazon ECS also supports environment variables.

### onearth-capabilities
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* HealthCheck: http://localhost/wmts/oe-status/wmts.cgi?SERVICE=WMTS&request=GetCapabilities

### onearth-reproject
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* HealthCheck: http://localhost/oe-status_reproject/Raster_Status/default/2004-08-01/GoogleMapsCompatible_Level3/0/0/0.jpeg

### onearth-tile-services
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* IDX_SYNC: `true/false` (defaults `false`) whether to sync IDX files on local disk with those found in the S3 URL
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* HealthCheck: http://localhost/oe-status/Raster_Status/default/2004-08-01/16km/0/0/0.jpeg

### onearth-time-service
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* HealthCheck: http://localhost/oe2-time-service-proxy-onearth-time-service/

### onearth-wms
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* ENDPOINT_REFRESH: Interval for refreshing the WMS endpoints in minutes
* HealthCheck: http://localhost/wms/oe-status_reproject/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=Raster_Status,Vector_Status&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34

See [OnEarth Configuration](../doc/configuration.md) for more information.

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
