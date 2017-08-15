# OnEarth Reprojection

OnEarth is able to reproject EPSG:4326 tiled layers into EPSG:3857 (WebMercator) on-the-fly using the `mod_reproject` Apache module.


# How It Works
mod_reproject requires source imagery that's available via a standard WMTS REST endpoint. It does not require access to the source files and reprojects tiles by downloading them from the source endpoint via subrequests, processing them, then sending the final reprojected output tile to the original requestor.

To get it working, you'll need a WMTS tile endpoint that serves tiles in EPSG:4326 projection (can be local or a remote source proxied to a local URI).

# Setup

Start by compiling and installing the [mod_receive](../src/modules/mod_receive), [mod_reproject](../src/modules/mod_reproject), [mod_wmts_wrapper](../src/modules/mod_wmts_wrapper), and [mod_wtms](../src/modules/mod_twms) (if TWMS is desired) Apache modules.

`mod_wmts_wrapper` isn't necessary for basic WMTS reprojection, but you'll need to configure it if you want handle WMTS key-value pair requests, have WMTS error return messages, or Date dimension handling.

It's not required to have mod_onearth installed or configured to use layer reprojection.

To manually set up the configuration for these modules, refer to their individual documentation. However, it's easier to use the `oe_configure_layer` tool.

To use the tool, configure a reprojection configuration XML file (details below), and run it with `oe_configure_layer` the way you would any other layer configuration file.

# Configuration

`mod_reproject`/`mod_wmts_wrapper` requires the following additional XML elements in your base configuration files:


### Environment Config
Make sure that the `<ReprojectApacheConfigLocation>` and `<ReprojectLayerConfigLocation>` elements are located in the environment config file you'll be using, and that there's one for each service (wmts or twms) that you wish to configure for. See [config support](config_support.md) for more information.

### Layer Config File
Reprojected layers require a differently-structured XML file from the normal OnEarth layer config. 

**Note that with reprojected layers, the `oe_configure_layer` tool actually configures all the reprojected layers from an external endpoint at once, instead of individually. You'll only need one configuration file per external endpoint.**

The reprojected layer config tool scrapes data from the GetCapabilities file of the specified endpoint, then configures the layers using data from that file. Here's an example:

```
<ReprojectLayerConfig>
    <GetCapabilitiesURI>https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml</GetCapabilitiesURI>
    <SrcLocation internal="/outside" external="https://gibs.earthdata.nasa.gov" />
    <EnvironmentConfig>/etc/onearth/config/conf/environment_webmercator.xml</EnvironmentConfig>
    <ExcludeLayer>private</ExcludeLayer>
</ReprojectLayerConfig>
```

#### Reproject Config Elements:

`<ReprojectLayerConfig>` (required) -- Base element that contains all the layer reproject information. When it encounters this element, oe_configure_layer will process this layer for mod_reproject.

`<SrcWMTSGetCapabilitiesURI>` (required) -- Specifies the GetCapabilities file that oe_configure_layer will use to build the layer configs, including source URL info.

-----

`<SrcLocationRewrite>` (required) -- This specifies the source endpoint.

##### Attributes:

`internal` (required) -- The internal path for the tile endpoint. Since Apache subrequests can't be made to destinations outside the server, this needs to be either the path of the mod_onearth or other WMTS REST tile server instance running on the same machine, or the internal location of an external server being proxied.

`external` (required) -- The base externally-accessible URL of the source endpoint.

-------

`<EnvironmentConfig>` (required) -- The environment configuration file to be used in setting up this endpoint. (make sure that it has the reproject-specific elements mentioned earlier in this doc).

`<ExcludeLayer>` (optional, can be multiple) -- Include one of these elements for each layer from the source endpoint that you don't want reprojected. The layer tool will skip any layers in the source GetCapabilities it finds with this name.

`<IncludeLayer>` (optional, can be multiple) -- Include one of these elements for each layer that you want to exclusively configure. **If this element is found, only the layers specified in each element will be configured, and all others will be ignored.**

