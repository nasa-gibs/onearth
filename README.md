### NASA Global Imagery Browse Services (GIBS)

**This software was originally developed at the Jet Propulsion Laboratory as Tiled WMS (https://github.com/nasajpl/tiledwms).  OnEarth is now the latest actively developed version.**

# OnEarth

OnEarth is a software package consisting of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The software was originally developed at the Jet Propulsion Laboratory ([JPL](http://www.jpl.nasa.gov/)) to serve global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center ([PO.DAAC](http://podaac.jpl.nasa.gov/)) in support of the State of the Oceans ([SOTO](http://podaac-tools.jpl.nasa.gov/soto-2d/)) visualization tool, the Lunar Mapping and Modeling Project ([LMMP](http://pub.lmmp.nasa.gov/LMMPUI/LMMP_CLIENT/LMMP.html)), and [Worldview](https://earthdata.nasa.gov/labs/worldview/).

The source code contains the mod_onearth Apache module (formerly Tiled WMS/KML server), a Meta Raster Format (MRF) imagery generator, a legend generator, and server configuration tools.

For more information, visit https://earthdata.nasa.gov/gibs

### OnEarth-Boxes
[OnEarth-Boxes](https://github.com/nasa-gibs/onearth-boxes) is a tool that can build a virtual machine with demo imagery and pre-configured endpoints for demos, development, and getting started with MRF and OnEarth. Multiple VM image formats are supported. For more information visit https://github.com/nasa-gibs/onearth-boxes.

## Setup

* [RPM Build](doc/rpm_build.md)
* [Docker Image Build](doc/docker_image_build.md)
* [Installation](doc/installation.md)
* [Configuration](doc/configuration.md)
* [Creating Image Archive](doc/archive.md)
* [Configuring Vector Data](doc/config_vectors.md)

## Components

* [mod_onearth](src/modules/mod_onearth/README.md)
* [mrfgen](src/mrfgen/README.md)
* [vectorgen](src/vectorgen/README.md)
* [OnEarth Layer Configurator](src/layer_config/README.md)
* [OnEarth Legend Generator](src/generate_legend/README.md)
* [OnEarth Metrics](src/onearth_logs/README.md)
* [OnEarth Scripts](src/scripts/README.md)
* [OnEarth Demo](src/demo/README.md)
* [mod_oems](src/modules/mod_oems/README.md)
* [mod_oemstime](src/modules/mod_oemstime/README.md)

## Other Information

* [Meta Raster Format](https://github.com/nasa-gibs/mrf/blob/master/README.md)
* [Tests](src/test/README.md)
* [Troubleshooting](doc/troubleshooting.md)
* [Contributing](CONTRIBUTING.md)

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
