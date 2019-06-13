#!/bin/sh
ONEARTH_HOST=${1:-localhost:8080}
ONEARTH_GROUP_NAME=${2:-onearth}

if [ ! -f /.dockerenv ]; then
  echo "This script is only intended to be run from within Docker" >&2
  exit 1
fi

# Performance test suite
python3.6 oe_profiler.py -t test0 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100
sleep 5

python3.6 oe_profiler.py -t test1 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100
sleep 5

python3.6 oe_profiler.py -t test2 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100
sleep 5

python3.6 oe_profiler.py -t test3 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100
sleep 5

python3.6 oe_profiler.py -t test4 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 1
sleep 5

python3.6 oe_profiler.py -t test5 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100
sleep 5

python3.6 oe_profiler.py -t test6 -s $ONEARTH_HOST -g $ONEARTH_GROUP_NAME -r 100000 -c 100 -u 100