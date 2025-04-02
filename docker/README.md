# Building and Deploying OE2

## Docker Setup

OnEarth uses Docker images for its services. The main OnEarth Docker image "tile-services"
contains WMTS/TWMS tile services and is configured with several
test layers. It requires "capabilities" and "time-services", which are separate Docker images in order to support time dynamic layers. Reprojection and WMS services are also available as separate Docker images.

To build the Docker images and deploy the OnEarth stack,
Update the `ONEARTH_VERSION` and `ONEARTH_RELEASE` variables in `version.sh`
and source the file: `source version.sh`.

To build the OnEarth Docker images, `cd docker` and run `docker compose up`
You can override certain environment variables by running: `USE_SSL=false SERVER_NAME=different_server docker compose up`
You can also choose to build the OnEarth tools image with `docker compose --profile enable-tools up`

If you would rather use scripts, you can follow this approach: 
The "deps" Docker image OnEarth dependencies must first be built before the other Docker images. Run `./ci/build_deps_image.sh nasagibs/onearth-deps:$ONEARTH_VERSION` to build the image. It can take a while to build the first time, but rebuilds are not needed unless there is a version or dependency change.

Run: `build.sh` and `run.sh` from the source root.

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
* SERVER_STATUS: `true/false` (defaults `false`) whether to enable the [mod_status](https://httpd.apache.org/docs/2.4/mod/mod_status.html) Apache server status page for this service (/server-status)
* HealthCheck: http://localhost/wmts/oe-status/wmts.cgi?SERVICE=WMTS&request=GetCapabilities

### onearth-reproject
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* SERVER_STATUS: `true/false` (defaults `false`) whether to enable the [mod_status](https://httpd.apache.org/docs/2.4/mod/mod_status.html) Apache server status page for this service (/server-status)
* HealthCheck: http://localhost/oe-status_reproject/Raster_Status/default/2004-08-01/GoogleMapsCompatible_Level3/0/0/0.jpeg

### onearth-tile-services
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* IDX_SYNC: `true/false` (defaults `false`) whether to sync IDX files on local disk at startup with those found in the S3 URL
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)
* GENERATE_COLORMAP_HTML: `true/false` (defaults `false`) whether to generate HTML versions of the XML colormaps and place them in `/etc/onearth/colormaps/v1.0/output` and `/etc/onearth/colormaps/v1.3/output`. Useful when these colormaps aren't already stored at `$S3_CONFIGS/colormaps/v1.0/output/` and `$S3_CONFIGS/colormaps/v1.3/output/`, respectively, as OnEarth will first attempt to sync them down from these locations.
* SERVER_STATUS: `true/false` (defaults `false`) whether to enable the [mod_status](https://httpd.apache.org/docs/2.4/mod/mod_status.html) Apache server status page for this service (/server-status)
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
* SHAPEFILE_BUCKET: Public S3 bucket containing shapefiles. When not specified, OnEarth will be configured to attempt to read shapfiles from `/onearth/shapefiles/` for each WMS request.
* SHAPEFILE_SYNC: `true/false` (defaults `false`) whether to sync shapefiles on local disk at `/onearth/shapefiles/` at startup with those found in the `SHAPEFILE_BUCKET` S3 URL
* USE_LOCAL_SHAPEFILES: `true/false` (defaults `false`) whether to configure OnEarth to load shapefiles from `SHAPEFILE_BUCKET` (when `false`) or from `/onearth/shapefiles/` (when `true`) for WMS requests. Use of local files is generally much faster than reading from S3. Ignored when `SHAPEFILE_BUCKET` isn't specified.
* ENDPOINT_REFRESH: Interval for refreshing the WMS endpoints in minutes
* SERVER_STATUS: `true/false` (defaults `false`) whether to enable the [mod_status](https://httpd.apache.org/docs/2.4/mod/mod_status.html) Apache server status page for this service (/server-status)
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
