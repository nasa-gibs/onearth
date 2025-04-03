source version.sh

export DOCKER_PLATFORM_OPTION=$(uname -m | grep -qE 'aarch64|arm64' && echo "linux/amd64" || echo "")
export USE_SSL=true 
export SERVER_NAME=localhost
export ONEARTH_DEPS_TAG=nasagibs/onearth-deps:${ONEARTH_VERSION}