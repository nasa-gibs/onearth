# OnEarth

OnEarth is a software package consisting of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The software was originally developed at the Jet Propulsion Laboratory ([JPL](http://www.jpl.nasa.gov/)) to serve global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center ([PO.DAAC](http://podaac.jpl.nasa.gov/)) in support of the State of the Oceans ([SOTO](https://podaac-tools.jpl.nasa.gov/soto/)) visualization tool, the Lunar Mapping and Modeling Project ([LMMP](https://moontrek.jpl.nasa.gov/)), and [Worldview](https://worldview.earthdata.nasa.gov/).

For more information, visit https://earthdata.nasa.gov/gibs

## Setup

* [Docker Image Build](doc/docker_image_build.md)
* [Installation](doc/installation.md)
* [Configuration](doc/configuration.md)
* [Creating Image Archive](doc/archive.md)
* [Configuring Vector Data](doc/config_vectors.md)

## Components

* [mod_mrf](src/modules/mod_mrf/src/README.md)
* [mod_ahtse_lua](src/modules/mod_ahtse_lua/src/README.md)
* [mod_receive](src/modules/mod_receive/src/README.md)
* [mod_receive](https://github.com/nasa-gibs/mod_receive)
* [mod_reproject](https://github.com/nasa-gibs/mod_reproject)
* [mod_twms](https://github.com/nasa-gibs/mod_twms)
* [mod_wmts_wrapper](src/modules/mod_wmts_wrapper/README.md)
* [mrfgen](src/mrfgen/README.md)
* [vectorgen](src/vectorgen/README.md)
* [OnEarth Legend Generator](src/generate_legend/README.md)
* [OnEarth Metrics](src/onearth_logs/README.md)
* [OnEarth Scripts](src/scripts/README.md)
* [OnEarth Empty Tile Generator](src/empty_tile/README.md)
* [OnEarth Demo](src/demo/README.md)

## Other Information

* [Meta Raster Format](https://github.com/nasa-gibs/mrf/blob/master/README.md)
* [Tests](src/test/README.md)
* [Troubleshooting](doc/troubleshooting.md)
* [Contributing](CONTRIBUTING.md)

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
