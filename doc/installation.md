## Installation

This are instructions on how to install OnEarth on CentOS/RedHat Linux 6.4 or greater.

## Preconditions

* Apache 2.2 or 2.4
* Python 2.6 or 2.7

If needed, some dependencies on CentOS/RedHat 6 machines may be obtained by installing:

EPEL Repository

```
sudo yum -y install epel-release
```

Postgres Repository RPM

```
sudo yum -y install https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-6-x86_64/pgdg-centos96-9.6-3.noarch.rpm
```

## RPM Installation

Download the latest OnEarth release (https://github.com/nasa-gibs/onearth/releases)

Unpackage the release .tar.gz file

```
tar -zxvf onearth-*.tar.gz
```

GIBS GDAL with the MRF driver

```
sudo yum -y install gibs-gdal-*
```

Optional Python packages via pip (included in onearth-config RPM); required for OnEarth configuration tools if RPM cannot run pip

```
sudo pip install lxml==3.8.0 pyparsing==2.2.0 parse_apache_configs==0.0.2
```

Optional Python packages via pip (included in onearth-vector RPM); required for OnEarth vectorgen if RPM cannot run pip

```
sudo pip install Fiona==1.7.0 Shapely==1.5.16 Rtree==0.8.0 mapbox-vector-tile==0.4.0 lxml==3.8.0
```

Install OnEarth packages

```
sudo yum -y install onearth-*
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
/usr/bin/oe_create_cache_config
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

mod_receive
``
/etc/httpd/modules/mod_receive.so
``

mod_reproject
``
/etc/httpd/modules/mod_reproject.so
``

mod_wmts_wrapper
``
/etc/httpd/modules/mod_wmts_wrapper.so
``

mod_twms
``
/etc/httpd/modules/mod_twms.so
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

OnEarth Tests
```
/usr/share/onearth/test*
```

## Next Steps

* [Run Demo](../src/demo/README.md)
* [Configuration](configuration.md)
* [Creating Image Archive](archive.md)


## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
