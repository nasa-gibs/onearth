# Set up a web site, run a few tests
# This would be a lot simpler in python, but let's stick to bash

# Use the GIBS server for data
GIBS_URL="https://gibs.earthdata.nasa.gov/twms/epsg4326/best/twms.cgi"

# A place for AHTSE content
AFOLDER=$PREFIX/ahtse
mkdir $AFOLDER
pushd $AFOLDER

# Get the twms hook for Blue Marble Bathymetry, an RGB global dataset, JPEG
if [ ! -e BMB.twms ]
then
rm -f BMB.*
gdalinfo ${GIBS_URL}\?request=GetTileService -oo TiledGroupName="BlueMarble" |grep "Bathymetry" |grep NAME |cut -d= -f2- >BMB.twms
# Build a small MRF, brunsli JPEG
gdal_translate -q -of MRF -co COMPRESS=JPEG -co BLOCKSIZE=512 -outsize 8192 4096 BMB.twms BMB.mrf
# Build overviews
gdaladdo -q BMB.mrf 2 4 8 16
fi

cat >BMB_mrf.webconf <<END_LABEL
ETagSeed 9361hsmv7348s
Size 8192 4096 1 3
PageSize 512 512 1 3
SkippedLevels 1
DataFile /data/BMB.pjg
IndexFile /data/BMB.idx
END_LABEL

touch ahtse.conf

# This increases server vulnerability somewhat
cat >>ahtse.conf <<END_LABEL
<Location /server-info>
  SetHandler server-info
</Location>
<Location /server-status>
  SetHandler server-status
</Location>

END_LABEL


grep -q /MRF\> ahtse.conf || {
cat >>ahtse.conf <<END_LABEL
<Location /MRF>
  MRF_RegExp ^/MRF/tile/([1-9]\d*|0)/([1-9]\d*|0)/([1-9]\d*|0)
  MRF_ConfigurationFile /data/BMB_mrf.webconf
  SetOutputFilter DBRUNSLI
</Location>

END_LABEL
}

cat >>00-mpm.conf <<END_LABEL
LoadModule mpm_event_module modules/mod_mpm_event.so
END_LABEL
sudo cp 00-mpm.conf /etc/httpd/conf.modules.d/
sudo cp ahtse.conf /etc/httpd/conf.d/

popd
sudo rm -rf /data
sudo mv ahtse /data
chown -r apache /data

# Deploy needed binaries
sudo cp $PREFIX/lib/libbrunsli{enc,dec}-c.so /usr/lib64
sudo rm -f /etc/httpd/conf.d/{welcome,autoindex,userdir}.conf

sudo service httpd restart
