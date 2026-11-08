#!/bin/sh
ENDPOINT_REFRESH=$1 # Interval for refreshing the WMS endpoints in minutes
GC_HEALTHCHECK=${2:-http://onearth-tile-services/oe-status/1.0.0/WMTSCapabilities.xml}
S3_CONFIGS=$3
SHAPEFILE_SYNC=${4:-false}
USE_LOCAL_SHAPEFILES=${5:-false}
SERVER_STATUS=${6:-false}
USE_SSL=${7:-false}
SERVER_NAME=${8:-localhost}

echo "[$(date)] Starting wms service" >> /var/log/onearth/config.log

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

mkdir -p /etc/onearth/config/mapserver/
mkdir -p /etc/onearth/config/endpoint/
mkdir -p /etc/onearth/config/layers/
mkdir -p /etc/onearth/mapfile-styles/

# Data for oe-status
mkdir -p /onearth/shapefiles/oe-status/Vector_Status/2021
cp ../oe-status/data/shapefiles/* /onearth/shapefiles/oe-status/Vector_Status/2021/
cp ../sample_configs/mapfile-styles/Vector_Status.txt /etc/onearth/mapfile-styles/

# Scrape OnEarth configs from S3
if [ -z "$S3_CONFIGS" ]
then
	echo "[$(date)] S3_CONFIGS not set for OnEarth configs, checking for local configs" >> /var/log/onearth/config.log

  # Check if configs are already mounted (local development)
  # Look for any YAML endpoint config to detect local setup
  LOCAL_CONFIGS=$(find /etc/onearth/config/endpoint/ -name "*.yaml" 2>/dev/null | head -1)
  if [ -z "$LOCAL_CONFIGS" ]; then
    echo "[$(date)] No local configs detected, using sample data" >> /var/log/onearth/config.log
    # Copy sample configs
    cp ../sample_configs/mapserver/* /etc/onearth/config/mapserver/
    cp ../sample_configs/endpoint/* /etc/onearth/config/endpoint/
    cp -R ../sample_configs/layers/* /etc/onearth/config/layers/
    cp -R ../sample_configs/mapfile-styles/* /etc/onearth/mapfile-styles/
  else
    echo "[$(date)] Local configs detected, skipping sample config copy" >> /var/log/onearth/config.log
    # Only copy conf files if they don't exist (needed for tilematrixsets.xml, etc.)
    find ../sample_configs/conf/ -name "*.xml" -exec sh -c 'test ! -f "/etc/onearth/config/conf/$(basename "$1")" && cp "$1" "/etc/onearth/config/conf/"' _ {} \; 2>/dev/null || true
    # Copy mapfile-styles if they don't exist
    find ../sample_configs/mapfile-styles/ -name "*" -exec sh -c 'test ! -f "/etc/onearth/mapfile-styles/$(basename "$1")" && cp "$1" "/etc/onearth/mapfile-styles/"' _ {} \; 2>/dev/null || true
  fi
else
	echo "[$(date)] S3_CONFIGS set for OnEarth configs, downloading from S3" >> /var/log/onearth/config.log

	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/mapserver/' -b $S3_CONFIGS -p config/mapserver >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/config/endpoint/' -b $S3_CONFIGS -p config/endpoint >>/var/log/onearth/config.log 2>&1
	python3 /usr/bin/oe_sync_s3_configs.py -f -d '/etc/onearth/mapfile-styles/' -b $S3_CONFIGS -p mapfile-styles >>/var/log/onearth/config.log 2>&1
  # layer configs are endpoint specific
  for f in $(grep -L 'reproject:' /etc/onearth/config/endpoint/*.yaml); do
    CONFIG_SOURCE=$(yq eval ".layer_config_source" $f)
    CONFIG_PREFIX=$(echo $CONFIG_SOURCE | sed 's@/etc/onearth/@@')

    mkdir -p $CONFIG_SOURCE

    python3 /usr/bin/oe_sync_s3_configs.py -f -d $CONFIG_SOURCE -b $S3_CONFIGS -p $CONFIG_PREFIX >>/var/log/onearth/config.log 2>&1
  done
fi

echo "[$(date)] OnEarth configs copy/download completed" >> /var/log/onearth/config.log

# Copy in oe-status endpoint configuration
cp ../oe-status/endpoint/oe-status_reproject.yaml /etc/onearth/config/endpoint/
mkdir -p $(yq eval ".layer_config_source" /etc/onearth/config/endpoint/oe-status_reproject.yaml)
cp ../oe-status/layers/* $(yq eval ".layer_config_source" /etc/onearth/config/endpoint/oe-status_reproject.yaml)/
mkdir -p $(yq eval ".twms_service.internal_endpoint" /etc/onearth/config/endpoint/oe-status_reproject.yaml)
cp ../oe-status/mapserver/oe-status_reproject.header /etc/onearth/config/mapserver/

# MapServer/GDAL/PROJ debug levels (production defaults; override per environment, e.g. docker run -e MS_DEBUGLEVEL=3)
MS_DEBUGLEVEL=${MS_DEBUGLEVEL:-0}
CPL_DEBUG=${CPL_DEBUG:-OFF}
PROJ_DEBUG=${PROJ_DEBUG:-OFF}
case "$MS_DEBUGLEVEL" in
  [0-5]) ;;
  *)
    echo "[$(date)] Invalid MS_DEBUGLEVEL '$MS_DEBUGLEVEL' (must be 0-5), using 0" >> /var/log/onearth/config.log
    MS_DEBUGLEVEL=0
    ;;
esac
case "$CPL_DEBUG" in
  [Oo][Nn]|[Oo][Ff][Ff]) ;;
  *)
    echo "[$(date)] Invalid CPL_DEBUG (must be ON or OFF), using OFF" >> /var/log/onearth/config.log
    CPL_DEBUG=OFF
    ;;
esac
case "$PROJ_DEBUG" in
  [Oo][Nn]|[Oo][Ff][Ff]) ;;
  *)
    echo "[$(date)] Invalid PROJ_DEBUG (must be ON or OFF), using OFF" >> /var/log/onearth/config.log
    PROJ_DEBUG=OFF
    ;;
esac
echo "[$(date)] Using MS_DEBUGLEVEL=$MS_DEBUGLEVEL CPL_DEBUG=$CPL_DEBUG PROJ_DEBUG=$PROJ_DEBUG" >> /var/log/onearth/config.log

# DEBUG and CONFIG "CPL_DEBUG"/"PROJ_DEBUG" lines in a mapfile override the environment, so apply the levels to the headers as well.
# The CONFIG lines must be present even when OFF: GDAL looks a key up in its own option table first and only falls back to
# getenv(), and getenv() in wms.cgi after the last FCGI_Accept() reads the freed FastCGI environment (SIGSEGV in
# GDALClose -> CPLDebug -> CPLGetConfigOption -> getenv at process exit). A table entry keeps CPLDebug out of getenv().
for h in /etc/onearth/config/mapserver/*.header; do
  [ -f "$h" ] || continue
  sed -i -E \
    -e "s/^([[:space:]]*)DEBUG[[:space:]]+([0-9]+|ON|OFF)[[:space:]]*$/\1Debug $MS_DEBUGLEVEL/I" \
    -e "s/^([[:space:]]*)CONFIG[[:space:]]+\"CPL_DEBUG\"[[:space:]]+\"[^\"]*\"/\1CONFIG \"CPL_DEBUG\" \"$CPL_DEBUG\"/I" \
    -e "s/^([[:space:]]*)CONFIG[[:space:]]+\"PROJ_DEBUG\"[[:space:]]+\"[^\"]*\"/\1CONFIG \"PROJ_DEBUG\" \"$PROJ_DEBUG\"/I" \
    "$h" \
    || echo "[$(date)] WARNING: could not set Debug level in $h" >> /var/log/onearth/config.log
  for key in PROJ_DEBUG CPL_DEBUG; do
    grep -qiE "^[[:space:]]*CONFIG[[:space:]]+\"$key\"" "$h" && continue
    eval "value=\$$key"
    if grep -qiE "^[[:space:]]*Debug[[:space:]]" "$h"; then
      sed -i -E "0,/^[[:space:]]*[Dd][Ee][Bb][Uu][Gg][[:space:]]/{s/^([[:space:]]*)([Dd][Ee][Bb][Uu][Gg][[:space:]].*)$/\1\2\n\1CONFIG \"$key\" \"$value\"/}" "$h"
    else
      sed -i -E "0,/^[[:space:]]*MAP[[:space:]]*$/{s/^[[:space:]]*MAP[[:space:]]*$/MAP\n  CONFIG \"$key\" \"$value\"/}" "$h"
    fi
    grep -qiE "^[[:space:]]*CONFIG[[:space:]]+\"$key\"" "$h" \
      || echo "[$(date)] WARNING: could not add CONFIG \"$key\" to $h" >> /var/log/onearth/config.log
  done
done

# mapserv.fcgi processes don't inherit the container environment
cat > /etc/httpd/conf.d/oe2_wms_debug.conf <<EOS
<IfModule fcgid_module>
    FcgidInitialEnv MS_DEBUGLEVEL $MS_DEBUGLEVEL
    FcgidInitialEnv CPL_DEBUG $CPL_DEBUG
    FcgidInitialEnv PROJ_DEBUG $PROJ_DEBUG
</IfModule>
EOS

# Copy tilematrixsets config file
mkdir -p /etc/onearth/config/conf/
cp /home/oe2/onearth/src/modules/mod_wmts_wrapper/configure_tool/tilematrixsets.xml /etc/onearth/config/conf/

# Create endpoints
cp /usr/local/bin/mapserv /var/www/cgi-bin/mapserv.fcgi

for f in $(grep -l mapserver /etc/onearth/config/endpoint/*.yaml); do
  INTERNAL_ENDPOINT=$(yq eval ".mapserver.internal_endpoint" $f)
  # WMS Endpoint
  mkdir -p $INTERNAL_ENDPOINT

  REDIRECT_ENDPOINT=$(yq eval ".mapserver.redirect_endpoint" $f)
  # Redirect Endpoint
  mkdir -p $REDIRECT_ENDPOINT

  cp /var/www/cgi-bin/mapserv.fcgi ${REDIRECT_ENDPOINT}/wms.cgi
done

time_out=600
echo "[$(date)] Begin checking $GC_HEALTHCHECK endpoint...">>/var/log/onearth/config.log 2>&1;
while [[ "$(curl -s -m 60 -o /dev/null -w ''%{http_code}'' "$GC_HEALTHCHECK")" != "200" ]]; do 
  if [[ $time_out -le 0 ]]; then
	echo "[$(date)] ERROR: Timed out waiting for endpoint">>/var/log/onearth/config.log 2>&1;
  cat /var/log/onearth/config.log; exit 1;
  else 
  	echo "[$(date)] Waiting for $GC_HEALTHCHECK endpoints...">>/var/log/onearth/config.log 2>&1;
  	sleep 60; #curl in 60 second intervals
  	time_out=$(($time_out-60));
  fi
done

echo "[$(date)] Completed healthcheck wait" >> /var/log/onearth/config.log

# Make endpoint configurations
sh load_endpoints.sh

# Set up cron job for refreshing endpoints
# Drop WMS-managed jobs from previous starts so restarts don't duplicate cron entries
crontab_base=$(mktemp)
grep -vF \
  -e '/home/oe2/onearth/docker/wms_service/' \
  -e '/etc/cron.hourly/logrotate' \
  -e '/etc/logrotate.d/mapserver' \
  -e 'find /tmp -mindepth 1 -type f -mmin +60 -delete' \
  /etc/crontab > "$crontab_base"
cat "$crontab_base" > /etc/crontab
rm -f "$crontab_base"

if [ -z "$ENDPOINT_REFRESH" ]
then
	echo "ENDPOINT_REFRESH not set...using default of 60 minutes"
	echo "*/58 * * * * /home/oe2/onearth/docker/wms_service/load_endpoints.sh" >> /etc/crontab
else
	echo "*/$ENDPOINT_REFRESH * * * * /home/oe2/onearth/docker/wms_service/load_endpoints.sh" >> /etc/crontab
fi

# Setup Apache extended server status
if [ "$SERVER_STATUS" = true ]; then
cat >> /etc/httpd/conf/httpd.conf <<EOS
LoadModule status_module modules/mod_status.so

<Location /server-status>
   SetHandler server-status
   Allow from all 
</Location>

# ExtendedStatus controls whether Apache will generate "full" status
# information (ExtendedStatus On) or just basic information (ExtendedStatus
# Off) when the "server-status" handler is called. The default is Off.
#
ExtendedStatus On
EOS
fi

# Comment out welcome.conf
sed -i -e 's/^\([^#].*\)/# \1/g' /etc/httpd/conf.d/welcome.conf

# Disable fancy indexing
sed -i -e '/^Alias \/icons\/ "\/usr\/share\/httpd\/icons\/"$/,/^<\/Directory>$/s/^/#/' /etc/httpd/conf.d/autoindex.conf

# Setup Apache with no-cache
cat >> /etc/httpd/conf/httpd.conf <<EOS

#
# Turn off caching
#
Header Set Pragma "no-cache"
Header Set Expires "Thu, 1 Jan 1970 00:00:00 GMT"
Header Set Cache-Control "max-age=0, no-store, no-cache, must-revalidate"
Header Unset ETag
FileETag None
EOS

# Build wms_time service endpoints in parallel
grep -l 'mapserver:' /etc/onearth/config/endpoint/*.yaml | parallel -j 4 lua /home/oe2/onearth/src/modules/wms_time_service/make_wms_time_endpoint.lua >>/var/log/onearth/config.log 2>&1

if [ "$USE_SSL" = true ]; then
  cp /home/oe2/onearth/certs/* /etc/pki/tls/private/
  sed -i -e 's/SSLPassPhraseDialog/#SSLPassPhraseDialog/g' /etc/httpd/conf.d/ssl.conf
  sed -i -e 's/ServerName localhost/ServerName '"$SERVER_NAME"'/g' /etc/httpd/conf.d/oe2_ssl.conf
else
  rm -f /etc/httpd/conf.d/oe2_ssl.conf
fi

# Remove stale mod_fcgid sockets left over from a previous run
rm -f /etc/httpd/run/fcgidsock/*

# Stale mod_fcgid socket sweep: /usr/local/bin/oe2_fcgid_sock_sweep.sh (docker/wms_service/, copied in by the Dockerfile;
# /usr/local/bin is root-owned and this script runs as www-data), scheduled in the crontab below.

# wms.cgi exits with SIGSEGV when GDAL teardown touches the freed FastCGI environment
# each core is 200-800 MB and a systemd-coredump run on the host, so cores are disabled for httpd and its children
# (soft and hard limit) unless CORE_DUMPS=ON is set for debugging. The kernel still invokes a piped core_pattern
# handler with RLIMIT_CORE=0, but it passes the limit as %c and systemd-coredump exits on a limit below one page
# before reading the pipe ("Resource limits disable core dumping"), the same path as ProcessSizeMax=0.
case "$CORE_DUMPS" in
  [Oo][Nn]) echo "[$(date)] CORE_DUMPS=ON, core dumps left enabled" >> /var/log/onearth/config.log ;;
  *) ulimit -c 0 || echo "[$(date)] WARNING: could not disable core dumps" >> /var/log/onearth/config.log ;;
esac
echo "[$(date)] Restarting Apache server" >> /var/log/onearth/config.log
/usr/sbin/httpd -k start
sleep 2

# Run logrotate hourly
echo "0 * * * * /etc/cron.hourly/logrotate" >> /etc/crontab

# Check the MapServer error log against maxsize between the hourly logrotate runs
echo "5-55/10 * * * * /usr/sbin/logrotate -s /var/lib/logrotate/logrotate.status /etc/logrotate.d/mapserver" >> /etc/crontab

# Clean up temp files older than 60 minutes
echo "*/30 * * * * find /tmp -mindepth 1 -type f -mmin +60 -delete" >> /etc/crontab

# Remove mod_fcgid sockets no process has bound any more
echo "*/10 * * * * /usr/local/bin/oe2_fcgid_sock_sweep.sh" >> /etc/crontab

# Start cron
supercronic -debug /etc/crontab >> /var/log/cron_jobs.log 2>&1 &

# Tail the logs
exec tail -qFn 1000 \
  /var/log/cron_jobs.log \
  /var/log/onearth/config.log \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log
