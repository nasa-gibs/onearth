## Installation

This are instructions on how to install OnEarth on CentOS/RedHat Linux 6.4 or greater.

## Preconditions

* Apache 2.2 or greater
* Python 2.6 or 2.7

## RPM Installation

Download the latest OnEarth release (https://github.com/nasa-gibs/onearth/releases)

Unpackage the release .tar.gz file

```
tar -zxvf onearth-*.tar.gz
```

Install GIBS GDAL with the MRF driver

```
sudo yum -y install gibs-gdal-*
```

Install OnEarth packages

```
sudo yum -y install onearth-*
```

If needed, some dependencies on CentOS/RedHat 6 machines may be obtained by installing the Postgres Repository RPM

```
sudo yum -y install https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-6-x86_64/pgdg-centos96-9.6-3.noarch.rpm
```

For manual installation or to install or another OS, please refer to the specific component:

* [mod_onearth](../src/modules/mod_onearth/README.md)
* [mod_oems](../src/modules/mod_oems/README.md)
* [mod_oemstime](../src/modules/mod_oemstime/README.md)
* [mrfgen](../src/mrfgen/README.md)
* [OnEarth Layer Configurator](../src/layer_config/README.md)
* [OnEarth Legend Generator](../src/generate_legend/README.md)
* [OnEarth Metrics](../src/onearth_logs/README.md)
* [OnEarth Scripts](../src/scripts/README.md)
* [vectorgen](../src/vectorgen/README.md)

## Install Locations

These are the default install locations.

mod_onearth
```
/etc/httpd/modules/mod_onearth.so
/usr/bin//oe_create_cache_config
/usr/share/onearth/apache/*
/usr/share/onearth/apache/kml/*
```

mod_oetwms
```
/etc/httpd/modules/mod_oetwms.so
```

mod_oems
``
/etc/httpd/modules/mod_oems.so
``

mod_oemstime
``
/etc/httpd/modules/mod_oemstime.so
``

mrfgen
```
/usr/bin/mrfgen
/usr/bin/RGBApng2Palpng
/usr/bin/colormap2vrt.py
/usr/bin/overtiffpacker.py
/usr/share/onearth/mrfgen/*
```

OnEarth Layer Configurator
```
/usr/bin/oe_configure_layer
/usr/bin/oe_configure_reproject_layer.py
/usr/bin/oe_utils.py
/usr/bin/oe_generate_legend.py
/usr/bin/oe_generate_empty_tile.py
/etc/onearth/config/*
```

OnEarth Metrics
```
/usr/bin/onearth_metrics
/etc/onearth/metrics/*
```

OnEarth Demo
```
/usr/share/onearth/demo/*
/etc/httpd/conf.d/onearth-demo.conf
```

OnEarth Mapserver
```
/usr/bin/legend
/usr/bin/mapserv
/usr/bin/msencrypt
/usr/bin/scalebar
/usr/bin/shp2img
/usr/bin/shptree
/usr/bin/shptreetst
/usr/bin/shptreevis
/usr/bin/sortshp
/usr/bin/tile4ms
/usr/lib64/libmapserver.so*
/usr/include/mapserver/*
/usr/lib64/python2.6/site-packages/_mapscript*
/usr/lib64/python2.6/site-packages/mapscript*
```

vectorgen
```
/usr/bin/oe_vectorgen
/usr/share/onearth/vectorgen/*
/usr/include/spatialindex/*
/usr/lib64/libspatialindex*
/usr/lib64/pkgconfig/libspatialindex.pc
```

## Next Steps

* [Configuration](configuration.md)
* [Creating Image Archive](archive.md)


## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
