## mod_onearth

This is the Apache module for OnEarth.  This software is designed for serving OGC WMTS and OnEarth Tiled-WMS requests.  OnEarth is based on concatenating all tiles into a single binary data file with an external index file.  The module converts client requests into MRF index values and returns a selection of tiles back to the client.

## Build

To build the module:

```Shell
cd onearth/src/modules/mod_onearth
make
```

## Install

Copy the module files into your Apache modules directory.

```Shell
cp onearth/src/modules/mod_onearth/.libs/mod_onearth.so {APACHE_HOME}/modules/
```

Edit the Apache httpd.conf and include the following:

```Shell
LoadModule onearth_module modules/mod_onearth.so
```

**Apache Config Directives:**

`WMSCache`: Location of the cache configuration.

See [Apache Configuration](../../../doc/config_apache.md) for more details on configuration.

## Time Snapping

`mod_onearth` has some special features for imagery layers that take place across specific time periods. For more information, look at [Time Snapping](TIME_SNAPPING.md).

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
