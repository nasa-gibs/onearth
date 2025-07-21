
# OnEarth CI Test Scripts

This directory contains files and scripts to test various aspects of OnEarth. The included tests are:

* `test_colormap2vrt.py` -- tests `colormap2vrt.py`
* `test_colormap_html_sld.py` -- tests scripts for converting colormaps to HTML and SLD
* `test_gc_service.py` -- tests the OnEarth GetCapabilities Service
* `test_generate_empty_tile.py` -- tests empty tile generation with `oe_generate_empty_tile.py`
* `test_legends.py` -- tests the oe_generate_legend tool with GIBS colormaps
* `test_mapserver.py` -- tests wms requests via mapserver  
* `test_mod_mrf.py` -- tests the mod_mrf module
* `test_mod_reproject.py` -- tests the mod_reproject module
* `test_mod_twms.py` -- tests the mod_twms module
* `test_mod_wmts_wrapper.py` -- tests the mod_wmts_wrapper module
* `test_mrfgen.py` -- tests mrfgen
* `test_periods.py` -- tests `periods.py`
* `test_oe_best_redis.py` -- tests `oe_best_redis.py`
* `test_rgb_to_pal.py` -- tests RGB PNG to palette PNG
* `test_sync_s3.py` -- tests `oe_sync_s3_configs.py` and `oe_sync_s3_idx.py`
* `test_time_service.py` -- tests the OnEarth Time Service
* `test_time_utils.py` -- tests time configuration utilities
* `test_twmsbox_wmts_convert.py` -- tests ancillary WMTS/TWMS helper scripts (`twmsbox2wmts.py` and `wmts2twmsbox.py`)
* `test_validate_palette.py` -- tests `oe_validate_palette.py`
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

The output will say 
```
Ran x tests in xs

OK
```
If the tests were all successful 

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
2. Tests that a request to timeservice without parameters will return all records when there are records that use an unsorted set for the :periods key
3. Test time snap for P1Y layer (year)
4. Test time snap for P7D layer (week)
5. Test time snap for P1M layer (month)
6. Test time snap for PT2H layer (hour)
7. Test time snap for PT6M layer (minute)
8. Test time snap for PT6M layer (second)
9. Test invalid layer error
10. Test invalid date error 
11. Test out of range error for periods
12. Test snap with single key parameter (key1)
13. Test best layer to check filename, prefix, date
14. Test snap with multiple key parameter (key1, key2, key3, etc)
15. Test snapping to one of multiple periods
16. Test snapping to one of multiple periods when an unsorted set is used for the :periods key
17. Test requesting a static best layer
18. Test the limit option to return the first *n* periods
19. Test the limit option to return the last *n* periods
20. Test the limit option to return the first *n* periods when *n* is larger than the number of periods
21. Test the limit option to return the last *n* periods when *n* is larger than the number of periods
22. Test the skip option to return periods after the first *s* periods
23. Test that no periods are returned when the skip option is set to a number greater than the number of periods
24. Test using the skip option together with a begin limit
25. Test using the skip option together with a begin limit when an unsorted set is used for the :periods key
26. Test using the skip option with an end limit to skip the last *s* periods
27. Test using the skip and limit options to return the *n* periods after *s* when *n* is larger than the number of priods
28. Test using the skip and limit options to return the last *n* periods after *s* when *n* is larger than the number of periods
29. Test requesting periods between start and end dates
30. Test requesting periods between start and end dates when the start and end dates fall on the start and end bounds of existing periods, respectively.
31. Test requesting periods between start and end dates when there is a single period
32. Test requesting periods when there is a single period spanning a single day and the requested start date occurs before that day.
33. Test requesting periods after a start date
34. Test requesting periods before an end date
35. Test requesting periods when there are no periods that fall between the start and end date range
36. Test requesting periods when there are no periods at all for a layer
37. Test requesting periods between start and end dates when the start and end dates are within periods but do not correspond to dates that data would exist for, causing the start and end dates to be snapped to the next closest time within the periods
38. Test requesting periods between subdaily start and end dates when the start and end dates are within subdaily periods but do not correspond to dates that data would exist for, causing the start and end dates to be snapped to the next closest time within the periods
39. Test requesting periods between start and end dates when the start and end dates are not within any periods and there is an odd number of periods
40. Test requesting periods between start and end dates when the start and end dates are not within any periods and there is an even number of periods
41. Test requesting periods when the start and end dates fall within a period but there exists no valid dates between the start and end dates
42. Test requesting periods for all layers between start and end dates
43. Test requesting periods for all layers while using the limit option to return the first *n* periods
44. Test requesting periods for all layers while using the limit option to return the last *n* periods
45. Test requesting periods between start and end dates while using the limit option to return the first *n* periods
46. Test requesting periods between start and end dates while using the limit option to return the last *n* periods
47. Test a time snapping date request while specifying start and end dates

## Time Utilities Tests
***Contains functional tests for oe_scrape_time.py, oe_periods_configure.py, periods.py, and oe_periods_key_converter.py. For periods.py unit tests, see test_periods.py***
1. Time scrape S3 keys
2. Time scrape local keys
3. Time scrape S3 keys using a layer filter
4. Time scrape S3 inventory
5. Configure a time config from a layer config
6. Configure time configs for layers matching a pattern
7. Configure a `best_config` key
8. Config a `best_layer` key
9. Test period generation with single date
10. Test period generation with two dates
11. Test generation of multiple periods with a single config
12. Test period generation with subdaily
13. Test period generation with multiday
14. Test period generation with monthly
15. Test period generation with 2 monthly dates using DETECT
16. Test period generation with 3 monthly dates using DETECT
17. Test period generation config DETECT everything
18. Test period generation config DETECT/DETECT (start/end)
19. Test period generation config DETECT/DETECT/P5D (start/end/forced-period)
20. Test period generation config DETECT/P10D (all times/forced-period)
21. Test period generation config 2017-01-01/2020-12-01/P8D (all forced)
22. Test period generation with an all-forced config when no dates are available
23. Test period generation with a forced start config
24. Test period generation with a forced start config when the forced start date doesn't exist
25. Test period generation with a forced start config when there's no data after the forced start date
26. Test period generation with a forced end date
27. Test period generation config LATEST-15D/LATEST/P1D
28. Test period generation config LATEST-30D/DETECT/P1D
29. Test period generation config DETECT/LATEST/P1D
30. Test period generation using multiple time configs
31. Test period generation using multiple subdaily configs
32. Test period generation config LATEST-90D/LATEST/PT10M when there are no dates
33. Test period generation with multiple configs with subdaily times with forced periods
34. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P1D
35. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P4D
35. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P8D
36. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P16D
37. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P1M
38. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is P3M
39. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is PT1S
40. Test period generation when there's a gap between the earliest date and the rest of the dates and the config is DETECT and the expected interval is PT10M
41. Test period generation with multiple forced configs followed by a detected end date config for P8D
42. Test period generation with a forced start config when there are gaps in dates that are skipped due to the forced start
43. Test period generation with a DETECT config when there are 100,000 daily dates
44. Test period generation with a DETECT config when there are 10,000 monthly dates
45. Test period generation for irregularly varying time periods using periods.py's `keep_existing_periods` option
46. Test period generation using periods.py's `start_date`, `end_date`, and `keep_existing_periods` options
47. Test period generation for a layer that has a `copy_dates` key
48. Test period generation for a layer that already has periods stored as an unsorted `set` using `keep_existing_periods`
49. Test period generation for a layer that already has periods stored as an unsorted `set`
50. Test period generation for a layer that already has periods
51. Test ingesting a new date using periods.py
52. Test period generation using periods.py's `find_smallest_interval` option
53. Test converting `periods` keys from an unsorted `set` to a sorted `zset`
54. Test converting `periods` keys from a sorted `zset` to an unsorted `set`
55. Test converting a single layer's `periods` key from a sorted `zset` to an unsorted `set` using oe_periods_key_converter.py's layer filter option

## Periods.py Unit Tests
1. Test `get_zadd_dict`
2. Test `get_rd_from_interval`
3. Test `get_duration_from_rd`
4. Test `find_periods_and_breaks`
5. Test `calculate_periods_from_config` using a time config of `DETECT`
6. Test `calculate_periods_from_config` using a forced time config
7. Test `calculate_periods_from_config` using a time config with `LATEST`
8. Test `calculate_periods_from_config` with subdaily intervals between datetimes
9. Test `calculate_periods_from_config` when there are no dates
10. Test `calculate_periods_from_config` with a single date
11. Test `calculate_periods_from_config` with irregular intervals between dates
12. Test `calculate_periods_from_config` while using the `start_date` option
13. Test `calculate_periods_from_config` while using the `end_date` option
14. Test `calculate_periods_from_config` with detecting minute intervals
15. Test `calculate_periods_from_config` with the `find_smallest_interval` option
16. Test `calculate_periods_from_config` with subdaily times with irregular intervals and a config of `DETECT/DETECT/PT6M`
17. Test `calculate_layer_periods` while using multiple time configs
18. Test `calculate_layer_periods` while using the `keep_existing_periods` option

## oe_best_redis.py Tests
1. Test `calculate_layer_best` with a datetime specified
2. Test `calculate_layer_best` with a datetime specified and no best layer
3. Test `calculate_layer_best` with a datetime specified and multiple source layers
4. Test `calculate_layer_best` with a specified date that doesn't exist in any source layer's `:dates` key
5. Test `recalculate_best` to recalculate an entire `:best` key

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

## RGB PNG To PAL PNG Tests:
1. Large image
2. Small image
3. RGBAPal image
4. RGB (No-Alpha) image with one missing color 
5. Small image with 1 missing color
6. Small image with 101 missing color
7. Small image with no matching colors
8. Small image with mismatched transparency
9. Small image with invalid fill value
10. GeoTIFF image

## vectorgen Tests:
1. MVT MRF generation from single shapefile
2. MVT MRF generation from single GeoJSON
3. MVT MRF generation from single GeoJSON with polygon features
4. MVT MRF generation from multiple shapefiles
5. MVT MRF generation from multiple GeoJSON
6. MVT MRF generation with specified overview levels
7. MVT MRF generation with specified feature reduce rate
8. MVT MRF generation with specified cluster reduce rate
9. MVT MRF generation with feature filters
10. MVT MRF generation with overview filters
11. Shapefile generation from single GeoJSON 
12. Shapefile generation from single GeoJSON with polygon features
13. Shapefile generation with differing `<target_epsg>` and `<source_epsg>`
14. Cloud-optimized shapefile generation using `<cloud_optimized_shapefile>`
15. GeoJSON generation from single GeoJSON
16. Shapefile generation from multiple GeoJSON using `<input_files>` (not in use: commented out)
17. Shapefile generation from multiple GeoJSON using `<input_dir>` (not in use: commented out)
18. Shapefile generation from multiple shapefiles (not in use: commented out)
19. MVT MRF generation with differing `<target_epsg>` and `<source_epsg>` (not in use: commented out)





## Legend Tests:

Tests legends in horizontal and vertical formats as PNGs and SVGs using various GIBS colormaps. The list of colormaps are configured in this [file](legends_test_data/colormaps.json).

## Sync S3 Tests:

1. Downloading configs from an S3 bucket to an empty directory
2. Downloading a config from an S3 bucket to a directory that already contains some of the S3 bucket's configs
3. Deleting a config from a directory when the config isn't in the S3 bucket
4. Downloading a config from S3 and deleting a config that isn't in the S3 bucket
5. Performing a dry run of syncing configs using the `-n` (`--dry-run`) argument
6. Overwriting configs that already exist in the directory using the `-f` (`--force`) argument
7. Downloading IDX files from an S3 bucket to an empty directory
8. Downloading IDX files from an S3 bucket to a directory that already contains some of the S3 bucket's IDX files
9. Deleting IDX files from a directory that aren't found in the S3 bucket
10. Downloading IDX files to a directory from S3 and deleting IDX files from the directory that aren't found in the S3 bucket
11. Performing a dry run of syncing IDX files using the `-n` (`--dry-run`) argument
12. Overwriting IDX files that already exist in the directory using the `-f` (`--force`) argument
13. Overwriting IDX files whose checksums do not match those of corresponding files in S3 using the `-c` (`--checksum`) argument
14. Deleting all configs from a directory when syncing with an empty S3 bucket (not in use: commented out)
15. Deleting all IDX files from a directory when syncing with an empty S3 bucket (not in use: commented out)

## WMTS/TWMS Helper Scripts Tests:

1. Converting from a Tiled WMS box to WMTS tile using `twmsbox2wmts.py`
2. Converting from a Tiled WMS box to WMTS tile using `twmsbox2wmts.py` with a specified `--tilesize`
3. Converting from a WMTS tile to a Tiled WMS box using `wmts2twmsbox.py` with the `--scale_denominator` option
4. Converting from a WMTS tile to a Tiled WMS box using `wmts2twmsbox.py` with the `--scale_denominator` option and a specified `--tilesize`
5. Converting from a WMTS tile to a Tiled WMS box using `wmts2twmsbox.py` with the `--top_left_bbox` option
6. Using both scripts to convert from a Tiled WMS box to a WMTS tile and back to a Tiled WMS box, using the `--scale_denominator` option for `wmts2twmsbox.py`
7. Using both scripts to convert from a Tiled WMS box to a WMTS tile and back to a Tiled WMS box, using the `--top_left_bbox` option for `wmts2twmsbox.py`
8. Using both scripts to convert from a Tiled WMS box to a WMTS tile and back to a Tiled WMS box, using a specified `--tilesize` for each script and the `--top_left_bbox` option for `wmts2twmsbox.py`
9. Using both scripts to convert from a WMTS tile to a Tiled WMS box and back to a WMTS tile, using the `--scale_denominator` option for `wmts2twmsbox.py`
10. Using both scripts to convert from a WMTS tile to a Tiled WMS box and back to a WMTS tile, using a specified `--tilesize` for each script and the `--scale_denominator` option for `wmts2twmsbox.py`
11. Using both scripts to convert from a WMTS tile to a Tiled WMS box and back to a WMTS tile, using the `--top_left_bbox` option for `wmts2twmsbox.py`

## `oe_validate_palette.py` Tests:

1. Validating a colormap with a corresponding image that matches the colormap using the `--match_index` option
2. Validating a colormap with a corresponding image that matches the colormap
3. Validating a colormap with a corresponding image that matches the colormap using the `--ignore_colors` option
4. Validating a colormap with a corresponding image that matches the colormap using the `--fill_value` option
5. Correctly failing to validate a colormap with a non-corresponding image that doesn't match the colormap using the `--match_index` option
6. Correctly failing to validate a colormap with a non-corresponding image that doesn't match the colormap
7. Correctly failing to validate a colormap with a non-corresponding image that doesn't match the colormap using the `--ignore_colors` option
8. Correctly failing to validate a colormap with a non-corresponding image that doesn't match the colormap using the `--fill_value` option

## `colormap2vrt.py` Tests:

1. Merging a colormap with a VRT file to create a new VRT file.
2. Merging a colormap with a VRT file using the `--transparent` option to create a new VRT file.

## Empty Tile Generation Tests

The following test cases for `oe_generate_empty_tile.py` are defined in this [file](empty_tiles_test_data/colormaps.json):
1. Generating an empty tile from [ColorMap_v1.2_Sample.xml](empty_tiles_test_data/ColorMap_v1.2_Sample.xml)
2. Generating an empty tile from [SampleColorMap_v1.2_ContinuousAndClass.xml](empty_tiles_test_data/SampleColorMap_v1.2_ContinuousAndClass.xml)
3. Generating an empty tile using the `--height` and `--width` options
4. Generating an empty tile using the `--width` option
5. Generating an empty tile using the `--type rgba` option

## Colormap to HTML/SLD Tests

1. Converting a colormap to HTML using `colorMaptoHTML_v1.0.py`
2. Converting a colormap to HTML using `colorMaptoHTML_v1.3.py`
3. Converting a colormap to a v1.0.0 SLD using `colorMaptoSLD.py` with `-s 1.0.0`
4. Converting a colormap that has its "No Data" colormap listed first to a v1.1.0 SLD using `colorMaptoSLD.py` with `-s 1.1.0`
5. Converting a colormap that has its "No Data" colormap listed last to a v1.1.0 SLD using `colorMaptoSLD.py` with `-s 1.1.0`
6. Converting a v1.0.0 SLD to a colormap using `SLDtoColorMap.py`
7. Converting a v1.0.0 SLD to a colormap using `SLDtoColorMap.py` with the `--offset` and `--factor` options
8. Converting a v1.0.0 SLD to a colormap using `SLDtoColorMap.py` with the `--precision` option
9. Converting a v1.1.0 SLD to a colormap using `SLDtoColorMap.py`
10. Converting a v1.1.0 SLD to a colormap using `SLDtoColorMap.py` with the `--offset` and `--factor` options
11. Converting a v1.1.0 SLD to a colormap using `SLDtoColorMap.py` with the `--precision` option
12. Converting a v1.1.0 SLD to a colormap using `SLDtoColorMap.py` with the `--densify` option with `r` specified for "ramp"