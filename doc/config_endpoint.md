# OnEarth Endpoint Configuration

These steps demonstrate how to create a new endpoint on the file system.  Repeat each section for multiple endpoints.

## WMTS

1) Create the endpoint directory and copy files

```Shell
mkdir -p /usr/share/onearth/demo/wmts-geo

cp -p /usr/share/onearth/apache/wmts.cgi /usr/share/onearth/demo/wmts-geo
cp -p /usr/share/onearth/apache/index.html /usr/share/onearth/demo/wmts-geo
```

2) Check permissions


## Tiled-WMS

1) Create the endpoint directory and copy files

```Shell
mkdir -p /usr/share/onearth/demo/twms-geo
cp -r /usr/share/onearth/apache/ /usr/share/onearth/demo/twms-geo
```

2) Check permissions

## KML

To create the KML endpoint, you'll need to compile the KML CGI script and specify the location of the KML endpoint.

This step requires cgicc to be installed: [http://www.gnu.org/software/cgicc]( http://www.gnu.org/software/cgicc/ ).

1) Compile the script. The WEB_HOST option must be set to the location of the KML endpoint. Default is 'localhost/twms'.

```
cd /usr/share/onearth/demo/twms-geo/kml/
make WEB_HOST=<host>:<port>/kml_endpoint
```

2) Copy the binary CGI script to the endpoint directory.

`mv kmlgen.cgi ../` 

## Empty Tiles

The WMTS and TWMS CGI scripts will "fall through" to an empty tile image in the event that an invalid request is received.  To support the following files should exist in the endpoint directory:
* black.jpg
* transparent.png

OnEarth installs the following files in the /usr/share/onearth/empty_tiles/ directory for you to choose from. Custom empty tiles may be created if none of the provided ones are suitable. 
* Blank_RGB_512.jpg - A 512x512 pixel black JPEG.
* Blank_RGB_256.jpg - A 256x256 pixel black JPEG.
* Blank_RGBA_512.jpg - A 512x512 pixel transparent (0,0,0,0) PNG.
* Blank_RGBA_256.jpg - A 256x256 pixel transparent (0,0,0,0) PNG.

To complete configuration of the a WMTS endpoint, you would copy or link these empty tiles as shown below:
```
cp -p /usr/share/onearth/empty_tiles/Blank_RGB_512.jpg /usr/share/onearth/demo/wmts-geo/black.jpg
cp -p /usr/share/onearth/empty_tiles/Blank_RGBA_512.png /usr/share/onearth/demo/wmts-geo/transparent.png

- or -

ln -s /usr/share/onearth/empty_tiles/Blank_RGB_512.jpg /usr/share/onearth/demo/wmts-geo/black.jpg
cp -p /usr/share/onearth/empty_tiles/Blank_RGBA_512.png /usr/share/onearth/demo/wmts-geo/transparent.png
```
