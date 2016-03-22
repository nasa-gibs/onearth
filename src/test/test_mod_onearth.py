#!/bin/env python

import os
import sys
import unittest2 as unittest
import random
import xmlrunner
import shutil

import pdb

from oe_test_utils import check_tile_request, restart_apache, check_response_code


class TestModOnEarth(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # Setup entails getting LCDIR, creating test WMTS/TWMS endpoints, and adding a new test config to Apache
        # Get LCDIR envvar
        try:
            self.lcdir = os.environ['LCDIR']
        except KeyError:
            self.lcdir = os.path.abspath(os.pdbath.dirname(__file__) + '/..')

        # Add test endpoint/cache config to Apache
        os.path.join(self.lcdir, 'test/onearth_test.conf')
        self.test_apache_config = os.path.join('/etc/httpd/conf.d/', 'oe_test.conf')
        shutil.copy(os.path.join(self.lcdir, 'test/oe_test.conf'), self.test_apache_config)
        restart_apache()

    def test_request_wmts_no_time_jpg(self):
        """
        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'

        # The URL of the tile to be requested
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS JPG Tile Request does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_no_time_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS PNG Tile Request does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_default_time_jpg(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS JPG Tile Request does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_default_time_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PNG Tile Request does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_date_from_year_layer(self):
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-22'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "year" layer does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_date_from_noyear_layer(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "year" layer does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_legacy_datetime_from_year_layer(self):
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T12:00:00Z'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy subdaily request does not match what\'s expected. URL: ' + request_url)

    def test_request_static_notime(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_static_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'WMTS static notime request does not match what\'s expected. URL: ' + request_url)
        
    def test_request_twms_current_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        request_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)

    def test_request_twms_date_png(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        request_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90&TIME=2012-02-29'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)

    def test_request_twms_current_jpg(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        request_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current JPG request does not match what\'s expected. URL: ' + request_url)

    def test_request_current_png_wmts(self):
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        request_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)

    def test_request_wmts_year_zlevel(self):
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_zindex_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T16:00:00Z'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'WMTS Z-Level JPG Tile Request does not match what\'s expected. URL: ' + request_url)
        
    # def test_request_twms_year_zlevel(self):
    #     ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
    #     request_url = 'http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_daily_png&amp;srs=EPSG:4326&amp;format=image%2Fpng&amp;styles=&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
    #     check_result = check_tile_request(request_url, ref_hash)
    #     self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)

    def test_request_multi_day_date_snapping(self):
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-28'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)
    
    def test_request_legacy_subdaily_snapping(self):
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T13:00:00Z'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + request_url)

    def test_request_date_kml(self):
        ref_hash = '69481cbae48db6f2e3603d1c16afc307'
        request_url = 'http://localhost/onearth/test/twms/kmlgen.cgi?layers=test_weekly_jpg&time=2012-02-29'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'KML date request does not match what\'s expected. URL: ' + request_url)

    def test_url_parameter_case_insensitivity(self):
        # Randomly capitalizes and lower-cases parameters and checks the tile resulting from the request. Tries 10 different combinations.
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
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
            request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?' + '&'.join(test_params)
            check_result = check_tile_request(request_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + request_url)

    def test_url_parameter_reordering(self):
        # Test 20 random permutations of the given param strings
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ['layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0']
        for _ in range(20):
            random.shuffle(params)
            param_string = '&'.join(params)
            request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?' + param_string
            check_result = check_tile_request(request_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + request_url)

    def test_wmts_error_handling(self):
        # MissingParameterValue test
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'version=1.0.0',
                  'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?request=GetTile&time=default&' + '&'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'
            check_code = check_response_code(request_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(request_url, response_code)
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
        for request_url in invalid_parameter_urls:
            check_code = check_response_code(request_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(request_url, response_code)
            self.assertTrue(check_code, error)

        # OperationNotSupported tests
        response_code = 501
        response_value = 'OperationNotSupported'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetLost&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        check_code = check_response_code(request_url, response_code, response_value)
        error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(request_url, response_code)
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
        for request_url in tile_outofrange_urls:
            check_code = check_response_code(request_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(request_url, response_code)
            self.assertTrue(check_code, error)

        # Test if empty tile is served for out of time bounds request
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        empty_urls = (  # Date before range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01',
            # Date after range
            'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01'
        )
        for url in empty_urls:
            check_result = check_tile_request(url, ref_hash)
            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        request_url = 'http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-29&twoplustwo=five'
        check_result = check_tile_request(request_url, ref_hash)
        self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

    def test_REST_API(self):
        params = ({'hash': '3f84501587adfe3006dcbf59e67cd0a3', 'url': 'http://localhost/onearth/test/wmts/test_weekly_jpg/default/2012-02-29/EPSG4326_16km/0/0/0.jpeg'},
                  {'hash': '9dc7e0fe96613fdb2d9855c3669ba524', 'url': 'http://localhost/onearth/test/wmts/test_weekly_jpg/default/2012-02-29/EPSG4326_16km/0/0/1.jpeg'}
                  )

        for param in params:
            check_result = check_tile_request(param['url'], param['hash'])
            self.assertTrue(check_result, 'REST API request does not match what\'s expected: ' + param['url'])

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(self.test_apache_config)
        restart_apache()


if __name__ == '__main__':
    try:
        outfile = sys.argv[1]
        # Unittest reads command-line arguments, which confuses things, so we delete them after reading them.
        del sys.argv[1:]
    except IndexError:
        outfile = 'test_mod_onearth_results.xml'
    with open(outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
