# mod_ahtse_lua

Apache httpd content generator using Lua

A module using a Lua script file to respond to a get request.  Similar to the CGI mechanism, somewhat customized for AHTSE use.
The lua script file should define a handler function that takes three arguments and returns three values.

#Since it involves executing a script, the use of this module may increase server vulnerability#

### Inputs
* URL parameter string, or nil if there are no parameters
* A table of input headers
* A table of notes.  The *HTTPS* key is set if the matching apache environment variable is also set

### Outputs
* Content
* A table of output headers
* The http status code

The *Content-Type* header is properly handled, others might not work as expected

## Apache Directives

* AHTSE_lua_RegExp _regexp_
  Regular expressions that have to match the request URL to activate the module.  May appear more than once.

* AHTSE_lua_Script _script_ _function_
  The lua script to run and what function to call.  The script can be lua source or precompiled lua bytecode.  The default function name is _handler_

* AHTSE_lua_Redirect On
  When the lua script returns a redirect status code and a Location header, issue an internal redirect to that location.  Default is to use the response as is.
  Recognized redirect codes are 301, 302, 307 and 308.

## Lua

 * sample_script.lua
   An example server side lua script, returns the query string wrapped in JSON

 * harness.lua
   Allows for execution of a mod_ahtse_lua script directly from lua, for development and debugging
