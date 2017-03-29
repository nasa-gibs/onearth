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

##Configuration

mod_reproject_wrapper has two directives, each to be placed in a `<Directory>` block in your Apache config.

### WMTSWrapperRole String
This indicates what "role" a particular directory plays in your WMTS REST request. Roles are:

- root
- layer
- style
- tilematrixset

###WMTSWrapperEnableTime (On|Off)
Indicates whether or not mod_wmts_wrapper should handled TIME REST and KvP requests. Should be placed in the same `<Directory>` block as `WMTSWrapperRole layer`.

### Example config:

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
        Reproject_RegExp GoogleMapsCompatible_Level7/\d{1,2}/\d{1,3}/\d{1,3}.(png|jpeg|jpg)
        Reproject_ConfigurationFiles /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_source.config /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_reproject.config
</Directory>
