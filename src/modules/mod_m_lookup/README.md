# mod_m_lookup

Uses a Lua script to translate an m-dimension into its associated z-index within an MRF.

Use in `<Directory>` block of Apache config.

### Dependencies:
* Lua
* Jansson


### Directives:

* **MLookupScript** -- location of Lua script to be run for each request
* **MLookupEndpoint** -- redirect endpoint for requests
* **MLookupRegexp** -- determine which requests will be handled by module
* **MLookupServiceRegexp** -- determine which requests will prompt a text reply instead of a redirect (for using as a service).