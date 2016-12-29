# mod_m_lookup

Uses a Lua script to translate an m-dimension into its associated z-index within an MRF.

Can either rewrite the request, replacing the M-dimension with the MRF z-level, or return a JSON response with the requested z-level (or error message).

Use in `<Directory>` block of Apache config.

### Dependencies:
* Lua (currently uses LuaJIT. For normal Lua, change [these lines](https://github.com/nasa-gibs/onearth/blob/2.0.0/src/modules/mod_m_lookup/mod_m_lookup.c#L10-L12))
* Jansson (for producing JSON response in service mode)


### Directives:

* **MLookupScript** -- location of Lua script to be run for each request
* **MLookupEndpoint** -- redirect endpoint for requests
* **MLookupRegexp** -- determine which requests will be handled by module
* **MLookupServiceRegexp** -- determine which requests will prompt a text reply instead of a redirect (for using as a service).