## mod_oemstime

OnEarth module for leveraging time snapping from Mapserver requests.

## Build

To build the module:

```Shell
cd onearth/src/modules/mod_oemstime
make
```

## Install

Copy the module files into your Apache modules directory.

```Shell
cp onearth/src/modules/mod_oemstime/.libs/mod_oemstime.so {APACHE_HOME}/modules/
```

Edit the Apache httpd.conf and include the following:

```Shell
LoadModule oemstime_module modules/mod_oemstime.so
```

**Apache Config Directives:**

`TWMSServiceURL`: Internal URL of OnEarth Tiled-WMS endpoint for time snapping. `{SRS}` keyword will automatically be replaced by the EPSG code in a request.

See [Apache Configuration](../../../doc/config_apache.md) for more details on configuration.

## Time Snapping

`mod_oemstime` utilizes the `mod_onearth` time snapping features for imagery layers that take place across specific time periods. For more information, look at [Time Snapping](TIME_SNAPPING.md).

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
