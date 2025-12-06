#!/bin/sh

set -evx

if [ "test_gc_service.py" = "test_mapserver.py" ]; then
  sh start_ci2.sh
else
  mkdir /build
fi

# Rebuild gc_service 
(
  cd /home/oe2/onearth/src/modules/gc_service
  luarocks make onearth_gc_gts-0.1-1.rockspec
  httpd -k restart
)

cp -R /test /build/

(
  cd /build/test
  python3 "test_gc_service.py" -o /results/"test_gc_service.py""_test_results.xml"
)

chown "503:20" /results/"test_gc_service.py""_test_results.xml"
