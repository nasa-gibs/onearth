# OnEarth 2 Varnish Cache

This container is used to set up [Varnish Cache](https://varnish-cache.org/) in front of OnEarth for improved response times.

## [default.vcl](default.vcl)

This configures the Varnish cache behavior for OnEarth. By default, GetCapabilities requests will be cached for 1 hour, while other requests will be cached for 5 minutes.
