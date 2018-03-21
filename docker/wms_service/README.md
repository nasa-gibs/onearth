# OnEarth 2 WMS Service Container

This container uses Mapserver/GDAL to serve GIBS layers in WMS format. It uses
the GDAL WMTS driver to create imagery from existing GIBS WMTS sources.

## Patched GDAL

This container uses a patched version of the WMTS driver in GDAL 2.2.3. The main
change is that a `<Dimension>` element is now used to fill in extra,
non-standard dimensions that may appear in the WMTS URL template, as described
in the source GetCapabilities file.

For example, if the GetCapabilities file has a URL template for the selected
layer that looks like this:

`<ResourceURL format="image/png" resourceType="tile"
template="https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/AMSR2_Snow_Water_Equivalent/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"/>`

by default, the GDAL WMTS driver will fill in the non-standard dimension
`{Time}` with whatever default parameter is indicated by the GetCapabilities
file.

Using the modified GDAL WMTS driver, the Time dimension (or any other
non-standard dimension) can instead be filled in with a custom value provided in
the GDAL XML source, like this:

`<Dimension name='Time'>1986-06-17</Dimension>`

The `name` attribute should contain the name of the dimension to replace, and
the text content of the node should be the value to replace it with.

The `<Dimension>` element can appear multiple times, so it can be used for
multiple non-standard dimensions in the URL template.

Note that if the dimension specified in the XML doesn't appear in the URL
template in the GetCapabilities file, it will be ignored.

Here's a sample GDAL WMTS XML source file using this new element.

```
<GDAL_WMTS>
    <Dimension name='Time'>%time%</Dimension>
    <GetCapabilitiesUrl>https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml</GetCapabilitiesUrl>
    <Layer>AMSR2_Snow_Water_Equivalent</Layer>
    <Style>default</Style>
    <TileMatrixSet>2km</TileMatrixSet>
    <DataWindow>
        <UpperLeftX>-180</UpperLeftX>
        <UpperLeftY>90</UpperLeftY>
        <LowerRightX>180</LowerRightX>
        <LowerRightY>-90</LowerRightY>
    </DataWindow>
    <BandsCount>4</BandsCount>
    <Cache />
    <ZeroBlockHttpCodes>404</ZeroBlockHttpCodes>
    <ZeroBlockOnServerException>true</ZeroBlockOnServerException>
</GDAL_WMTS>
```

## Configuration tool

This container includes a basic tool to set up all the layers specified in a
particular GetCapabilities file.

The syntax is: `make_wms.py {outfile}`. The URL of the GC file is set as a
global at the top of the script.

## Default container setup

The default container WMS endpoint is at `http://localhost/wms?`. Currently, it
configures all the layers available at the
`https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/` endpoint.

Sample url:
http://localhost:8082/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=MODIS_Terra_SurfaceReflectance_Bands121&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=768&BBOX=-135%2C-270%2C135%2C270&time=2012-01-01
