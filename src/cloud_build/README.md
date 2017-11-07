# Building and Installing OE2

## Docker setup
The included Dockerfile will build an image with OE2.
To set up some sample layers, run (within the container) `/home/oe2/onearth/src/cloud_build/test_layer_setup.sh`

## Setup without Docker

## Clone the repo and initialize the subrepos
```
git clone https://github.com/nasa-gibs/onearth.git
cd onearth
checkout 2.0.0-cloud-setup
```

## Install everything (requires sudo permissions)
```
cd src/cloud_build
./build_oe2.sh
```

This script attempts to install all the software and does some basic verification (printing issues to stderr).

## Set up a couple sample layers

```
./test_layer_setup.sh
```

This script configures a few test layers and checks to see that they are working. The layers are made available at:

`localhost/mrf_endpoint/static_test/default/tms/{level}/{row}/{col}.jpg` -- Tests functionality of mod_mrf. Layer is a static layer without a TIME dimension.

`localhost/mrf_endpoint/date_test/default/{time}/tms/{level}/{row}/{col}.jpg` -- Same as previous, except this layer exists with the period 2015-01-01/2017-01-01/P1Y. Default date is 2015-01-01

`localhost/reproject_endpoint/static_test/default/tms/{level}/{row}/{col}.jpg` -- Tests functionality of mod_reproject, reprojecting the static layer served by mod_mrf.

`localhost/reproject_endpoint/date_test/default/{time}/tms/{level}/{row}/{col}.jpg` -- Same as previous, with a TIME dimension.

The date snapping service is also available at `localhost/date_service/date?`

## Notes 
The date-snapping service also determines the filenames mod_mrf will look for when trying to find data for a specific date. Currently, it formats them as `{layer}{YYYY}{DoY}`.
