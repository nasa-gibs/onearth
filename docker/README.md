# Building and Installing OE2

## Docker setup

The included Dockerfile will build an image with OE2. The build is configured
with a couple of test layers.

To run, simply build the image `docker build -t onearth_2 .`, and then start a
container using that image. Make sure to expose port 80 on the container to
access the image server.

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

The date snapping service is also available at `localhost/date_service/date?`

## Notes

The date-snapping service also determines the filenames mod_mrf will look for
when trying to find data for a specific date. Currently, it formats them as
`{layer}{UNIX_epoch}.(idx|pjg)`.