# mod_wmts_wrapper

This module is designed as a wrapper around Apache modules like mod_redirect
that only serve tiles via REST requests.

Right now it only works with mod_reproject.

## What it does

mod_wmts_wrapper does a few things:

* Converts KvP WMTS requests into REST, returning errors if necessary.
* Returns WMTS errors for problems with REST WMTS requests (i.e., non-existent
  layer)
* Integrates with mod_reproject so that it can handle layers that have a TIME
  parameter.
* Adds additional error handling to mod_reproject (i.e., tile out of bounds)

## Build/Install

### Dependencies

* [mod_reproject](../mod_reproject)
* [mod_mrf](../mod_mrf)
* [mod_receive](../mod_receive)
* [Jansson](http://www.digip.org/jansson/)

For the Apache modules, edit the `Makefile.lcl` file in the `src` directory and
run `make install`

Jansson can be installed in CentOS 7 with `yum install jansson-devel`

## Time/Date Handling

mod_wmts_wrapper can rewrite mod_reproject and mod_mrf configrations on the fly
so that mod_reproject uses the correct URL for a requested date.

In order to use this, you need to modify the string used in the reproject
configuration file specified by the `Reproject_ConfigurationFiles`, `IndexFile`,
`DataFile`, and `Redirect` directives.

#### mod_reproject

You will have a line like this in your Apache config:

`Reproject_ConfigurationFiles source.config reproj.config`

in the `reproj.config` file you'll need to have a line like this:

`SourcePath /endpoint/layer/style/${date}/tilematrixset/`

mod_wmts_wrapper will then use the date from the current request to fill in the
${date} field in the source URL that mod_reproject uses.

#### mod_mrf

You will have a line like this in your Apache config:

`MRF_ConfigurationFile mrf.config`

in the `mrf.config` file you'll need a line like this:

`IndexFile /endpoint/layer/style/tilematrixset/${filename}.idx`

and either this:

`DataFile /endpoint/layer/style/tilematrixset/${filename}.pjg`

or this:

`Redirect /outside/${filename}.pjg`

## Configuration

mod_reproject_wrapper has four directives, each to be placed in a `<Directory>`
block in your Apache config.

### WMTSWrapperRole String

This indicates what "role" a particular directory plays in your WMTS REST
request. Roles are:

* root
* layer
* style
* tilematrixset

This configuration allows the module to correctly handle errors.

### WMTSWrapperEnableTime (On|Off)

Indicates whether or not mod_wmts_wrapper should handled TIME REST and KvP
requests. Should be placed in the same `<Directory>` block as `WMTSWrapperRole
layer`.

### WMTSWrapperMimeType String

Set the MIME type for the tiles to be served by this endpoint.

### WMTSWrapperTimeLookupUri String

Set the URI of the time lookup service mod_wmts_wrapper should use for layers
that involve a TIME dimension (see [time_service](../time_service/README.md)).

### WMTSWrapperEnableYearDir (On|Off)

If turned on, the wrapper module will look for a year substitution string in the
path to the IDX file. Use ${YYYY} where the year should be inserted into the IDX
path.

Example: `IndexFile
/var/www/html/mrf_endpoint/date_test_year_dir/default/tms/${YYYY}/${filename}.idx`

### WMTSWrapperDateServiceKeys (String, can be multiple)

The OnEarth date service can accept additional keys (can be used to separate
layers by projection or endpoint).

Keys listed here will be appended to the date service request in order.

So, if configured like this:

```
WMTSWrapperDateServiceKeys geographic best
```

The date service query will add the following parameters to the date service
request for each tile request:

```
/date-service?layer=layer&key1=geographic&key2=best
```

Note that this configuration option works per layer.

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
        WMTSWrapperMimeType "image/png"
        WMTSWrapperTimeLookupUri "/time_lookup"
        Reproject_RegExp GoogleMapsCompatible_Level7/\d{1,2}/\d{1,3}/\d{1,3}.(png|jpeg|jpg)
        Reproject_ConfigurationFiles /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_source.config /usr/share/onearth/demo/wmts-webmerc/blue_marble/default/GoogleMapsCompatible_Level7/blue_marble_reproject.config
        WMTSWrapperDateServiceKeys geographic best
</Directory>
```
