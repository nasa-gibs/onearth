## mod_oetwms

This is the legacy TWMS support module for OnEarth. This software is designed for serving OnEarth Tiled-WMS requests. This module enables the use of GetTileService requests.

## Build

To build the module:

```Shell
cd onearth/src/modules/mod_oetwms
make
```

## Install

Copy the module files into your Apache modules directory.

```Shell
cp onearth/src/modules/mod_onearth/.libs/mod_oetwms.so {APACHE_HOME}/modules/
```

Edit the Apache httpd.conf and include the following:

```Shell
LoadModule oetwms_module modules/mod_oetwms.so
```

**Apache Config Directives:**

`TWMSDirConfig`: Location of the getTileService XML file.

See [Apache Configuration](../../../doc/config_apache.md) for more details on configuration.

## mod_onearth

`mod_oetwms` is intended for use with [mod_onearth](../mod_onearth/README.md).

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
