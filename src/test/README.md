
# OnEarth CI Test Scripts

This directory contains files and scripts to test various aspects of OnEarth. The included tests are:

* `test_gc_service.py` -- tests the OnEarth GetCapabilities Service
* `test_legends.py` -- tests the oe_generate_legend tool with GIBS colormaps
* `test_mod_mrf.py` -- tests the mod_mrf module
* `test_mod_reproject.py` -- tests the mod_reproject module
* `test_mod_twms.py` -- tests the mod_twms module
* `test_mod_wmts_wrapper.py` -- tests the mod_wmts_wrapper module
* `test_mrfgen.py` -- tests mrfgen
* `test_time_service.py` -- tests the OnEarth Time Service
* `test_time_utils.py` -- tests time configuration utilities
* `test_vectorgen.py` -- tests vectorgen

## Running tests in Docker

There is a script called `bin/run_test_in_docker.sh` that will run a test script
inside of a Docker container.  It takes two parameters, the name of the onearth
Docker image to run the test in, and the name of the test script.  After
running, the results will be written to a file in the `src/test/results`
directory.

Example:

```
./bin/run_test_in_docker.sh nasagibs/onearth-test:latest test_mod_mrf.py
```

## Setup
These tests assume that OnEarth and its associated utilities are installed. **Test files for mod_* tests must be copied to a directory that Apache has permission to access.**

The tests have additional dependencies from the rest of OnEarth. To install the Python dependencies required by the test scripts, run `sudo pip3 install -r requirements.txt`.

## Running the Tests
Each test script will output a JUnit XML results file. By default, these files are named `*_results.xml`. A different output filename can be specified with the `-o` option, i.e. `sudo python test_mod_mrf.py -o output_file.xml`.

**Note also that the mrfgen tests involve the downloading and processing of imagery, so they may take a while to complete. You may experience 'out of memory' errors if running these tests in a VM without enough memory configured.**


--------
## Time Service Tests

1.  **Regular Daily date (P1D)**

    a.  **2015-01-01/2016-12-31/P1D**

        i.  2015-01-01 -> 2015-01-01

        ii. 2015-01-02 -> 2015-01-02

        iii. 2016-02-29 -> 2016-02-29

        iv. 2017-01-01 -> Blank Tile

    b.  **2015-01-01/2015-01-10/P1D, 2015-01-12/2015-01-31/P1D**

        i.  2015-01-01 -> 2015-01-01

        ii. 2015-01-11 -> Blank Tile

        iii. 2015-01-12 -> 2015-01-12

        iv. 2015-02-01 -> Blank Tile

2.  **Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)**

    a.  **2015-01-01/2016-01-01/P1M**

        i.  2015-01-01 -> 2015-01-01

        ii. 2015-01-20 -> 2015-01-01

        iii. 2015-12-31 -> 2015-12-01

        iv. 2016-01-01 -> 2016-01-01

        v.  2016-01-20 -> 2016-01-01

        vi. 2016-02-01 -> Blank Tile

        vii. 2014-12-31 -> Blank Tile

    b.  **2015-01-01/2016-01-01/P3M**

        i.  2015-01-01 -> 2015-01-01

        ii. 2015-01-20 -> 2015-01-01

        iii. 2015-12-31 -> 2015-10-01

        iv. 2016-01-01 -> 2016-01-01

        v.  2016-01-20 -> 2016-01-01

        vi. 2016-04-01 -> Blank Tile

        vii. 2014-12-31 -> Blank Tile

    c.  **1990-01-01/2016-01-01/P1Y**

        i.  1990-01-01 -> 2000-01-01

        ii. 1990-05-20 -> 2000-01-01

        iii. 2000-01-01 -> 2000-01-01

        iv. 2000-05-20 -> 2000-01-01

        v.  2005-12-31 -> 2005-01-01

        vi. 2008-10-01 -> 2008-01-01

        vii. 2016-11-20 -> 2016-01-01

        viii. 2017-01-01 -> Blank Tile

        ix. 1989-12-31 -> Blank Tile

    d.  **2010-01-01/2012-03-11/P8D**

        i.  2010-01-01 -> 2010-01-01

        ii. 2010-01-04 -> 2010-01-01

        iii. 2010-01-10 -> 2010-01-09

        iv. 2012-03-11 -> 2012-03-11

        v.  2012-03-14 -> 2012-03-11

        vi. 2012-03-19 -> Blank Tile

        vii. 2009-12-31 -> Blank Tile

3.  **Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods)**

    a.  **2000-01-01/2000-06-01/P1M,2000-07-03/2000-07-03/P1M,2000-08-01/2000-12-01/P1M**

        i.  2000-01-01 -> 2000-01-01

        ii. 2000-01-20 -> 2000-01-01

        iii. 2000-06-10 -> 2000-06-01

        iv. 2000-07-01 -> Blank Tile

        v.  2000-07-02 -> Blank Tile

        vi. 2000-07-03 -> 2000-07-03

        vii. 2000-07-20 -> 2000-07-03

        viii. 2000-08-01 -> 2000-08-01

        ix. 2000-08-10 -> 2000-08-01

        x.  2000-12-31 -> 2000-12-01

        xi. 1999-12-31 -> Blank Tile

        xii. 2001-01-01 -> Blank Tile

    b.  **2001-01-01/2001-12-27/P8D, 2002-01-01/2002-12-27/P8D**

        i.  2001-01-01 -> 2001-01-01

        ii. 2001-01-05 -> 2001-01-1

        iii. 2001-05-14 -> 2001-05-09

        iv. 2002-01-01 -> 2002-01-01

        v.  2000-12-31 -> Blank Tile

        vi. 2003-01-01 -> 2002-12-27

        vii. 2003-01-04 -> Blank Tile
        
## Time Utilities Tests
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
1. MVT MRF generation
2. Shapefile generation

## Legend Tests:

Tests legends in horizontal and vertical formats as PNGs and SVGs using various GIBS colormaps. The list of colormaps are configured in this [file](legends_test_data/colormaps.json).
