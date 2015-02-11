# OnEarth Endpoint Configuration

These steps demonstrate how to create a new endpoint on the file system.  Repeat each section for multiple endpoints.

## WMTS

1) Create the endpoint directory and copy files

```Shell
mkdir -p /usr/share/onearth/demo/wmts-geo

cp -p /usr/share/onearth/apache/wmts.cgi /usr/share/onearth/demo/wmts-geo
cp -p /usr/share/onearth/apache/black.jpg /usr/share/onearth/demo/wmts-geo
cp -p /usr/share/onearth/apache/transparent.png /usr/share/onearth/demo/wmts-geo
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

The serving of KML files via kmlgen.cgi requires cgicc ( http://www.gnu.org/software/cgicc/ ).

1) Change WEB_HOST inside Makefile. The sub-directory (e.g., "/twms-geo") is also needed.

```Shell
cd /usr/share/onearth/demo/twms-geo/kml/
vi Makefile

WEB_HOST='"<host>:<port>/twms-geo"'
```

2) Run the make process, which will create a binary CGI script. Then move the CGI file to the endpoint directory.

```Shell
make
mv kmlgen.cgi ../
```

