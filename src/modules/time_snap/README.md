# OnEarth Time Snap Service

## What it does

This is a service that allows for the querying of time period and default date
information per layer, as well as date snapping.

As part of OnEarth 2.0, it's used by `mod_wmts_wrapper` to complete layer
requests that involve a time dimension.

The service takes queries via URL query parameters and returns a JSON response.

## How it works

`time_snap` is a Lua script that's intended to be run by the `mod_ahtse_lua`
Apache module.

`time_snap` currently uses a Redis database for queries, but other handlers can
be easily added.

## Dependencies

* Apache 2.4
* `mod_ahtse_lua`
* Lua 5.1 or greater
* luarocks (Lua package system)
* Redis

#### Lua dependencies

* luaposix
* redis-lua (forked in this repo)
* json-lua

## Installation

1. Make sure `mod_ahtse_lua` is installed and is being loaded by your Apache
   configuration.

2. Install Redis. For CentOS 7, use `yum install redis`. Make sure the database
   is running.

3. Install `luarocks`. For CentOS 7, use `yum install luarocks`.

4. Within the `onearth` repo, navigate to `src/modules/time_snap`

5. Install the OnEarth Lua package with `luarocks` (you will probably need to
   use `sudo`):

```
luarocks make
```

6. Install the Lua Redis handler library:

```
cd redis-lua
luarocks make rockspec/redis-lua-2.0.5-0.rockspec
```

## Configuration

### Set up the Redis database with layer information

`time_snap` is set to read values from a Redis database in the following format,
for each layer configured:

`layer:[layer_name]:default` -- A string with the current default date for the
layer specified by `[layer_name]`. Should be in either `YYYY-MM-DD` or
`YYYY-MM-DDTHH:MM:SS` format.

`layer:[layer_name]:periods` -- A set of strings in the following format:
`start_date/end_date/P[interval_number][interval_size]`. For example,
`2012-01-01/2016-01-01/P1Y`.

##### Example

For testing, here's a fast way to set up a Redis database for testing.

1. Enter the Redis CLI: `redis-cli`
2. Add a default date: `SET layer:test_layer:default "2015-06-01`
3. Add some periods: `SADD layer:test_layer:periods "2012-01-01/2013-01-01/P1M"
   "2005-06-01/2005-12-01/P10D"`

### Create the Lua configuration script

To start, you'll need to create a simple Lua configuration script that
determines how your service will run. Here's a sample script:

```
-- Set configuration here
local databaseHandler = {type="redis", ip="127.0.0.1"}
local filenameFormatHandler = {type="strftime", dateFormat="%Y%j", dateTimeFormat="%Y%j"}
-- End configuration

local onearth = require "onearth"
handler = onearth.dateSnapper(databaseHandler, filenameFormatHandler)
```

The only lines you need to edit are the two after `Set configuration here`.

#### Database Handlers

_Redis_

* type -- set to `"redis"`.
* host -- sets the hostname for the Redis database you'll be using. Should be in
  quotes.
* port (optional) -- sets the port number for your Redis database. Defaults to
  6379.

#### Filename Format Handlers

_strftime_ Outputs filenames in this format: `[layer_name][date]`, where
`[date]` is the date formatted using a strftime-compatible template. For more
information, see (http://man7.org/linux/man-pages/man3/strftime.3.html)

* type -- set to `"strftime"`
* dateFormat -- the strftime-compatible format for non-subdaily dates.
* dateTimeFormat -- the strftime-compatible format for subdaily dates.

_epoch_ Outputs filenames in this format: `[layer_name][unix_epoch]`, where
`[unix_epoch]` is the date UNIX epoch time (ms).

### Create the Apache configuration

In your Apache configuration, you need to set up an endpoint that the service
will run under. This can exist under a `<Directory>` or `<Location>` block.

You'll need to make sure the following directives are in place (for more
information, consult the `mod_ahtse_lua` documentation):

`AHTSE_lua_RegExp` -- Any request that matches this regex expression will be
handled by `time_snap`. `AHTSE_lua_Script` -- This needs to be a path to the Lua
configuration script described previously.
