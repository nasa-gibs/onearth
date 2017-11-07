# mod_sfim
An apache httpd module that sends back a static file for web requests that match a regexp.
Adds one directive to the apache configuration file.  

** SendFileIfMatch file_name regexp mime-type

The file_name file will be sent as a response, with mime-type as the type, if the request matches the regexp.
JSON-P is supported if the type is application/jsonp, in which case the response type will be application/json
If parameters are present in the request, the regexp will also take them into consideration
There can be multiple such directives in a given Location or Directory container
