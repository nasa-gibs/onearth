# Layer Configuration File
An XML configuration file exists for every OnEarth layer.  This file is read by the OnEarth layer configuration tool, along with the associated support configuration files, to generate the WMTS and TWMS service document and OnEarth cache configuration file(s).  The contents of the layer configuration file are listed below:

* **Identifier** - A unique identifier used as the WMTS Layer/Identifier and TWMS TiledGroup/Name values in the service GetCapabilities document.  Ideally the identifier does not use any special characters as it is included in all WMTS and TWMS http requests.
* **Title** - A human readable title used as the WMTS Layer/Title and TWMS TiledGroup/Title values in the service GetCapabilities document.
* **FileNamePrefix** - An internal "short name" used as the prefix for MRF index, image, and metadata file names.
* **HeaderFileName** - A file path to an existing MRF metadata file for the layer.
* **Compression** - The image file format.   Valid values are 'PNG', "JPG", "TIF".
* **Projection** - The identifier of the layer's associated projection as contained within the [projection configuration](config_support.md#projection-configuration) and [TileMatrixSets](config_support.md#tilematrixsets) support files.
* **TileMatrixSet** - The identifier of the layer's associated TileMatrixSet within the projection as contained within the [TileMatrixSets](config_support.md#tilematrixsets) support file.
* **EmptyTileSize** - The size, in bytes, of the layer's associated empty tile.  
  * The offset attribute is used to indicate an offset within the MRF's image file that points to the beginning of the empty tile.  If the empty tile is at the beginning of the MRF image file, then the offset is '0'.
* **Pattern(s) (Optional)** - Pre-generated URL request patterns that are compiled into the OnEarth cache configuration file for optimized request matching.  See [Patterns](patterns.md) for more information.
* **EnvironmentConfig** - The file path to the layer's associated [environment configuration](config_support.md#environment-configuration) support file.
* **ArchiveLocation** - The directory name within which MRF index, image, and metadata files will be placed.
* The static attribute indicates whether the layer varies by date (false) or is a single static image (true).
* The year attribute indicates whether files are grouped into subdirectories by year (true) or are all in the base directory (false).
* The root attribute references the unique identifier of the layer's associated archive location as contained in the [archive configuration](config_support.md#archive-configuration) support file.
* **ColorMap (Optional)** - A URL to the layer's associated colormap, if one exists, to be included in the WMTS GetCapabilities service document.
* **Time** - The ISO 8601 time range for the layer.  The tool may be configured to scan the file system to detect the the time (e.g., `<Time>DETECT</Time>`).  See [Time Detection](time_detection.md) for details.

A sample layer configuration file is shown here:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LayerConfiguration>
    <Identifier>MODIS_Aqua_Cloud_Effective_Radius_v6</Identifier>
    <Title>MODIS_Aqua_Cloud_Effective_Radius_v6</Title>
    <FileNamePrefix>MYG06_L1D_CER</FileNamePrefix>
    <HeaderFileName>/etc/onearth/config/headers/MYG06_L1D_CERTTTTTTT_.mrf</HeaderFileName>
    <Compression>PNG</Compression>
    <TileMatrixSet>2km</TileMatrixSet>
    <EmptyTileSize offset="0">1397</EmptyTileSize>
    <Projection>EPSG:4326</Projection>
    <EnvironmentConfig>/etc/onearth/config/conf/environment_geographic.xml</EnvironmentConfig>
    <ArchiveLocation static="false" year="true" root="geographic-aqua">MYG06_L1D_CER</ArchiveLocation>
    <ColorMap>MODIS_Aqua_Cloud_Effective_Radius_v6.xml</ColorMap>
    <Time>DETECT/DETECT/P1D</Time>
</LayerConfiguration>
```
