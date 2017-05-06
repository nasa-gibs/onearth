# mod_wmts_wrapper

This module is designed as a wrapper around Apache modules like mod_redirect that only serve tiles via REST requests.

Right now it only works with mod_reproject.

## What it does

mod_wmts_wrapper does a few things:

- Converts KvP WMTS requests into REST, returning errors if necessary.
- Returns WMTS errors for problems with REST WMTS requests (i.e., non-existent layer)
- Integrates with mod_reproject so that it can handle layers that have a TIME parameter.
- Adds additional error handling to mod_reproject (i.e., tile out of bounds)

## Build/Install

### Dependencies
- mod_reproject.h (from [mod_reproject](https://github.com/lucianpls/mod_reproject))

First, you need to patch and compile mod_reproject. Download [mod_reproject](https://github.com/lucianpls/mod_reproject). (Note that mod_reproject has dependencies you'll need to install)

In the `src` directory, copy `mod_reproject.patch` from this repo and run `patch < mod_reproject.cpp`.

Edit `Makefile.lcl` for your environment and run `make install`.

Return to the mod_reproject_wrapper directory, then edit the `Makefile.lcl` for your environment and run `make install`.

## Time/Date Handling
mod_wmts_wrapper can rewrite mod_reproject configrations on the fly so that mod_reproject uses the correct URL for a requested date.

In order to use this, you need to modify the string used in the reproject configuration file specified by the `Reproject_ConfigurationFiles` directive.

For example, if you have line like this:

`Reproject_ConfigurationFiles source.config reproj.config`

in the `reproj.config` file you'll need to have a line like this:

`SourcePath /endpoint/layer/style/${date}/tilematrixset/`

mod_wmts_wrapper will then use the date from the current request to fill in the ${date} field in the source URL that mod_reproject uses.

## Integration with mod_onearth
mod_wmts_wrapper is designed such that mod_onearth, if configured in the same endpoint, will be the first to handle requests **unless the incoming request is a REST request that corresponds to a layer that's been configured with mod_reproject and mod_wmts_wrapper**.

**Note that mod_wmts is NOT compatible with any cgi scripts due to the order of the handlers, so make sure that you REMOVE wmts.cgi from the endpoint where you are running both mod_onearth and mod_reproject/mod_wmts_wrapper. mod_wmts_wrapper provides the same capabilities as the `wmts.cgi` that is included with OnEarth.**

## Configuration

mod_reproject_wrapper has two directives, each to be placed in a `<Directory>` block in your Apache config.

### WMTSWrapperRole String
This indicates what "role" a particular directory plays in your WMTS REST request. Roles are:

- root
- layer
- style
- tilematrixset

This configuration allows the module to correctly handle errors.

###WMTSWrapperEnableTime (On|Off)
Indicates whether or not mod_wmts_wrapper should handled TIME REST and KvP requests. Should be placed in the same `<Directory>` block as `WMTSWrapperRole layer`.

### Example config (starred entries are `mod_reproject` configuration directives):

```
<Directory /usr/share/onearth/demo/wmts-webmerc/>
        WMTSWrapperRole root
</Directory>

<Directory /usr/share/onearth/demo/wmts-webmerc/blue_marble>
        WMTSWrapperRole layer
        WMTSWrapperEnableTime on
</Directory>

<Directory /usr/share/onearth/demo/wmts-webmerc/blue_marble/default>
        WMTSWrapperRole style
</Directory>

<Directory /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7>
        WMTSWrapperRole tilematrixset
        * Reproject_RegExp GoogleMapsCompatible_Level7/\d{1,2}/\d{1,3}/\d{1,3}.(png|jpeg|jpg)
        * Reproject_ConfigurationFiles /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_source.config /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_reproject.config
</Directory>
