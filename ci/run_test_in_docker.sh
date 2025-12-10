#!/bin/sh

set -evx

DOCKER_IMAGE="$1"
SCRIPT_NAME="$2"

if [ -z "$DOCKER_IMAGE" ] || [ -z "$SCRIPT_NAME" ]; then
  echo "Usage: run_test_in_docker.sh DOCKER_IMAGE SCRIPT_NAME" >&2
  exit 1
fi

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

mkdir -p src/test/tmp
cat > src/test/tmp/docker-script.sh <<EOS
#!/bin/sh

set -evx

if [ "$2" = "test_mapserver.py" ]; then
  sh start_ci2.sh
else
  mkdir /build
fi

cp -R /test /build/

(
  cd /build/test
  python3 "$SCRIPT_NAME" -o /results/"$SCRIPT_NAME""_test_results.xml"
)

chown "$DOCKER_UID:$DOCKER_GID" /results/"$SCRIPT_NAME""_test_results.xml"
EOS
chmod +x src/test/tmp/docker-script.sh

mkdir -p src/test/results
docker run \
  --rm \
  -e ONEARTH_VERSION=test \
  --volume "$(pwd)/src/test:/test:ro" \
  --volume "$(pwd)/src/test/results:/results" \
  "$DOCKER_IMAGE" \
  /test/tmp/docker-script.sh

rm src/test/tmp/docker-script.sh
exit 0
