## OnEarth Demo

This package includes a pair of pre-configured endpoints for OnEarth that feature the Blue Marble imagery layer.

By default, the package is installed to ``/usr/share/onearth/demo``

The ``examples/`` directory contains demos with more advanced features. For each demo, execute `configure_demo.sh` as a privileged user to install. Installations may take a long time to configure imagery.

Example:

``sudo /usr/share/onearth/demo/examples/default/configure_demo.sh``

The `default` example must first be configured before installing other examples.

### WMTS endpoint
A WMTS endpoint is included with an OpenLayers demo. It's located at:

``<server_url>/onearth/wmts/epsg4326``

The endpoint CGI itself is located at:

``<server_url>/onearth/wmts/epsg4326/wmts.cgi``

### TWMS/KML
A TWMS endpoint with the KML cgi script is also configured. It allows for the testing of TWMS with a KML client such as Google Earth. It's located at:

``<server_url>/onearth/twms/epsg4326/kmlgen.cgi``

To access the demo Blue Marble imagery provided, use the URL:

``<server_url>/onearth/twms/epsg4326/kmlgen.cgi?layers=blue_marble&time=2015-01-01``

The KML file that the script will produce can then be used with your chosen client.

### WMS
A WMS endpoint that uses MapServer is available.

``<server_url>/onearth/wms``

The demo utilizes a link to mapserv via wms.cgi:

``<server_url>/onearth/wms/epsg4326/wms.cgi``

### WFS
A WFS endpoint that uses MapServer is available.

``<server_url>/onearth/wms``

The demo utilizes a link to mapserv via wfs.cgi:

``<server_url>/onearth/wms/epsg4326/wfs.cgi``

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
