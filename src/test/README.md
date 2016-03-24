#OnEarth CI Test Scripts

This directory contains files and scripts to test various aspects of OnEarth. The included tests are:


* `test_mod_onearth.py` -- tests the OnEarth Apache module
* `test_layer_config.py` -- tests the Layer Config tool

##Setup
These tests assume that OnEarth and its associated utilities are installed.

The contents of this directory need to be copied to `/etc/onearth/config`. You'll need to make sure that the `LCDIR` environment variable is properly set.

The tests have additional dependencies from the rest of OnEarth. To install the Python dependencies required by the test scripts, run `sudo pip install -r requirements.txt`.

##Running the Tests
Each test script will output a JUnit XML results file. By default, these files are named `test_layer_config_results.xml` and `test_mod_onearth_results.xml`. A different output filename can be specified with the `-o` option, i.e. `sudo python test_mod_onearth.py -o output_file.xml`.

**Note that the tests need to be run with root privileges.**

###Additional Test Options
####test_mod_onearth.py
* `-d, --debug` -- This will output verbose messages on the test operations to the output file.
* `-s, --start_server` -- This will load the test Apache configuration for manual testing purposes (normally the script deletes it when the tests are over.)

####test_layer_config.py
* `-d, --debug` -- This will display verbose messages about the files the script is creating and text it's searching for in the config tool output files.

--------
##List of test_layer_config tests:

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

##List of mod_onearth tests:
* Request current (no time) PNG tile via WMTS
* Request current (no time) JPEG tile via WMTS
* Request current (time=default) PNG tile via WMTS
* Request current (time=default) JPEG tile via WMTS
* Request tile with date from “year” layer via WMTS
* Request tile with date  from “non-year” layer via WMTS
* Request tile with date and time (sub-daily) from “year” layer via WMTS 
* Request tile with date and time (z-level) from “year” layer via WMTS
* Request tile from static layer with no time via WMTS
* Request current (no time) PNG tile via TWMS
* Request current (no time) JPEG tile via TWMS
* Request tile with date via TWMS
* Request tile with date via KML
* Request WMTS GetCapabilities
* Request TWMS GetCapabilities
* Request TWMS GetTileService
* WMTS Error handling
* URL Parameter Case Insensitivity
* URL Parameter Reordering
* WMTS REST requests

####Date Snapping Tests

1.  **Regular Daily date (P1D)**

    a.  **2015-01-01/2016-12-31/P1D**

        i.  **2015-01-01 -&gt; 2015-01-01**

        ii. **2015-01-02 -&gt; 2015-01-02**

        iii. **2016-02-29 -&gt; 2016-02-29**

        iv. **2017-01-01 -&gt; Blank Tile**

    b.  **2015-01-01/2015-01-10/P1D, 2015-01-12/2015-01-31/P1D**

        i.  **2015-01-01 -&gt; 2015-01-01**

        ii. **2015-01-11 -&gt; Blank Tile**

        iii. **2015-01-12 -&gt; 2015-01-12 **

        iv. **2015-02-01 -&gt; Blank Tile**

2.  **Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)**

    a.  **2015-01-01/2016-01-01/P1M**

        i.  **2015-01-01 -&gt; 2015-01-01**

        ii. **2015-01-20 -&gt; 2015-01-01**

        iii. **2015-12-31 -&gt; 2015-12-01**

        iv. **2016-01-01 -&gt; 2016-01-01**

        v.  **2016-01-20 -&gt; 2016-01-01**

        vi. **2016-02-01 -&gt; Blank Tile**

        vii. **2014-12-31 -&gt; Blank Tile**

    b.  **2015-01-01/2016-01-01/P3M**

        i.  **2015-01-01 -&gt; 2015-01-01**

        ii. **2015-01-20 -&gt; 2015-01-01**

        iii. **2015-12-31 -&gt; 2015-10-01**

        iv. **2016-01-01 -&gt; 2016-01-01**

        v.  **2016-01-20 -&gt; 2016-01-01**

        vi. **2016-04-01 -&gt; Blank Tile**

        vii. **2014-12-31 -&gt; Blank Tile**

    c.  **1990-01-01/2016-01-01/P1Y**

        i.  **1990-01-01 -&gt; 2000-01-01**

        ii. **1990-05-20 -&gt; 2000-01-01**

        iii. **2000-01-01 -&gt; 2000-01-01**

        iv. **2000-05-20 -&gt; 2000-01-01**

        v.  **2005-12-31 -&gt; 2005-01-01**

        vi. **2008-10-01 -&gt; 2008-01-01**

        vii. **2016-11-20 -&gt; 2016-01-01**

        viii. **2017-01-01 -&gt; Blank Tile**

        ix. **1989-12-31 -&gt; Blank Tile**

    d.  **2010-01-01/2012-03-11/P8D**

        i.  **2010-01-01 -&gt; 2010-01-01**

        ii. **2010-01-04 -&gt; 2010-01-01**

        iii. **2010-01-10 -&gt; 2010-01-09**

        iv. **2012-03-11 -&gt; 2012-03-11**

        v.  **2012-03-14 -&gt; 2012-03-11**

        vi. **2012-03-19 -&gt; Blank Tile**

        vii. **2009-12-31 -&gt; Blank Tile**

3.  **Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods)**

    a.  **2000-01-01/2000-06-01/P1M,2000-07-03/2000-07-03/P1M,2000-08-01/2000-12-01/P1M**

        i.  **2000-01-01 -&gt; 2000-01-01**

        ii. **2000-01-20 -&gt; 2000-01-01**

        iii. **2000-06-10 -&gt; 2000-06-01**

        iv. **2000-07-01 -&gt; Blank Tile**

        v.  **2000-07-02 -&gt; Blank Tile**

        vi. **2000-07-03 -&gt; 2000-07-03**

        vii. **2000-07-20 -&gt; 2000-07-03**

        viii. **2000-08-01 -&gt; 2000-08-01**

        ix. **2000-08-10 -&gt; 2000-08-01**

        x.  **2000-12-31 -&gt; 2000-12-01**

        xi. **1999-12-31 -&gt; Blank Tile**

        xii. **2001-01-01 -&gt; Blank Tile**

    b.  **2001-01-01/2001-12-27/P8D, 2002-01-01/2002-12-27/P8D**

        i.  **2001-01-01 -&gt; 2001-01-01**

        ii. **2001-01-05 -&gt; 2001-01-1**

        iii. **2001-05-14 -&gt; 2001-05-09**

        iv. **2002-01-01 -&gt; 2002-01-01**

        v.  **2000-12-31 -&gt; Blank Tile**

        vi. **2003-01-01 -&gt; 2002-12-27**

        vii. **2003-01-04 -&gt; Blank Tile**
