#!/bin/sh
. /version.sh
printenv | grep ONEARTH
echo "in the entrypoint, onearth version is ONEARTH_VERSION=${ONEARTH_VERSION} and use_SSL is ${USE_SSL}"
exec "$@"