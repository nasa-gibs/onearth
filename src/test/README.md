
# OnEarth CI Test Scripts

This directory contains files and scripts to test various aspects of OnEarth. The included tests are:

* `test_gc_service.py` -- tests the OnEarth GetCapabilities Service
* `test_legends.py` -- tests the oe_generate_legend tool with GIBS colormaps
* `test_mapserver.py` -- tests wms requests via mapserver  
* `test_mod_mrf.py` -- tests the mod_mrf module
* `test_mod_reproject.py` -- tests the mod_reproject module
* `test_mod_twms.py` -- tests the mod_twms module
* `test_mod_wmts_wrapper.py` -- tests the mod_wmts_wrapper module
* `test_mrfgen.py` -- tests mrfgen
* `test_sync_s3.py` -- tests `oe_sync_s3_configs.py` and `oe_sync_s3_idx.py`
* `test_time_service.py` -- tests the OnEarth Time Service
* `test_time_utils.py` -- tests time configuration utilities
* `test_vectorgen.py` -- tests vectorgen

## Running tests in Docker

There is a script called [run_test_in_docker.sh](../../ci/run_test_in_docker.sh) that will run a test script
inside of a Docker container.  It takes two parameters, the name of the onearth
Docker image to run the test in, and the name of the test script.  After
running, the results will be written to a file in the `src/test/results`
directory.

Example:
```
./ci/run_test_in_docker.sh nasagibs/onearth-test:latest test_mod_mrf.py
```

Refer [here](../../ci/README.md) for information on building the docker image used for testing.

## Setup
These tests assume that OnEarth and its associated utilities are installed. **Test files for mod_* tests must be copied to a directory that Apache has permission to access.**

The tests have additional dependencies from the rest of OnEarth. To install the Python dependencies required by the test scripts, run `sudo pip3 install -r requirements.txt`.

## Running the Tests
Each test script will output a JUnit XML results file. By default, these files are named `*_results.xml`. A different output filename can be specified with the `-o` option, i.e. `python3 test_mod_mrf.py -o output_file.xml`.

**Note also that the mrfgen tests involve the downloading and processing of imagery, so they may take a while to complete. You may experience 'out of memory' errors if running these tests in a VM without enough memory configured.**


--------
## Time Service Tests
1. Tests that a request to timeservice without parameters will return all records
2. Test time snap for P1Y layer (year)
3. Test time snap for P7D layer (week)
4. Test time snap for P1M layer (month)
5. Test time snap for PT2H layer (hour)
6. Test time snap for PT6M layer (minute)
7. Test time snap for PT6M layer (second)
8. Test invalid layer error
9. Test invalid date error 
10. Test out of range error for periods
11. Test snap with single key parameter (key1)
12. Test best layer to check filename, prefix, date
13. Test snap with multiple key parameter (key1, key2, key3, etc)
14. Test snapping to one of multiple periods


## Time Utilities Tests
***There are currently two sets of tests endpoint agonostic and endpoint specific, endpoint specific are marked with _dep(deprecated) at the end. ***
1. Time scrape S3 keys
2. Time scrape S3 inventory
3. Test period generation with single date
4. Test period generation with subdaily
5. Test period generation with multiday
6. Test period generation with monthly
7. Test period generation config DETECT everything
8. Test period generation config DETECT/DETECT (start/end)
9. Test period generation config DETECT/DETECT/P5D (start/end/forced-period)
10. Test period generation config DETECT/P10D (all times/forced-period)
11. Test period generation config 2017-01-01/2020-12-01/P8D (all forced)
12. Test period generation config 2017-01-01/DETECT/PT1M (forced start/forced subdaily period)
13. Test period generation config DETECT/2020-12-01/P1M (forced end/forced monthly period)


## mrfgen Tests:
1. Global geographic PNG-MRF
	* Global input image
	* Geographic projection
	* Paletted PNG input image
	* Paletted MRF-PNG output image
2. Tiled polar north JPEG-MRF
	* Tiled input images
	* Stereographic Polar North projection
	* JPEG input images
	* MRF-JPEG output image
3. Global web mercator JPEG-MRF
	* Global input image in geographic projection
	* Reprojection to web mercator
4. Geographic PNG-MRF using granule input files
 	* Granule input images with global coverage
 	* Input images cross antimeridian
	* Native geographic projection
	* Generate initial empty MRF with nocopy option
	* Insert into existing MRF
	* Create MRF with single granule
	* Create MRF composite image with multiple granules
	* Blend input images
	* Use z-levels
		* Add image to new z-level
		* Add image to existing z-level
		* Add image to multiple z-levels
5. Web Mercator PNG-MRF using granule input files
	* Granule input images with partial coverage
	* Reprojection to web mercator
	* No blending of input images
	* Automatic creation of empty MRF
6. Tiled geographic JPEG-MRF using tiled input files with z-level and time
	* Tiled input images
	* RGBA TIFF input images
	* Use single z-level
	* Use time (hh:mm:ss)
	* Use zdb lookup

## vectorgen Tests:
1. MVT MRF generation from single shapefile
2. MVT MRF generation from single GeoJSON
3. MVT MRF generation from multiple shapefiles
4. MVT MRF generation from multiple GeoJSON
5. MVT MRF generation with specified overview levels
6. MVT MRF generation with specified feature reduce rate
7. MVT MRF generation with specified cluster reduce rate
8. MVT MRF generation with feature filters
9. MVT MRF generation with overview filters
10. Shapefile generation from single GeoJSON 
11. Shapefile generation with differing `<target_epsg>` and `<source_epsg>`
12. GeoJSON generation from single GeoJSON
13. Shapefile generation from multiple GeoJSON using `<input_files>` (not in use: commented out)
14. Shapefile generation from multiple GeoJSON using `<input_dir>` (not in use: commented out)
15. Shapefile generation from multiple shapefiles (not in use: commented out)
16. MVT MRF generation with differing `<target_epsg>` and `<source_epsg>` (not in use: commented out)





## Legend Tests:

Tests legends in horizontal and vertical formats as PNGs and SVGs using various GIBS colormaps. The list of colormaps are configured in this [file](legends_test_data/colormaps.json).

## Sync S3 Tests:

1. Downloading a config from an S3 bucket to a directory containing other files
2. Deleting a config from a directory when the config isn't in the S3 bucket
3. Downloading a config from S3 and deleting a config that isn't in the S3 bucket

4. Deleting all configs from a directory when syncing with an empty S3 bucket (not in use: commented out)