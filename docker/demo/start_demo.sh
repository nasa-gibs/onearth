#!/bin/sh
DEBUG_LOGGING=${1:-false}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Set Apache logs to debug log level
if [ "$DEBUG_LOGGING" = true ]; then
    perl -pi -e 's/LogLevel warn/LogLevel debug/g' /etc/httpd/conf/httpd.conf
fi
perl -pi -e 's/LogFormat "%h %l %u %t \\"%r\\" %>s %b/LogFormat "%h %l %u %t \\"%r\\" %>s %b %D/g' /etc/httpd/conf/httpd.conf

# Comment out welcome.conf
sed -i -e 's/^\([^#].*\)/# \1/g' /etc/httpd/conf.d/welcome.conf

# Disable fancy indexing
sed -i -e '/^Alias \/icons\/ "\/usr\/share\/httpd\/icons\/"$/,/^<\/Directory>$/s/^/#/' /etc/httpd/conf.d/autoindex.conf

# Check if we should generate dynamic demo page or use static one
CONFIG_DIR="/etc/onearth/config"
if [ -d "$CONFIG_DIR" ]; then
    echo "Config directory found, generating dynamic demo page..."
    /var/www/html/demo/generate_demo_page.sh
else
    echo "Config directory not mounted at $CONFIG_DIR, using static demo page"
fi

echo 'Starting Apache server'
/usr/sbin/httpd -k start
sleep 2

# Tail the apache logs
exec tail -qFn 10000 \
  /etc/httpd/logs/access_log \
  /etc/httpd/logs/error_log