export DOCKER_PLATFORM_OPTION=$(uname -m | grep -qE 'aarch64|arm64' && echo "linux/amd64" || echo "")
export USE_SSL=false # Change this back to true later as default, just for testing since dont have process to create certs folder 
export SERVER_NAME=localhost
export BUILD_TOOLS_IMAGE=false
export ONEARTH_DEPS_TAG=nasagibs/onearth-deps:${ONEARTH_VERSION}