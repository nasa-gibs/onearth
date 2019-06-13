## OnEarth Profiler

Profiling tools for OnEarth.


## oe_profiler.py

Runs an OnEarth profiling test. Each test should have a directory (e.g. test0)
that contains a YAML configuration file like the following:

```
description: "Single 250m JPEG MRF with TIME"
base_url: "http://$ONEARTH_HOST/profiler/VNGCR_LQD_I1-M4-M3_NRT"
period: "2018-01-16T00:00:00/2018-02-14T00:00:00/P1D"
tilematrixset: "250m"
```

$ONEARTH_HOST is a keyword that will be replaced by the --server option.
Include a "list_urls" in the test directory if you want to use a predefined list of URLS.
A run_test.sh template needs to be included for now, but will be replaced later. 

```
usage: oe_profiler.py [-h] [-t TEST_DIR] [-s SERVER] [-g GROUP]
                      [-r NUMBER_REQUESTS] [-c NUMBER_USERS] [-u NUMBER_URLS]
                      [-a]

Runs an OnEarth profiling test.

optional arguments:
  -h, --help            show this help message and exit
  -t TEST_DIR, --test_dir TEST_DIR
                        Test directory with configurations
  -s SERVER, --server SERVER
                        OnEarth host server used for testing
  -g GROUP, --group_name GROUP
                        The log group name
  -r NUMBER_REQUESTS, --number_requests NUMBER_REQUESTS
                        Total number of requests
  -c NUMBER_USERS, --number_users NUMBER_USERS
                        Total number of concurrent users (max 100)
  -u NUMBER_URLS, --number_urls NUMBER_URLS
                        Total number of random l/r/c URLs (ignored if
                        list_urls file is found)
  -a, --analysis_only   Just analyze results; do not send requests
```

