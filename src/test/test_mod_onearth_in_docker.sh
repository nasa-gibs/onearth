#!/bin/sh

set -evx

DOCKER_IMAGE="$1"

if [ -z "$DOCKER_IMAGE" ] ]; then
  echo "Usage: test_mod_onearth_in_docker.sh DOCKER_IMAGE" >&2
  exit 1
fi

dirname=$(basename "$(pwd)")
if [ "$dirname" != "test" ]; then
  echo "This script is intended to be run from the src/test directory." >&2
  exit 1
fi

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)

mkdir -p tmp
cat > tmp/docker-script.sh <<EOS
#!/bin/sh

set -evx

mkdir /build
cp -R /test /build/

(
  cd /build/test
  pip install -r requirements.txt
  python test_mod_onearth.py -o /results/test_results.xml
)

chown "$DOCKER_UID:$DOCKER_GID" /results/test_results.xml
EOS
chmod +x tmp/docker-script.sh

mkdir -p results
docker run \
  --rm \
  --volume "$(pwd):/test:ro" \
  --volume "$(pwd)/results:/results" \
  "$DOCKER_IMAGE" \
  /test/tmp/docker-script.sh

rm tmp/docker-script.sh
