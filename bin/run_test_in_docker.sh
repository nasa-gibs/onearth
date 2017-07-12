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

mkdir /build
cp -R /test /build/

(
  cd /build/test
  pip install -r requirements.txt
  python "$SCRIPT_NAME" -o /results/test_results.xml
)

chown "$DOCKER_UID:$DOCKER_GID" /results/test_results.xml
EOS
chmod +x src/test/tmp/docker-script.sh

mkdir -p src/test/results
docker run \
  --rm \
  --volume "$(pwd)/src/test:/test:ro" \
  --volume "$(pwd)/src/test/results:/results" \
  "$DOCKER_IMAGE" \
  /test/tmp/docker-script.sh

rm src/test/tmp/docker-script.sh
