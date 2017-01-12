# Creating Image Archive

## Introduction

This describes how to create an image archive for the OnEarth server by generating the proper directory structures for placing Meta Raster Format (MRF) files.

## Archive Location

Choose a location on the filesystem for the MRF archive.  This must be the same location as specified for "WMSCache" in the [Apache configuration](config_apache.md) and must accessible by Apache.  

The following archive location will be used for this example: `/usr/share/onearth/demo/data/EPSG4326/`

The following data layer name will be used for this example: `MODIS_Aqua_Aerosol`

Typically, the data for each layer is contained in a subdirectory with the data layer name. In this case: `/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol`

## Static vs. Time Dependent Layers

Layers in OnEarth can either be static or time dependent.  

Time dependent refers to layers that have new data over time.  For the Global Imagery Browse Services (GIBS), most data products are updated daily for several years.  A new MRF file is created for each day and can be referenced in a request by the `TIME=` parameter.

Static, on the other hand, refers to a layer that does not change over time.  Therefore, the layer can be represented as a single file.  The `TIME=` parameter in a request is ignored.

The OnEarth server expects an MRF archive for time dependent layers to be logically ordered.  The following directory scheme is used: `/archive/layer/year/`

So following our example, we expect to see something like this for each year with existing data:

```
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2013/
```

Each directory then contains MRF files for each available day.
```
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015002_.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015002_.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015002_.ppg
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015001_.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015001_.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2015/MODIS_Aqua_Aerosol2015001_.ppg
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014365_.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014365_.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014365_.ppg
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.ppg

```

Note that a timestamp for the day is appended to each file.  This is important for the server to know how to map the time in the request to a file.  
The file names must be in the format: `<FILENAME><YEAR><ORDINAL_DATE>_.<EXT>` (notice the underscore before the extension).


Static layers do not need a "year" directory. The MRF files can simply exist in the archive directory or the "layer" subdirectory: 

```
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol.ppg
```

### Default Files

The OnEarth server also expects a set of default MRF files for time dependent layers.  These files are used to represent the "current" or "default" day when the `TIME=` parameter is not specified in a request.  The files are also used by the server for initializing tests and referencing blank/empty tiles. This does not apply to static layers.

Default files must exist in a special "YYYY" directory like the following: `/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/YYYY/`

The contents of this directory should be whatever MRF is used as the "current" day, but with "TTTTTTT" substituted for the ordinal date.  So the "YYYY" directory should contain something like the following:
```
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/YYYY/MODIS_Aqua_AerosolTTTTTTT_.idx
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/YYYY/MODIS_Aqua_AerosolTTTTTTT_.mrf
/usr/share/onearth/demo/data/EPSG4326/MODIS_Aqua_Aerosol/YYYY/MODIS_Aqua_AerosolTTTTTTT_.ppg
```

These "TTTTTTT" files can simply be soft links to the latest date, rather than be copied or newly generated.

If the default files must exist outside of the archive (e.g., in the case of a read-only archive where links can't be updated) or if they require different file names, the "Default<Data|Index|ZIndex>FileName" options of the layer configuration files can be used.

For time dependent layers, if no default files exist or if the files cannot be accessed, the last available time within the layer's time period configuration will be used.

If no files can be accessed, an empty tile will be returned.


### MRF Files

*How come there are three MRF files for each set?*

An MRF file (or "file set" technically) is actually a triplet of files:
1) a header file (.mrf),
2) an index file (.idx), and
3) a data file (.pjg/ppg/ptf/lrc).

* The header is an XML metadata file containing descriptive information about imagery for use with GDAL routines. All tiles store the same set of metadata.
* The index file contains spatially organized pointers to individual tiles in an MRF data file.
* The Pile of PNGs (ppg) or Pile of JPEGS (pjg) or Pile of TIFFs (ptf) data file contains blocks of concatenated images. Esri LERC (lrc) format is also supported.

Only the header and data file must exist and be co-located in the archive.  The header files are used only on the server for configuring layers, but may be useful to keep in the archive for consistency and troubleshooting.

For more information, see the [MRF Specification](https://github.com/nasa-gibs/mrf/blob/master/spec/mrf_spec.md)


### Generating New MRF Files

MRF files can be generated using GDAL with the MRF driver. A simple way to generate bulk MRF imagery is by using the mrfgen tool.

For more information on generating MRF files, see the documentation for [mrfgen](../src/mrfgen/README.md).

Vecto based datasets, including vector tiles, can be generated using [vectorgen](../src/vectorgen/README.md).