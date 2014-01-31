**This software was originally developed at the Jet Propulsion Laboratory as Tiled WMS (https://github.com/nasajpl/tiledwms).  OnEarth is now the latest actively developed version.**

## OnEarth
### NASA Global Imagery Browse Services (GIBS)

OnEarth is a software package consisting of image formatting and serving modules which facilitate the deployment of a web service capable of efficiently serving standards-based requests for georeferenced raster imagery at multiple spatial resolutions including, but not limited to, full spatial resolution.  The software was originally developed at the Jet Propulsion Laboratory (JPL) to serve global daily composites of MODIS imagery.  Since then, it has been deployed and repurposed in other installations, including at the Physical Oceanography Distributed Active Archive Center (PO.DAAC) in support of the State of the Oceans (SOTO) visualization tool, the Lunar Mapping and Modeling Project (LMMP), and GIBS.

The source code contains the Meta Raster Format (MRF) plugin for GDAL, the mod_onearth Apache Module (formerly Tiled WMS/KML server), and associated configuration files and tools.

The software implements a data and image storage format driver for GDAL. The format supports extremely large, tiled, multi-resolution and multi-spectral data.  Sparse raster data is supported efficiently.  JPEG (lossy) and PNG (lossless) compression per tile are currently supported. Grayscale, color, indexed (palette) color models are supported.

For more information, visit https://earthdata.nasa.gov/gibs