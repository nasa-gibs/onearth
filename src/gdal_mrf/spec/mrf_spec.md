## Meta Raster Format (MRF) Specification v0.3.0 (Draft)

The Meta Raster Format (MRF) is an image and data storage format designed for fast access to imagery within a georeferenced tile pyramid at discrete resolutions. 

![](https://raw.githubusercontent.com/nasa-gibs/onearth/develop/src/gdal_mrf/spec/pyramids.png)

The format supports extremely large, tiled, multi-resolution and multi-spectral data. Sparse raster data is supported efficiently.  JPEG (lossy) and PNG (lossless) compression per tile are currently supported.  Grayscale, color, indexed (palette) color models are supported.

The file format was originally developed at the NASA Jet Propulsion Laboratory.

MRF is composed of metadata, data, and index files with the respective extensions: .mrf, .ppg/.pjg, and .idx. 

### MRF metadata file (.mrf)

Header XML metadata file containing descriptive information about imagery for use with GDAL routines.  All tiles store the same set of metadata.

    MRF_META: root node
        Raster: image metadata
            Size: size of overview
            Compression: JPEG, PNG, PPNG (Paletted-PNG)
            Quality: image quality
            PageSize: dimension of tiles
        Rsets: single image or uniform scaling factor
        GeoTags: 
            BoundingBox: bounding box for imagery

Additional custom elements are used with mod_onearth.

Example:
 
    <MRF_META>
        <Raster>
            <Size x="81920" y="40960" c="1" />
            <Compression>PPNG</Compression>
            <DataValues NoData="0" />
            <Quality>85</Quality>
            <PageSize x="512" y="512" c="1" />
        </Raster>
        <Rsets model="uniform" />
        <GeoTags>
            <BoundingBox minx="-180" miny="-90" maxx="180" maxy="90" />
        </GeoTags>
    </MRF_META> 

### MRF data file (.ppg/.pjg)

The Pile of PNGs (ppg) or Pile of JPEGS (pjg) data file contains blocks of concatenated images.  Each block is a self-contained image that is either PNG or JPEG.  The full resolution base of the pyramid is first, followed by any subsequent pyramid levels.  The data file eliminates the need to store tiles in independent files, thereby minimizing file system operations and significantly improving performance.

RGB and indexed colors are supported.  Modifications to the file are done only via appends.  With mod_onearth, the file starts with an empty tile.

![](https://raw.githubusercontent.com/nasa-gibs/onearth/develop/src/gdal_mrf/spec/tiledata.png)

### MRF index file (.idx)

The index file contains spatially organized pointers to individual tiles in an MRF (ppg/pjg) data file.   Tiles are referenced by offset within the data file and size of the tile (both 64-bit integers).  Tiles have a top-left origin.  The index is fixed-sized and updated as tiles are modified.

![](https://raw.githubusercontent.com/nasa-gibs/onearth/develop/src/gdal_mrf/spec/tileidx.png)
