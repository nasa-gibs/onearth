
# OnEarth CI Test Scripts

This directory contains files and scripts to test various aspects of OnEarth. The included tests are:

* `test_mod_onearth.py` -- tests the OnEarth Apache module (requires `sudo`)
* `test_mod_oems.py` -- tests the mod_oems and mod_oemstime modules (requires `sudo`)
* `test_layer_config.py` -- tests the Layer Config tool
* `test_mrfgen.py` -- tests MRFgen
* `test_vectorgen.py` -- tests oe_vectorgen
* `test_legends.py` -- tests the oe_generate_legend tool with GIBS colormaps

## Running tests in Docker

There is a script called `bin/run_test_in_docker.sh` that will run a test script
inside of a Docker container.  It takes two parameters, the name of the onearth
Docker image to run the test in, and the name of the test script.  After
running, the results will be written to a file in the `src/test/results`
directory.

Example:

```
./bin/run_test_in_docker.sh gibs/onearth:latest test_mod_onearth.py
```

## Setup
These tests assume that OnEarth and its associated utilities are installed. **Test files for mod_onearth tests must be copied to a directory that Apache has permission to access.**

The tests have additional dependencies from the rest of OnEarth. To install the Python dependencies required by the test scripts, run `sudo pip install -r requirements.txt`.

## Running the Tests
Each test script will output a JUnit XML results file. By default, these files are named `test_layer_config_results.xml` and `test_mod_onearth_results.xml`. A different output filename can be specified with the `-o` option, i.e. `sudo python test_mod_onearth.py -o output_file.xml`.

**Note that the included `mod_onearth_test_data/twms_endpoint/kmlgen.cgi` has been compiled for use in CentOS 6. It may need to be recompiled for other systems. For more information, see [OnEarth Endpoint Configuration](doc/config_endpoint.md).**

**Note also that the mrfgen tests involve the downloading and processing of imagery, so they may take a while to complete. You may experience 'out of memory' errors if running these tests in a VM without enough memory configured.**


### Additional Test Options
#### test_mod_onearth.py
* `-d, --debug` -- This will output verbose messages on the test operations to the output file.
* `-s, --start_server` -- This will load the test Apache configuration for manual testing purposes (normally the script deletes it when the tests are over.)

#### test_mod_oems.py
* `-d, --debug` -- This will output verbose messages on the test operations to the output file.
* `-s, --start_server` -- This will load the test Apache configuration for manual testing purposes (normally the script deletes it when the tests are over.)

#### test_layer_config.py
* `-d, --debug` -- This will display verbose messages about the files the script is creating and text it's searching for in the config tool output files.

#### test_mrfgen.py
* `-d, --debug` -- This will display verbose messages about the files the script is creating and text it's searching for in the config tool output files.

#### test_vectorgen.py
* `-d, --debug` -- This will display verbose messages about the files the script is creating and text it's searching for in the config tool output files.

#### test_legends.py
* `-d, --debug` -- This will display verbose messages about the files the script is creating and text it's searching for in the config tool output files.


--------
## List of test_layer_config tests:

1.  Configure a static layer for WMTS
2.  Configure a daily layer with no year for WMTS
3.  Configure a daily layer with year for WMTS
4.  Configure a sub-daily layer with year for WMTS
5.  Configure a daily layer with year and z-level times for WMTS
6.  Configure a daily layer with no year and z-level times for WMTS
7.  Configure a static layer for TWMS
8.  Configure a daily layer with no year for TWMS
9.  Configure a daily layer with year for TWMS
10. Configure a sub-daily layer with year for TWMS
11. Configure a daily layer with year and z-level times for TWMS
12. Configure a daily layer with no year and z-level times for TWMS
13. Check empty tile
14. Generate vertical legend from Classification color map
15. Generate horizontal legend from Classification color map
16. Generate vertical legend from Continuous color map
17. Generate horizontal legend from Continuous color map
18. Generate vertical legend from Discrete color map
19. Generate horizontal legend from Discrete color map
20. Generate vertical legend from Mixed Discrete/Continuous w/ Classification color map
21. Generate horizontal legend from Mixed Discrete/Continuous w/ Classification color map
22. Generate vertical legend from Multiple Discrete/Continuous color map
23. Generate horizontal legend from Multiple Discrete/Continuous color map
24. Continuous daily period detection
25. Intermittent daily period detection
26. Continuous multi-day period detection
27. Intermittent multi-day period detection
28. Continuous sub-daily “legacy” period detection
29. Intermittent sub-daily “legacy” period detection
30. Z-level period detection
32. Continuous monthly period detection
33. Intermittent monthly period detection
34. Continuous yearly period detection
35. Intermittent yearly period detection
36. Generate empty tile
37. Support for versioned color maps

## List of mod_onearth tests:
1. Request current (no time) JPEG tile via WMTS
2. Request current (no time) PNG tile via WMTS
3. Request current (time=default) JPEG tile via WMTS
4. Request current (time=default) PNG tile via WMTS
5. Request current (no time) JPEG tile via TWMS
6. Request current (no time) PNG tile via TWMS
7. Request tile with date from “year” layer via WMTS
8. Request tile with date  from “non-year” layer via WMTS
9. Request tile with date and time (sub-daily) from “year” layer via WMTS
10. Request tile with date and time (z-level) from “year” layer via WMTS
11. Request tile with date and time (z-level) from “year” layer via TWMS
11. Request tile from static layer with no time via WMTS
12. Request tile with date via TWMS
13. Request tile with date via KML
14. Request WMTS GetCapabilities
15. Request TWMS GetCapabilities
16. Request TWMS GetTileService
17. URL Parameter Case Insensitivity
18. URL Parameter Reordering
19. WMTS Error handling
20. WMTS REST requests

#### Date Snapping Tests

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

## List of mod_oems tests:

1. Request current (no time) JPEG via WMS
2. Request current (no time) PNG via WMS
3. Request current (time=default) JPEG tile via WMS
4. Request current (time=default) PNG tile via WMS
5. Request tile with date from "year" layer via WMS
6. Request tile with date from "non-year" layer via WMS
7. Request tile with date and time (sub-daily) from "year" layer via WMS
8. Request WMS GetCapabilities 1.1.1
9. Request WMS GetCapabilities 1.3.0
10. Request WFS GetCapabilities 2.0.0
11. Request erroneous layer via WMS
12. Request tile with date and time (sub-daily) and another layer with YYYY-MM-DD time via WMS
13. Request tile with multi-day period and snap to available date via WMS
14. Request multiple layers with multi-day period and snap to available date via WMS
15. Request multiple layers with multi-day period and snap to date that is out of range via WMS
16. Request multiple layers with multi-day period and snap to date that is out of range for one of the layers via WMS
17. Request multiple layers with bad date format via WMS
18. Request layer with date and reproject from EPSG:4326 to EPSG:3857 via WMS
19. Request multiple layers and reproject from EPSG:4326 to EPSG:3857 via WMS
20. Request tile with time (sub-daily) and snap to available date time via WMS
21. Request image from vector source file with time via WMS
22. Request GeoJSON from vector source file via WFS
23. Request CSV from vector source file via WFS
24. Request GeoJSON from vector source file with time via WFS
25. Request CSV from vector source file with time via WFS

## List of mrfgen tests:
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

## List of vectorgen tests:
1. MVT MRF generation
2. Shapefile generation

## List of legend tests:

Tests legends in horizontal and vertical formats as PNGs and SVGs using various GIBS colormaps. The list of colormaps are configured in this [file](legends_test_data/colormaps.json).
