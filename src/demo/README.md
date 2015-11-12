## OnEarth Demo

This package includes a pair of pre-configured endpoints for OnEarth that feature the Blue Marble imagery layer.

### WMTS endpoint
A WMTS endpoint is included with an OpenLayers demo. It's located at:

```<server_url>/onearth/demo```

The endpoint CGI itself is located at:

```<server_url>/onearth/demo/wmts.cgi```

### TWMS/KML
A TWMS endpoint with the KML cgi script is also configured. It allows for the testing of TWMS with a KML client such as Google Earth. It's located at:

```<server_url>/onearth/demo-twms/kmlgen.cgi```

To access the demo Blue Marble imagery provided, use the URL:

```<server_url>/onearth/demo-twms/kmlgen.cgi?layers=blue_marble&time=2015-01-01```

The KML file that the script will produce can then be used with your chosen client.

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
