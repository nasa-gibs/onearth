## mod_oems

OnEarth module that acts as a wrapper around Mapserver that allows for WMS and WFS requests. Mapserver must be installed in order for the module to function properly.

## Build

To build the module:

```Shell
cd onearth/src/modules/mod_oems
make
```

## Install

Copy the module files into your Apache modules directory.

```Shell
cp onearth/src/modules/mod_oems/.libs/mod_oems.so {APACHE_HOME}/modules/
```

Edit the Apache httpd.conf and include the following:

```Shell
LoadModule oems_module modules/mod_oems.so
```

**Apache Config Directives:**

`MapfileDir`: Location on the server of the Mapserver mapfiles.
`DefaultMapfile`: Filename of the default mapfile to use relative to `MapfileDir`.

See [Apache Configuration](../../../doc/config_apache.md) for more details on configuration.

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)

