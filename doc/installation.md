# Installation

.
## Preconditions

Install Apache

## RPM Installation

Download latest OnEarth release (https://github.com/nasa-gibs/onearth/releases)
Unpackage release .tar.gz file
`yum install gibs-gdal-*`
`yum install onearth-*`


## Endpoint Creation

```bash
mkdir –p  /srv/www/gibs/wmts
cp -r /usr/share/onearth/apache/ /srv/www/gibs/wmts
```
Create imagery archive directory (I.e. /archive/imagery/)
Create /etc/httpd/conf.d/onearth.conf file with following contents

```bash
LoadModule wms_module modules/mod_wms.so
LoadModule twms_module modules/mod_twms.so

<Directory "/srv/www/gibs/wmts">
    OptionsIndexes FollowSymLinks+ExecCGI
    AddHandler cgi-script .cgi
    AllowOverrideNone
    Order allow,deny
    Allow from all
    WMSCache        /archive/imagery/cache_wmts.config

    Header set Access-Control-Allow-Origin *

    RewriteEngineOn
    RewriteBase /wmts/

    # rewrite .jpg -> .jpeg
    RewriteRule ^(.+)\.jpg$ $1.jpeg

    # RESTful with date
    RewriteRule ^([\w\d\._-]+)/[\w\d\._-]+/([-\d]+)/([\w\d\._-]+)/(\d+)/(\d+)/(\d+)\.(\w+)$ wmts.cgi?TIME=$2&SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=$1&STYLE=&TILEMATRIXSET=$3&TILEMATRIX=$4&TILEROW=$5&TILECOL=$6&FORMAT=image\%2F$7 [NE,L]

    # RESTful no date
    RewriteRule ^([\w\d\._-]+)/[\w\d\._-]+/([\w\d\._-]+)/(\d+)/(\d+)/(\d+)\.(\w+)$ wmts.cgi?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=$1&STYLE=&TILEMATRIXSET=$2&TILEMATRIX=$3&TILEROW=$4&TILECOL=$5&FORMAT=image\%2F$6 [NE,L]

</Directory>
```

Start/Restart Apache
