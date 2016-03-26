#!/bin/env python

import os
import sys
import unittest2 as unittest
import random
import xmlrunner
from shutil import rmtree
from optparse import OptionParser

from oe_test_utils import check_tile_request, restart_apache, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command

DEBUG = False


class TestModOnEarth(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        testdata_path = os.path.join(os.getcwd(), 'mod_onearth_test_data')
        wmts_configs = ('wmts_cache_configs', 'wmts_cache_staging', 'test_imagery/cache_all_wmts.config')
        twms_configs = ('twms_cache_configs', 'twms_cache_staging', 'test_imagery/cache_all_twms.config')
        image_files_path = os.path.join(testdata_path, 'test_imagery')
        self.test_apache_config = os.path.join(testdata_path, 'oe_test.conf')
        
        for template_dir, staging_dir, cache_config in (wmts_configs, twms_configs):
            # Make staging cache files dir
            template_path = os.path.join(testdata_path, template_dir)
            staging_path = os.path.join(testdata_path, staging_dir)
            cache_path = os.path.join(testdata_path, cache_config)
            make_dir_tree(staging_path)

            # Copy XML/MRF files to staging cache files dir, swapping in the location of the imagery files
            for file in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
                file_text_replace(os.path.join(template_path, file), os.path.join(staging_path, file),
                                  '{cache_path}', image_files_path)

            # Run oe_create_cache_config to make the cache config files
            cmd = 'oe_create_cache_config -cbd {0} {1}'.format(staging_path, cache_path)
            run_command(cmd)
            rmtree(staging_path)

        # Put the correct path into the Apache config (oe_test.conf)
        file_text_replace(self.test_apache_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_config)),
                          '{cache_path}', testdata_path)
        restart_apache()

        # Set some handy constant values
        self.tile_hashes = {'210964547845bbeb357f62c214128215': '1990-01-01',
                            '403705d851af424b3bf9cafbbf869d0c': '2000-01-01',
                            '4832d6edeed31fad0bd59bbc26d92275': '2000-06-01',
                            '7ea2038a74af2988dc432a614ec94187': '2000-07-03',
                            '03b3cc7adc929dd605d617b7066b30ae': '2000-08-01',
                            'fd9e3aa7c12fbf823bd339b92920784e': '2000-12-01',
                            '24f90bd216f6b7ee25501155fcc8ece4': '2001-01-01',
                            '3d12e06c60b379efc41f4b8021ce1e29': '2001-05-09',
                            'e16d97b41cbb408d2a285788dfc9e3b8': '2002-01-01',
                            'b64066bafe897f0d2c0fc4a41ae7e052': '2002-12-27',
                            'f4426ab405ce748b57b34859b3811bf6': '2005-01-01',
                            '9a3cf29a5df271c41eefc5c989fd690d': '2008-01-01',
                            '84eba8cdbb26444dbc97e119c0b76728': '2010-01-01',
                            '91206f8c5a4f6fcdcab366ea00a1f53c': '2010-01-09',
                            '5346e958989b57c45919604ecf909f43': '2012-03-11',
                            '92e5d5eef4dc6866b636a49bfae3e463': '2015-01-01',
                            '5d91fa0c5273b2b58c486a15c91b2e78': '2015-01-02',
                            '81b8d855e38e6783f14899ff89a2c878': '2015-10-01',
                            '7f2992ac0986784c28d93840b1e984c4': '2016-02-29',
                            '1571c4d601dfd871e7680e279e6fd39c': '2015-01-12',
                            'b69307895d6cb654b98d247d710dd806': '2015-12-01',
                            'ba366ccd45a8f1ae0ed2b65cf67b9787': '2016-01-01',
                            '5e11f1220da2bb6f92d3e1c998f20bcf': 'black'}

        # URL that will be used to create the snap test requests
        self.snap_test_url_template = 'http://localhost/onearth/test/wmts/wmts.cgi?layer={0}&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME={1}'

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_wmts_no_time_jpg(self):
        """
        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'

        # The URL of the tile to be requested
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'

        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG tile via WMTS'
            print 'URL: ' + req_url

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_no_time_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no time) PNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_jpg(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (time=default) JPG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        if DEBUG:
            print '\nTesting: Request current (time=default) PNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_jpg(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current JPG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request current (no TIME) PNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + req_url)

    # REQUEST WITH DATE/TIME AND STATIC TESTS

    def test_request_wmts_date_from_year_layer(self):
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-22'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_date_from_noyear_layer(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date  from "non-year layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_legacy_datetime_from_year_layer(self):
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_static_notime(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_static_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS PNG request with date does not match what\'s expected. URL: ' + req_url)

    def test_request_date_kml(self):
        ref_hash = '69481cbae48db6f2e3603d1c16afc307'
        req_url = 'http://localhost/onearth/test/twms/kmlgen.cgi?layers=test_weekly_jpg&time=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date via KML'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'KML date request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_year_zlevel(self):
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_zindex_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T16:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (z-level) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS Z-Level JPG Tile Request does not match what\'s expected. URL: ' + req_url)
        
    # def test_request_twms_year_zlevel(self):
    #     ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
    #     req_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
    #     check_result = check_tile_request(req_url, ref_hash)
    #     self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + req_url)


    # DATE/TIME SNAPPING REQUESTS (should this be its own thing?)

    def test_snapping_1a(self):
        # This is the layer name that will be used in the WMTS request
        layer_name = 'snap_test_1a'

        # Tests are tuples with order of (request date, expected date)
        # Note that date/hash pairs must exist in self.tile_hashes dict
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-02', '2015-01-02'),
                 ('2016-02-29', '2016-02-29'),
                 ('2017-01-01', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Daily date (P1D)'
            print 'Time Period 1a: 2015-01-01/2016-12-31/P1D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 1a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_2a(self):
        layer_name = 'snap_test_2a'
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-11', 'black'),
                 ('2015-01-12', '2015-01-12'),
                 ('2015-02-01', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Irregular Daily date (PID with gaps)'
            print 'Time Period 2a: 2015-01-01/2015-01-10/P1D, 2015-01-12/2015-01-31/P1D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 2a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3a(self):
        layer_name = 'snap_test_3a'
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-20', '2015-01-01'),
                 ('2015-12-31', '2015-12-01'),
                 ('2016-01-01', '2016-01-01'),
                 ('2016-01-20', '2016-01-01'),
                 ('2016-02-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3a: 2015-01-01/2016-01-01/P1M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3b(self):
        layer_name = 'snap_test_3b'
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-20', '2015-01-01'),
                 ('2015-12-31', '2015-10-01'),
                 ('2016-01-01', '2016-01-01'),
                 ('2016-01-20', '2016-01-01'),
                 ('2016-04-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3b: 2015-01-01/2016-01-01/P3M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3b requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3c(self):
        layer_name = 'snap_test_3c'
        tests = (('1990-01-01', '1990-01-01'),
                 ('1990-05-20', '1990-01-01'),
                 ('2000-01-01', '2000-01-01'),
                 ('2000-05-20', '2000-01-01'),
                 ('2005-12-31', '2005-01-01'),
                 ('2017-01-01', 'black'),
                 ('1989-12-31', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3c: 1990-01-01/2016-01-01/P1Y'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3c requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3d(self):
        layer_name = 'snap_test_3d'
        tests = (('2010-01-01', '2010-01-01'),
                 ('2010-01-04', '2010-01-01'),
                 ('2010-01-10', '2010-01-09'),
                 ('2012-03-11', '2012-03-11'),
                 ('2012-03-14', '2012-03-11'),
                 ('2012-03-19', 'black'),
                 ('2009-12-31', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3d: 1990-01-01/2016-01-01/P1Y'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3d requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_4a(self):
        layer_name = 'snap_test_4a'
        tests = (('2000-01-01', '2000-01-01'),
                 ('2000-01-20', '2000-01-01'),
                 ('2000-06-10', '2000-06-01'),
                 ('2000-07-01', 'black'),
                 ('2000-07-02', 'black'),
                 ('2000-07-03', '2000-07-03'),
                 ('2000-07-20', '2000-07-03'),
                 ('2000-08-01', '2000-08-01'),
                 ('2000-08-10', '2000-08-01'),
                 ('2000-12-31', '2000-12-01'),
                 ('1999-12-31', 'black'),
                 ('2001-01-01', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods'
            print 'Time Period 4a: 2000-01-01/2000-06-01/P1M,2000-07-03/2000-07-03/P1M,2000-08-01/2000-12-01/P1M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 4a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_4b(self):
        layer_name = 'snap_test_4b'
        tests = (('2001-01-01', '2001-01-01'),
                 ('2001-01-05', '2001-01-01'),
                 ('2001-05-14', '2001-05-09'),
                 ('2002-01-01', '2002-01-01'),
                 ('2000-12-31', 'black'),
                 ('2003-01-01', '2002-12-27'),
                 ('2003-01-04', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods'
            print 'Time Period 4b: 2001-01-01/2001-12-27/P8D, 2002-01-01/2002-12-27/P8D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 4b requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    # REQUEST SYNTAX TESTS (capitalization, parameter ordering, error handling, REST)

    def test_url_parameter_case_insensitivity(self):
        # Randomly capitalizes and lower-cases parameters and checks the tile resulting from the request. Tries 10 different combinations.
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        if DEBUG:
            print '\nTesting URL Parameter Insensitivity'
        for _ in range(10):
            test_params = []
            for param in params:
                param_split = param.split('=')
                case = random.randint(0, 1)
                if case:
                    param_split[0] = param_split[0].upper()
                else:
                    param_split[0] = param_split[0].lower()
                test_params.append('='.join(param_split))
            req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?' + '&'.join(test_params)
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_url_parameter_reordering(self):
        # Test 20 random permutations of the given param strings
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ['layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0']
        if DEBUG:
            print 'Testing URL Parameter Reordering'
        for _ in range(20):
            random.shuffle(params)
            param_string = '&'.join(params)
            req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?' + param_string
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_error_handling(self):
        # MissingParameterValue test
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'version=1.0.0',
                  'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        if DEBUG:
            print '\nTesting WMTS Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?request=GetTile&time=default&' + '&'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad SERVICE value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Service=bad_value',
            # Bad VERSION value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Version=bad_value',
            # Bad LAYER value
            'http://localhost/onearth/test/wmts/wmts.cgi?tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&layer=bad_layer_value',
            # Bad STYLE value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&style=bad_value',
            # Bad FORMAT value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&TileMatrix=0&TileCol=0&TileRow=0&time=default&Format=fake_image',
            # Bad TILEMATRIXSET value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&tilematrixset=fake_tilematrixset',
            # Bad (non-positive integer) TILEMATRIX value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=-20',
            # Bad (non-positive integer) TILEROW value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&time=default&TileRow=-20',
            # Bad (non-positive integer) TILECOL value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileRow=0&time=default&TileCol=-20',
            # Invalid TILEMATRIX value
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=20',
            # Invalid TIME format
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-290'
        )
        for req_url in invalid_parameter_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # OperationNotSupported tests
        response_code = 501
        response_value = 'OperationNotSupported'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetLost&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        if DEBUG:
            print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
        check_code = check_response_code(req_url, response_code, response_value)
        error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
        self.assertTrue(check_code, error)

        # TileOutOfRange tests
        response_code = 400
        response_value = 'TileOutOfRange'
        tile_outofrange_urls = (
            # TileCol out of range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=50&TileRow=0&time=default',
            # TileRow out of range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=50&time=default'
        )
        for req_url in tile_outofrange_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # Test if empty tile is served for out of time bounds request
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        empty_urls = (  # Date before range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01',
            # Date after range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01'
        )
        for url in empty_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting empty tile'.format(url)
            check_result = check_tile_request(url, ref_hash)
            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-29&twoplustwo=five'
        if DEBUG:
            print 'Using URL: {0}, expecting bad parameter will be ignored'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Bad parameter request is not ignored. URL: ' + url)

    def test_REST_API(self):
        params = (('3f84501587adfe3006dcbf59e67cd0a3', 'http://localhost/onearth/test/wmts/test_weekly_jpg/default/2012-02-29/EPSG4326_16km/0/0/0.jpeg'),
                  ('9dc7e0fe96613fdb2d9855c3669ba524', 'http://localhost/onearth/test/wmts/test_weekly_jpg/default/2012-02-29/EPSG4326_16km/0/0/1.jpeg'))
        if DEBUG:
            print '\nTesting REST API'
        for ref_hash, url in params:
            if DEBUG:
                print 'Using URL ' + url
            check_result = check_tile_request(url, ref_hash)
            self.assertTrue(check_result, 'REST API request does not match what\'s expected: ' + url)

    # GETCAPABILITIES AND GETTILESERVICE REQUEST TESTS

    def test_wmts_get_capabilities(self):
        ref_hash = '74553d1c7ee662de1baa6a0788b42599'
        req_url = 'http://localhost/onearth/test/wmts/wmts.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting WMTS GetCapablities'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WTMTS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_capabilities(self):
        ref_hash = '982d923b04448f444d6efc769e71c9f2'
        req_url = 'http://localhost/onearth/test/twms/twms.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting TWMS GetCapablities'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_tile_service(self):
        ref_hash = 'dc758b15305c273eb2c65b0ab0262317'
        req_url = 'http://localhost/onearth/test/twms/twms.cgi?Request=GetTileService'
        if DEBUG:
            print '\nTesting WMTS GetTileService'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS Get GetTileService Request does not match what\'s expected. URL: ' + req_url)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_apache_config)))
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_onearth_results.xml',
                      help='Specify XML output file (default is test_mod_onearth_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModOnEarth.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
