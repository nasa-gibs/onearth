# Support Configuration Files

The OnEarth configuration process requires the following support configuration files:

* **Archive Configuration** - Configurable file system archive locations for logically separated MRFs.
* **Projection Configuration** - Projection-specific metadata required when building WMTS and TWMS service documents.
* **Environment Configuration** - Environment specific paths for items such as service location URLs.
* **Tile Matrix Sets** - WMTS TileMatrixSet XML elements used during WMTS GetCapabilities generation.
* **WMTS GetCapabilities Base** - XML content used as a base for the WMTS GetCapabilities XML during generation.
* **TWMS GetCapabilities Base** - XML content used as a base for the TWMS GetCapabilities XML during generation.
* **TWMS GetTileService Base** - XML content used as a base for the TWMS GetTileService XML during generation.


## Archive Configuration
The archive configuration file contains a listing of "archive" file system locations.  Each "archive" location represents a separate top level directory within which MRF files will be located.  This allows for logical organization of an MRF archive based on factors such as projection, mission, etc.  Each archive location is identified by a unique name, specified in the id attribute, which is used for to reference the archive location outside of the file.  A sample archive configuration file is included below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ArchiveConfiguration>
    <Archive id="antarctic">
        <Location>/archive/imagery/antarctic/</Location>
    </Archive>
</ArchiveConfiguration>
```

## Projection Configuration
The projection configuration file contains a set of metadata elements for each projection supported during imagery access.  The metadata associated with each projections includes the following:

* **Well Known Text Spatial Reference System**  - The well-known text representation of the projection's spatial reference system providing a standard textual representation for spatial reference system information.  The definitions of the well-known text representation are modeled after the POSC/EPSG coordinate system data model. A dataset's coordinate system is identified by the PROJCS keyword if the data is in projected coordinates, by GEOGCS if in geographic coordinates, or by GEOCCS if in geocentric coordinates. WKT values can be found on the SpatialReference.org website.
* **WGS 84 Bounding Box** - The lower-left and upper-right corners defining the extent of the projection in WGS 84 (urn:ogc:def:crs:OGC:2:84) coordinate reference system.
* **"Native" Bounding Box** - The lower-left and upper-right corners defining the extent of the projection in the projection's coordinate reference system's units.

Each projection is identified by a unique name, specified in the id attribute, which is used for to reference the projection outside of the file.  A sample projection configuration file is included below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ProjectionConfiguration>
    <Projection id="EPSG:3857">
        <WKT><![CDATA[PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"],AUTHORITY["EPSG","3857"]]]]></WKT>
        <WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
            <LowerCorner>-180 -85</LowerCorner>
            <UpperCorner>180 85</UpperCorner>
        </WGS84BoundingBox>
        <BoundingBox crs="urn:ogc:def:crs:EPSG::3857">
            <LowerCorner>-20037508.34278925 -20037508.34278925</LowerCorner>
            <UpperCorner>20037508.34278925 20037508.34278925</UpperCorner>
        </BoundingBox>
    </Projection>
    <Projection id="EPSG:4326">
        <WKT><![CDATA[GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]]]></WKT>
        <WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
            <LowerCorner>-180 -90</LowerCorner>
            <UpperCorner>180 90</UpperCorner>
        </WGS84BoundingBox>
    </Projection>
</ProjectionConfiguration>
```

## Environment Configuration

The environment configuration file contains information that the OnEarth layer configuration tool uses during service metadata and cache configuration file creation.  The information associated with each environment includes the following:

* **GetCapabilities Location** - The file system path where the WMTS and TWMS GetCapabilities XML files are copied after generation.
* **GetTileService Location** - The file system path where the TWMS GetTileService XML file should be placed for external access.
* **Cache Location** - The file system path where the WMTS and TWMS OnEarth cache config binary and XML files are copied after generation. The base filename is specified using the "basename" attribute.
* **Staging Location** - The file system path where intermediary and final configuration files are staged.
* **Service URL** - The base URL for WMTS and TWMS tiled access used during GetCapabilities XML creation.
* **Legend Location** - The file system path where legend images are copied after generation. 
* **Legend URL** - The base URL for external access to legend images.
* **ColorMap Location** - The file system path where color map files may be found. 
* **ColorMap URL** - The base URL for external access to color maps.
* **StyleJSON Location** - (Optional) The file system path where style JSON files may be found. 
* **StyleJSON URL** - (Optional) The base URL for external access to style JSON files.
* **MapfileLocation** - (Optional) The location of the Mapfile for MapServer.
* **MapfileStagingLocation** (Optional) The location to stage configuration files for MapServer.
* **MapfileConfigLocation** (Optional) The location of configuration files for MapServer.
* **ReprojectEndpoint** (Optional) Used for reprojected layers. The endpoint location relative to the base server URL for accessing reprojected layers.
* **ReprojectApacheConfigLocation** (Optional) Used for reprojected layers. This location is where Apache configuration files for reprojected layers are stored. As such, this must be a location Apache is configured to read upon startup (for example `/etc/httpd/conf.d`, or a location specified by an `Includes` directive in your Apache config).
* **ReprojectLayerConfigLocation** (Optional) Used for reprojected layers. This is the base Apache configuration directory location for reprojected layers.

The environment configuration does not have unique identifier.  Reference to the environment configuration is done through referencing the file path.  A sample environment configuration file is included below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<EnvironmentConfiguration>
    <GetCapabilitiesLocation service="wmts">/srv/www/onearth/wmts/epsg3857/</GetCapabilitiesLocation>
    <GetCapabilitiesLocation service="twms">/srv/www/onearth/twms/epsg3857/.lib/</GetCapabilitiesLocation>
    <GetTileServiceLocation>/srv/www/onearth/twms/epsg3857/.lib/</GetTileServiceLocation>
    <CacheLocation service="wmts" basename="cache_all_wmts">/archive/imagery/epsg3857/</CacheLocation>
    <CacheLocation service="twms" basename="cache_all_twms">/archive/imagery/epsg3857/</CacheLocation>
    <StagingLocation service="wmts">/etc/onearth/config/wmts/EPSG3857/</StagingLocation>
    <StagingLocation service="twms">/etc/onearth/config/twms/EPSG3857/</StagingLocation>
    <ServiceURL service="wmts">http://onearth.project.org/wmts/epsg3857/</ServiceURL>
    <ServiceURL service="twms">http://onearth.project.org/twms/epsg3857/</ServiceURL>
    <LegendLocation>/usr/share/onearth/legends</LegendLocation>
    <LegendURL>http://onearth.project.org/legends/</LegendURL>
    <ColorMapLocation>/usr/share/onearth/demo/colormaps/</ColorMapLocation>
    <ColorMapURL>http://onearth.project.org/colormaps/</ColorMapURL>
    <StyleJSONLocation>/usr/share/onearth/demo/gl-styles/</StyleJSONLocation>
    <StyleJSONURL>http://localhost/gl-styles/</StyleJSONURL>
    <MapfileLocation basename="epsg3857">/usr/share/onearth/demo/mapserver/</MapfileLocation>
    <MapfileStagingLocation>/usr/share/onearth/layer_config/mapserver/EPSG3857/</MapfileStagingLocation>
    <MapfileConfigLocation basename="EPSG3857">/etc/onearth/config/mapserver/</MapfileConfigLocation>
    <ReprojectEndpoint service="wmts">/wmts/epsg3857</ReprojectEndpoint>
    <ReprojectEndpoint service="twms">/twms/epsg3857</ReprojectEndpoint>
    <ReprojectApacheConfigLocation service="wmts" basename="onearth-reproject-wmts">/etc/httpd/conf.d/</ReprojectApacheConfigLocation>
    <ReprojectApacheConfigLocation service="twms" basename="onearth-reproject-twms">/etc/httpd/conf.d/</ReprojectApacheConfigLocation>
    <ReprojectLayerConfigLocation service="wmts">/srv/www/onearth/wmts/epsg3857/</GetCapabilitiesLocation>
    <ReprojectLayerConfigLocation service="twms">/srv/www/onearth/twms/epsg3857/</GetCapabilitiesLocation>
</EnvironmentConfiguration>
```

## TileMatrixSets
The Tile Matrix Sets configuration file contains a superset of all WMTS TileMatrixSet XML elements that are included in the WMTS GetCapabilities file during generation.  Tile Matrices are organized by projection.  The projection id identified by a unique name, specified in the id attribute, which is used for reference to the projection outside of the file.  The individual TileMatrixSet elements are uniquely identified by the Identifier child element, which is the primary identifier of the TileMatrixSet according to the WMTS specification.  A sample Tile Matrix Sets configuration file is included below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TileMatrixSets xmlns:ows="http://www.opengis.net/ows/1.1">
   <Projection id="EPSG:3857">
      <TileMatrixSet>
         <ows:Identifier>GoogleMapsCompatible_Level3</ows:Identifier>
         <ows:SupportedCRS>urn:ogc:def:crs:EPSG:6.18:3:3857</ows:SupportedCRS>
         <WellKnownScaleSet>urn:ogc:def:wkss:OGC:1.0:GoogleMapsCompatible</WellKnownScaleSet>
         <TileMatrix>
            <ows:Identifier>0</ows:Identifier>
            <ScaleDenominator>559082264.0287178</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>1</MatrixWidth>
            <MatrixHeight>1</MatrixHeight>
         </TileMatrix>
         <TileMatrix>
            <ows:Identifier>1</ows:Identifier>
            <ScaleDenominator>279541132.0143589</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>2</MatrixWidth>
            <MatrixHeight>2</MatrixHeight>
         </TileMatrix>
         <TileMatrix>
            <ows:Identifier>2</ows:Identifier>
            <ScaleDenominator>139770566.0071794</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>4</MatrixWidth>
            <MatrixHeight>4</MatrixHeight>
         </TileMatrix>
         <TileMatrix>
            <ows:Identifier>3</ows:Identifier>
            <ScaleDenominator>69885283.00358972</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>8</MatrixWidth>
            <MatrixHeight>8</MatrixHeight>
         </TileMatrix>
      </TileMatrixSet>
   </Projection>
   <Projection id="EPSG:4326">
        <TileMatrixSet>
         <ows:Identifier>EPSG4326_16km</ows:Identifier>
         <ows:SupportedCRS>urn:ogc:def:crs:OGC:1.3:CRS84</ows:SupportedCRS>
         <TileMatrix>
            <ows:Identifier>0</ows:Identifier>
            <ScaleDenominator>223632905.6114871</ScaleDenominator>
            <TopLeftCorner>-180 90</TopLeftCorner>
            <TileWidth>512</TileWidth>
            <TileHeight>512</TileHeight>
            <MatrixWidth>2</MatrixWidth>
            <MatrixHeight>1</MatrixHeight>
         </TileMatrix>
         <TileMatrix>
            <ows:Identifier>1</ows:Identifier>
            <ScaleDenominator>111816452.8057436</ScaleDenominator>
            <TopLeftCorner>-180 90</TopLeftCorner>
            <TileWidth>512</TileWidth>
            <TileHeight>512</TileHeight>
            <MatrixWidth>3</MatrixWidth>
            <MatrixHeight>2</MatrixHeight>
         </TileMatrix>
         <TileMatrix>
            <ows:Identifier>2</ows:Identifier>
            <ScaleDenominator>55908226.40287178</ScaleDenominator>
            <TopLeftCorner>-180 90</TopLeftCorner>
            <TileWidth>512</TileWidth>
            <TileHeight>512</TileHeight>
            <MatrixWidth>5</MatrixWidth>
            <MatrixHeight>3</MatrixHeight>
         </TileMatrix>
      </TileMatrixSet>
   </Projection>
</TileMatrixSets>
```
 
## WMTS GetCapabilities Base
When generating the WMTS GetCapabilities XML file, there are a set of high level static elements containing information about the project and image services.  For simpler generation, OnEarth uses a static configuration file containing this base WMTS GetCapabilities content.  Details regarding the contents of this section can be found in the WMTS specification.  Note that the OnEarth configuration file contains a "{ServiceURL}" pattern that is replaced by the Service URL value as contained within the environment configuration file specified above.   A sample WMTS GetCapabilities Base configuration file is included below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://www.opengis.net/wmts/1.0
    http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
    version="1.0.0">
    <ows:ServiceIdentification>
        <ows:Title xml:lang="en">Project Imagery Services</ows:Title>
        <ows:Abstract xml:lang="en">Imagery for our project's data.</ows:Abstract>
        <ows:Keywords>
            <ows:Keyword>World</ows:Keyword>
            <ows:Keyword>Global</ows:Keyword>
        </ows:Keywords>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        <ows:Fees>none</ows:Fees>
        <ows:AccessConstraints>none</ows:AccessConstraints>
    </ows:ServiceIdentification>
    <ows:ServiceProvider>
        <ows:ProviderName>Project Name</ows:ProviderName>
        <ows:ProviderSite xlink:href="http://onearth.project.org/"/>
        <ows:ServiceContact>
            <ows:IndividualName></ows:IndividualName>
            <ows:PositionName></ows:PositionName>
            <ows:ContactInfo>
                <ows:Address>
                    <ows:DeliveryPoint></ows:DeliveryPoint>
                    <ows:City></ows:City>
                    <ows:AdministrativeArea></ows:AdministrativeArea>
                    <ows:PostalCode></ows:PostalCode>
                    <ows:Country></ows:Country>
                    <ows:ElectronicMailAddress></ows:ElectronicMailAddress>
                </ows:Address>
            </ows:ContactInfo>
        </ows:ServiceContact>
    </ows:ServiceProvider>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="{ServiceURL}/1.0.0/WMTSCapabilities.xml">
                        <ows:Constraint name="GetEncoding">
                            <ows:AllowedValues>
                                <ows:Value>RESTful</ows:Value>
                            </ows:AllowedValues>
                        </ows:Constraint>
                    </ows:Get>
                    <ows:Get xlink:href="{ServiceURL}/wmts.cgi?">
                        <ows:Constraint name="GetEncoding">
                            <ows:AllowedValues>
                                <ows:Value>KVP</ows:Value>
                            </ows:AllowedValues>
                        </ows:Constraint>
                    </ows:Get>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="{ServiceURL}">
                        <ows:Constraint name="GetEncoding">
                            <ows:AllowedValues>
                                <ows:Value>RESTful</ows:Value>
                            </ows:AllowedValues>
                        </ows:Constraint>
                    </ows:Get>
                    <ows:Get xlink:href="{ServiceURL}/wmts.cgi?">
                        <ows:Constraint name="GetEncoding">
                            <ows:AllowedValues>
                                <ows:Value>KVP</ows:Value>
                            </ows:AllowedValues>
                        </ows:Constraint>
                    </ows:Get>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <Contents>
    </Contents>
    <ServiceMetadataURL xlink:href="{ServiceURL}"/>
</Capabilities>
```
 
## TWMS GetCapabilities Base
When generating the TWMS GetCapabilities XML file, there are a set of high level static elements containing information about the project and image services.  For simpler generation, OnEarth uses a static configuration file containing this base TWMS GetCapabilities content.  Details regarding the contents of this section can be found in the WMS specification.  Note that the OnEarth configuration file contains a "{ServiceURL}" pattern that is replaced by the Service URL value as contained within the environment configuration file specified above.   A sample TWMS GetCapabilities Base configuration file is included below:

```xml
<?xml version='1.0' encoding="UTF-8" standalone="no" ?>
<!DOCTYPE WMT_MS_Capabilities SYSTEM "http://localhost/WMS_MS_Capabilities.dtd" [ <!ELEMENT VendorSpecificCapabilities EMPTY> ]>
<WMT_MS_Capabilities version="1.1.1">
  <Service>
    <Name>OGC:WMS</Name>
    <Title>Project Imagery Services</Title>
    <Abstract>Imagery for our project's data.</Abstract>
    <KeywordList>
      <Keyword>WMS</Keyword>
      <Keyword>Earth</Keyword>
    </KeywordList>
    <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="http://earthdata.nasa.gov/" />
    <ContactInformation>
      <ContactPersonPrimary>
        <ContactPerson></ContactPerson>
        <ContactOrganization></ContactOrganization>
      </ContactPersonPrimary>
      <ContactElectronicMailAddress></ContactElectronicMailAddress>
    </ContactInformation>
    <Fees>none</Fees>
    <AccessConstraints>none</AccessConstraints>
  </Service>
  <Capability>
    <Request>
      <GetCapabilities>
        <Format>application/vnd.ogc.wms_xml</Format>
        <DCPType>
          <HTTP>
            <Get>
              <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="{ServiceURL}/twms.cgi?" />
            </Get>
          </HTTP>
        </DCPType>
      </GetCapabilities>
      <GetMap>
        <Format>image/jpeg</Format>
        <Format>image/png</Format>
        <DCPType> <HTTP> <Get>
          <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="{ServiceURL}/twms.cgi?" />
        </Get> </HTTP> </DCPType>
      </GetMap>
      <GetTileService>
        <Format>text/xml</Format>
        <DCPType><HTTP><Get>
          <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="{ServiceURL}/twms.cgi?" />
        </Get></HTTP></DCPType>
      </GetTileService>
    </Request>
    <Exception>
      <Format>application/vnd.ogc.se_xml</Format>
    </Exception>
    <VendorSpecificCapabilities/>
    <UserDefinedSymbolization SupportSLD="0" UserLayer="0" UserStyle="1" RemoteWFS="0" />
    <Layer queryable="0">
      <Title>Imagery Product Services</Title>
      <SRS></SRS>
      <CRS></CRS>
    </Layer>
  </Capability>
</WMT_MS_Capabilities>
```
 
## TWMS GetTileService Base
When generating the TWMS GetTileService XML file, there are a set of high level static elements containing information about the project and image services.  For simpler generation, OnEarth uses a static configuration file containing this base TWMS GetTileService content.  Details regarding the contents of this section can be found in the WMS specification.  Note that the OnEarth configuration file contains a "{ServiceURL}" pattern that is replaced by the Service URL value as contained within the environment configuration file specified above.   A sample TWMS GetTileService Base configuration file is included below:

```xml
<WMS_Tile_Service version="0.1.0">
  <Service>
    <Name>GIBS:WMS:Tile</Name>
    <Title>WMS Tile Service</Title>
    <Abstract>Tiled WMS service, tiled in a global grid</Abstract>
    <KeywordList>
      <Keyword>WMS</Keyword>
      <Keyword>Tile</Keyword>
      <Keyword>Global</Keyword>
      <Keyword>Earth</Keyword>
    </KeywordList>
    <OnlineResource xmlns:xlink="http://www.w3.orf/1999/xlink" xlink:type="simple" xlink:href="http://earthdata.nasa.gov"/>
    <ContactInformation>
      <ContactPersonPrimary>
        <ContactPerson></ContactPerson>
        <ContactOrganization></ContactOrganization>
      </ContactPersonPrimary>
      <ContactElectronicMailAddress></ContactElectronicMailAddress>
    </ContactInformation>
    <Fees>none</Fees>
    <AccessConstraints>none</AccessConstraints>
  </Service>
  <TiledPatterns>
    <OnlineResource xlink:href="{ServiceURL}" xlink:type="simple" xmlns:xlink="http://www.w3.org/1999/xlink"/>
    <BoundingBox minx="{minx}" miny="{miny}" maxx="{maxx}" maxy="{maxy}" />
  </TiledPatterns>
</WMS_Tile_Service>
```
