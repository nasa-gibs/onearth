#!/usr/bin/env python3

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Tests for mrfgen.py
#

import os
import sys
import unittest2 as unittest
import xmlrunner
import filecmp
import shutil
import datetime
import sqlite3
from osgeo import gdal
from optparse import OptionParser
from io import StringIO
from oe_test_utils import DebuggingServerThread, make_dir_tree, mrfgen_run_command as run_command

DEBUG = False
SAVE_RESULTS = False

year = datetime.datetime.now().strftime('%Y')
doy = int(datetime.datetime.now().strftime('%j'))-1


class TestMRFGeneration_paletted(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config1a.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('input_dir', 'output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp1.png")

        #generate MRF
        #pdb.set_trace()
        run_command("mrfgen -c " + test_config, show_output=DEBUG)
        
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(geotransform[1], 0.087890625, "Pixel size does not match")
        self.assertEqual(geotransform[5], -0.087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 3, "Overview count does not match")

        if DEBUG:
            print('Colors:', band.GetRasterColorTable().GetCount())
        self.assertEqual(band.GetRasterColorTable().GetCount(), 256, "Color count does not match")       
        for x in range(0, 255):
            color = band.GetRasterColorTable().GetColorEntry(x)
            if DEBUG:
                print(color)
            if x == 0:
                self.assertEqual(str(color), '(220, 220, 255, 0)', "Color does not match")
            if x == 1:
                self.assertEqual(str(color), '(0, 0, 0, 255)', "Color does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_paletted_nnb(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config1c.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('input_dir', 'output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/MYR4ODLOLLDY2014277_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp1.png")

        # generate MRF
        # pdb.set_trace()
        run_command("mrfgen -c " + test_config, show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),
                         'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        if DEBUG:
            print('Size: ', dataset.RasterXSize, 'x', dataset.RasterYSize, 'x', dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (', geotransform[0], ',', geotransform[3], ')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (', geotransform[1], ',', geotransform[5], ')')
        self.assertEqual(geotransform[1], 0.087890625, "Pixel size does not match")
        self.assertEqual(geotransform[5], -0.087890625, "Pixel size does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 3, "Overview count does not match")

        if DEBUG:
            print('Colors:', band.GetRasterColorTable().GetCount())
        self.assertEqual(band.GetRasterColorTable().GetCount(), 256, "Color count does not match")
        for x in range(0, 255):
            color = band.GetRasterColorTable().GetColorEntry(x)
            if DEBUG:
                print(color)
            if x == 0:
                self.assertEqual(str(color), '(220, 220, 255, 0)', "Color does not match")
            if x == 1:
                self.assertEqual(str(color), '(0, 0, 0, 255)', "Color does not match")

        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")
        img = driver.CreateCopy(self.output_img, mrf, 0)

        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ', img.RasterXSize, 'x', img.RasterYSize, 'x', img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")

        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")

        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_nonpaletted(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        self.tmp_area = os.path.join(self.staging_area, 'tmp')
        test_config = os.path.join(testdata_path, "mrfgen_test_config1b.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Create non-paletted PNG using gdal_translate
        if DEBUG:
            print("Generating global image: non-paletted PNG")
        shutil.copytree(os.path.join(testdata_path, 'bluemarble_small'), os.path.join(self.tmp_area, 'bluemarble_small'))
        self.input_jpg = os.path.join(self.tmp_area, "bluemarble_small/bluemarble_small.jpg")
        self.output_png = os.path.join(self.tmp_area, "bluemarble_small/bluemarble_small.png")
        run_command('gdal_translate -of PNG ' + self.input_jpg + ' ' + self.output_png, show_output=DEBUG)
        shutil.copytree(os.path.join(self.tmp_area, 'bluemarble_small'), os.path.join(self.staging_area, 'bluemarble_small'))

        # Copy empty output tile and input imagery
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))
        #shutil.copytree(os.path.join(testdata_path, 'bluemarble_small'), os.path.join(self.staging_area, 'bluemarble_small'))
        shutil.copy2(os.path.join(testdata_path, 'bluemarble_small/bluemarble_small.jgw'), os.path.join(self.staging_area, 'bluemarble_small'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp1b.png")

        # generate MRF
        #pdb.set_trace()
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)
        
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        #self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(str(geotransform[1]), '0.087890625', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-0.087890625', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 4, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)
        

class TestMRFGeneration_polar(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config2a.xml")

        # Make source image dir
        input_dir = os.path.join(testdata_path, 'MORCR143ARDY')
        make_dir_tree(os.path.join(input_dir), ignore_existing=True)
        
        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.mrf")
        self.output_pjg = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.jpg")
        self.compare_img = os.path.join(testdata_path, "test_comp2.jpg")
            
        # generate MRF
        run_command("mrfgen -c " + test_config)
           
    def test_generate_mrf_polar(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]')

        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -4194304, "Origin does not match")
        self.assertEqual(geotransform[3], 4194304, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(int(geotransform[1]), 4096, "Pixel size does not match")
        self.assertEqual(int(geotransform[5]), -4096, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")

        img = None
        mrf = None
        
    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_polar_avg(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config2b.xml")

        # Make source image dir
        input_dir = os.path.join(testdata_path, 'MORCR143ARDY')
        make_dir_tree(os.path.join(input_dir), ignore_existing=True)

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.mrf")
        self.output_pjg = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/MORCR143ARDY2017248_.jpg")
        self.compare_img = os.path.join(testdata_path, "test_comp2.jpg")

        # generate MRF
        run_command("mrfgen -c " + test_config)

    def test_generate_mrf_polar(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),
                         'PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]')

        if DEBUG:
            print('Size: ', dataset.RasterXSize, 'x', dataset.RasterYSize, 'x', dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (', geotransform[0], ',', geotransform[3], ')')
        self.assertEqual(geotransform[0], -4194304, "Origin does not match")
        self.assertEqual(geotransform[3], 4194304, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (', geotransform[1], ',', geotransform[5], ')')
        self.assertEqual(int(geotransform[1]), 4096, "Pixel size does not match")
        self.assertEqual(int(geotransform[5]), -4096, "Pixel size does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")

        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")
        img = driver.CreateCopy(self.output_img, mrf, 0)

        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ', img.RasterXSize, 'x', img.RasterYSize, 'x', img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")

        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")

        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_mercator(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config3a.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile and input imagery
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))
        shutil.copytree(os.path.join(testdata_path, 'bluemarble_small'), os.path.join(self.staging_area, 'bluemarble_small'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.mrf")
        self.output_pjg = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.jpg")
        self.compare_img = os.path.join(testdata_path, "test_comp3.jpg")
            
        # generate MRF
        #pdb.set_trace()
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(str(geotransform[1]), '39135.7584765625', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-39135.7584765625', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_mercator_avg(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config3b.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile and input imagery
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))
        shutil.copytree(os.path.join(testdata_path, 'bluemarble_small'),
                        os.path.join(self.staging_area, 'bluemarble_small'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.mrf")
        self.output_pjg = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/BlueMarbleSmall2014237_.jpg")
        self.compare_img = os.path.join(testdata_path, "test_comp3.jpg")

        # generate MRF
        # pdb.set_trace()
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ', ' ')),
                         'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')

        if DEBUG:
            print('Size: ', dataset.RasterXSize, 'x', dataset.RasterYSize, 'x', dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (', geotransform[0], ',', geotransform[3], ')')
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (', geotransform[1], ',', geotransform[5], ')')
        self.assertEqual(str(geotransform[1]), '39135.7584765625', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-39135.7584765625', "Pixel size does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")

        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")
        img = driver.CreateCopy(self.output_img, mrf, 0)

        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ', img.RasterXSize, 'x', img.RasterYSize, 'x', img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")

        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")

        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_granule(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.input_dir = os.path.join(testdata_path, 'obpg')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config4a = os.path.join(testdata_path, "mrfgen_test_config4a.xml")
        test_config4b = os.path.join(testdata_path, "mrfgen_test_config4b.xml")
        test_config4c = os.path.join(testdata_path, "mrfgen_test_config4c.xml")
        test_config4d = os.path.join(testdata_path, "mrfgen_test_config4d.xml")

        # Make source image dir
        make_dir_tree(self.input_dir, ignore_existing=True)

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/OBPG2015336_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/OBPG2015336_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/OBPG2015336_.idx")
        self.output_zdb = os.path.join(self.staging_area, "output_dir/OBPG2015336_.zdb")
        self.output_img_a = os.path.join(self.staging_area, "output_dir/OBPG2015336_.png")
        self.output_img_b = os.path.join(self.staging_area, "output_dir/OBPG2015336_Z0.png")
        self.output_img_c = os.path.join(self.staging_area, "output_dir/OBPG2015336_Z1.png")
        self.output_img_d = os.path.join(self.staging_area, "output_dir/OBPG2015336_Z2.png")
        self.compare_img_b = os.path.join(testdata_path, "test_comp4b.png")
        self.compare_img_c = os.path.join(testdata_path, "test_comp4c.png")
        self.compare_img_d = os.path.join(testdata_path, "test_comp4d.png")

        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Aqua_Chlorophyll_A.xml"), os.path.join(self.staging_area, 'working_dir'))
        if DEBUG:
            print("Generating empty MRF with No Copy option")

        #pdb.set_trace()
        run_command("mrfgen -c " + test_config4a, show_output=DEBUG)
        if DEBUG:
            print("Generating global composite using granules with existing NoCopy MRF at z=0")
        run_command("mrfgen -c " + test_config4b, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf+':MRF:Z0 ' + self.output_img_b, show_output=DEBUG)
        if DEBUG:
            print("Generating global image with single granules with existing NoCopy MRF at z=1")
        run_command("mrfgen -c " + test_config4c, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf+':MRF:Z1 ' + self.output_img_c, show_output=DEBUG)
        if DEBUG:
            print("Generating global image with single granules with existing NoCopy MRF at z=2")
        run_command("mrfgen -c " + test_config4d, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf + ':MRF:Z2 ' + self.output_img_d, show_output=DEBUG)
           
    def test_generate_mrf(self):
        '''
        This portion the following test cases:
            Test using empty MRF with No Copy option
        '''
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img_a, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        '''
        This portion covers the following test cases:
            Test composite MRF with No Copy option
            Test using granule images
            Test using existing MRF
            Test using granule images with Z-level
            Test input images that cross antimeridian
            Test merging of input images with transparency
            Test adding image to existing Z-level
        '''
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf+":MRF:Z0")
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img_b)
        if DEBUG:
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)        
            print("Comparing: " + self.output_img_b + " to " + self.compare_img_b)
        self.assertTrue(filecmp.cmp(self.output_img_b, self.compare_img_b), "Output composite image does not match")

        '''
        This portion covers the following test cases:        
            Test adding image to new Z-level
            Test adding image to multiple Z-levels
            Test using single image with Z-level
        '''
        # Read MRF
        dataset = gdal.Open(self.output_mrf+":MRF:Z1")
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Convert and compare MRF
        img = gdal.Open(self.output_img_c)
        if DEBUG:
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)        
            print("Comparing: " + self.output_img_c + " to " + self.compare_img_c)
        self.assertTrue(filecmp.cmp(self.output_img_c, self.compare_img_c), "Output granule image does not match")

        '''
        This portion covers the following test cases:        
            Same as previous item, but with the 'NNb' resampling method
        '''
        # Read MRF
        dataset = gdal.Open(self.output_mrf + ":MRF:Z2")
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),
                         'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        if DEBUG:
            print('Size: ', dataset.RasterXSize, 'x', dataset.RasterYSize, 'x', dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (', geotransform[0], ',', geotransform[3], ')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (', geotransform[1], ',', geotransform[5], ')')
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")

        # Convert and compare MRF
        img = gdal.Open(self.output_img_d)
        if DEBUG:
            print('Size: ', img.RasterXSize, 'x', img.RasterYSize, 'x', img.RasterCount)
            print("Comparing: " + self.output_img_d + " to " + self.compare_img_d)
        self.assertTrue(filecmp.cmp(self.output_img_d, self.compare_img_d), "Output granule image does not match")


        img = None
        
        # Test ZDB
        if DEBUG:
            print("Checking " + self.output_zdb)
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print("Number of records: " + str(lid))
        self.assertEqual(lid, 3, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print(key_str)
        self.assertEqual(key_str, '20151202', "Time for Z=0 does not match in ZDB")
        cur.execute("SELECT key_str FROM ZINDEX where z=1;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print(key_str)
        self.assertEqual(key_str, '20151202100000', "Time for Z=1 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        if not SAVE_RESULTS:
            [os.remove(os.path.join(self.input_dir, file)) for file in os.listdir(self.input_dir) if not file.endswith('.tiff')]
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

class TestMRFGeneration_granule_webmerc(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.input_dir = os.path.join(testdata_path, 'obpg')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config5.xml")

        # Make source image dir
        make_dir_tree(self.input_dir, ignore_existing=True)

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/OBPG_webmerc2015336_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/OBPG_webmerc2015336_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/OBPG_webmerc2015336_.idx")
        self.output_zdb = os.path.join(self.staging_area, "output_dir/OBPG_webmerc2015336_.zdb")
        self.output_img = os.path.join(self.staging_area, "output_dir/OBPG_webmerc2015336_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp5.png")

        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Aqua_Chlorophyll_A.xml"), os.path.join(self.staging_area, 'working_dir'))
        
        if DEBUG:
            print("Generating global Web Mercator image with granules ")
        #pdb.set_trace()
        run_command("mrfgen -c " + test_config, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 1024 ' + self.output_mrf+':MRF:Z0 ' + self.output_img, show_output=DEBUG)
           
    def test_generate_mrf(self):
        '''
        This covers the following test cases:        
            Test auto creation of empty MRF
            Test using existing MRF with reprojection with z-level
            Test non-merging of input images with transparency
        '''
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 1222.9924523925781, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -1222.9924523925781, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img)
        if DEBUG:
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)        
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output composite image does not match")        
        
        img = None
        
        # Test ZDB
        if DEBUG:
            print("Checking " + self.output_zdb)
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print("Number of records: " + str(lid))
        self.assertEqual(lid, 1, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print(key_str)
        self.assertEqual(key_str, '20151202', "Time for Z=0 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        if not SAVE_RESULTS:
            [os.remove(os.path.join(self.input_dir, file)) for file in os.listdir(self.input_dir) if not file.endswith('.tiff')]
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

class TestMRFGeneration_tiled_z(unittest.TestCase):
    '''
    This covers the following test cases:
        Test using tiled images with Z-level        
        Test MRF generation with date and time
    '''
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config6.xml")

        # Make source image dir
        make_dir_tree(os.path.join(testdata_path, 'MORCR143LLDY'), ignore_existing=True)

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/MORCR143LLDY2016024000000_.mrf")
        self.output_pjg = os.path.join(self.staging_area, "output_dir/MORCR143LLDY2016024000000_.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/MORCR143LLDY2016024000000_.idx")
        self.output_zdb = os.path.join(self.staging_area, "output_dir/MORCR143LLDY2016024000000_.zdb")
        self.output_img = os.path.join(self.staging_area, "output_dir/MORCR143LLDY2016024000000_.jpg")
        self.compare_img = os.path.join(testdata_path, "test_comp6.jpg")

        #pdb.set_trace()
        #generate MRF
        run_command("mrfgen -c " + test_config, show_output=DEBUG)
        run_command('gdal_translate -of JPEG -outsize 1024 512 -projwin -10018754.1713946 5621521.48619207 -8015003.3371157 4300621.37204427 ' + self.output_mrf+':MRF:Z0 ' + self.output_img, show_output=DEBUG)
        
    def test_generate_mrf_tiled_z(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf+":MRF:Z0")
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 163840, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 163840, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(str(geotransform[1]), '244.59849047851563', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-244.59849047851563', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 10, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img)
        if DEBUG:
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)        
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output composite image does not match")        
        
        img = None
        
        # Test ZDB
        if DEBUG:
            print("Checking " + self.output_zdb)
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print("Number of records: " + str(lid))
        self.assertEqual(lid, 1, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print(key_str)
        self.assertEqual(key_str, 'test', "Time for Z=0 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_nonpaletted_colormap(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config7a = os.path.join(testdata_path, "mrfgen_test_config7a.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Combined_Flood.xml"), os.path.join(self.staging_area, 'working_dir'))

        # Copy empty output tile and input imagery
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))
        shutil.copytree(os.path.join(testdata_path, 'flood'), os.path.join(self.staging_area, 'flood'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp7a.png")

        # generate MRF
        #pdb.set_trace()
        cmd = "mrfgen -c " + test_config7a + " -s --email_logging_level WARN"
        run_command(cmd, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 2048 2048 ' + self.output_mrf + ' ' + self.output_img, show_output=DEBUG)
   
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ', ' ')),
                         'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')

        if DEBUG:
            print('Size: ', dataset.RasterXSize, 'x', dataset.RasterYSize, 'x', dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (', geotransform[0], ',', geotransform[3], ')')
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (', geotransform[1], ',', geotransform[5], ')')
        self.assertEqual(str(geotransform[1]), '1222.9924523925781', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-1222.9924523925781', "Pixel size does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")

        # Convert and compare MRF
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")

        img = None
        mrf = None

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

class TestMRFGeneration_email_notification(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        self.tmp_area = os.path.join(self.staging_area, 'tmp')
        test_config7a = os.path.join(testdata_path, "mrfgen_test_config7a.xml")
        test_config7b = os.path.join(testdata_path, "mrfgen_test_config7b.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Combined_Flood.xml"), os.path.join(self.staging_area, 'working_dir'))
        shutil.copy2(os.path.join(testdata_path, "colormaps/ColorMap_v1.2_Sample.xml"), os.path.join(self.staging_area, 'working_dir'))

        # Copy empty output tile and input imagery
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))
        shutil.copytree(os.path.join(testdata_path, 'flood'), os.path.join(self.staging_area, 'flood'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/Flood_webmerc2019268_.png")

        # Set up SMTP server
        server = DebuggingServerThread()
        server.start()
        old_stdout = sys.stdout
        sys.stdout = new_stdout = StringIO()

        # generate MRF
        cmd = "mrfgen -c " + test_config7a + " -s --email_logging_level WARN"
        run_command(cmd, show_output=DEBUG)

        # Take down SMTP server
        sys.stdout = old_stdout
        result = new_stdout.getvalue()
        server.stop()

        # Check result
#         self.assertTrue("Subject: [WARN/ONEARTH] triggered by mrfgen" in result)
#         self.assertTrue("From: earth@localhost.test" in result)
#         self.assertTrue("To: space@localhost.test" in result)
#         self.assertTrue("category: mrfgen" in result)
      
        # Set up SMTP server
        server = DebuggingServerThread()
        server.start()
        old_stdout = sys.stdout
        sys.stdout = new_stdout = StringIO()

        # generate MRF
        cmd = "mrfgen -c " + test_config7b + " -s --email_server=localhost:1025 --email_sender=earth@localhost.test --email_recipient=space@localhost.test --email_logging_level ERROR"
        run_command(cmd, show_output=DEBUG)

        # Take down SMTP server
        sys.stdout = old_stdout
        result2 = new_stdout.getvalue()
        server.stop()

        # Check result
        self.assertTrue("Subject: [ERROR/ONEARTH] triggered by mrfgen" in result2)
        self.assertTrue("From: earth@localhost.test" in result2)
        self.assertTrue("To: space@localhost.test" in result2)
        self.assertTrue("category: mrfgen" in result2)
   
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

        
class TestMRFGeneration_mixed_projections(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config8.xml")

        # Make source image dir
        input_dir = os.path.join(testdata_path, 'mixed_projections')
        make_dir_tree(os.path.join(input_dir), ignore_existing=True)
        
        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/sst2019231_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/sst2019231_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/sst2019231_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/sst2019231_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp8.png")
            
        # generate MRF
        print("mrfgen -c " + test_config)
        run_command("mrfgen -c " + test_config)
           
    def test_generate_mixed_projections(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 4, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 0.17578125, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.17578125, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

class TestMRFGeneration_antimeridian_crossing(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config9.xml")

        # Make source image dir
        input_dir = os.path.join(testdata_path, 'antimeridian_crossing')
        make_dir_tree(os.path.join(input_dir), ignore_existing=True)
        
        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/vns2019270_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/vns2019270_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/vns2019270_.idx")
        self.output_img = os.path.join(self.staging_area, "output_dir/vns2019270_.png")
        self.compare_img = os.path.join(testdata_path, "test_comp9.png")

        # generate MRF
        print("mrfgen -c " + test_config)
        run_command("mrfgen -c " + test_config)

    def test_generate_antimeridian_crossing(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        
        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print('Pixel Size: (',geotransform[1], ',',geotransform[5],')')
        self.assertEqual(float(geotransform[1]), 0.17578125, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.17578125, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print('Generated: ' + ' '.join(img.GetFileList()))
            print('Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount)
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_jpng(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        self.tmp_area = os.path.join(self.staging_area, 'tmp')
        test_config = os.path.join(testdata_path, "mrfgen_test_config10.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_JPNG2021100000000.mrf")
        self.output_pjp = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_JPNG2021100000000.pjp")
        self.output_idx = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_JPNG2021100000000.idx")
        self.output_img_png = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_JPNG2021100000000.png")
        self.output_img_jpg = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_JPNG2021100000000.jpg")
        self.compare_img_png = os.path.join(testdata_path, "test_comp10.png")
        self.compare_img_jpg = os.path.join(testdata_path, "test_comp10.jpg")

        # generate MRF
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)
        shutil.copy(self.output_pjp, self.output_pjp.replace(".pjp", ".ppg"))
        run_command('mrf_read.py --input ' + self.output_mrf + ' --output ' + self.output_img_png + ' --tilematrix 4 --tilecol 5 --tilerow 3', show_output=DEBUG)
        run_command('mrf_read.py --input ' + self.output_mrf + ' --output ' + self.output_img_jpg + ' --tilematrix 5 --tilecol 5 --tilerow 3', show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjp, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjp), "MRF PJP generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 10240, "Size does not match")
        self.assertEqual(dataset.RasterCount, 4, "Size does not match")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 6, "Overview count does not match")

        if DEBUG:
            print("Comparing: " + self.output_img_png + " to " + self.compare_img_png)
        self.assertTrue(filecmp.cmp(self.output_img_png, self.compare_img_png), "PNG output image does not match")

        if DEBUG:
            print("Comparing: " + self.output_img_jpg + " to " + self.compare_img_jpg)
        self.assertTrue(filecmp.cmp(self.output_img_jpg, self.compare_img_jpg), "JPEG output image does not match")

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)

class TestMRFGeneration_zenjpeg(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        self.tmp_area = os.path.join(self.staging_area, 'tmp')
        test_config = os.path.join(testdata_path, "mrfgen_test_config12.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_ZENJPEG2021100000000.mrf")
        self.output_pjp = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_ZENJPEG2021100000000.pjg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_ZENJPEG2021100000000.idx")
        self.output_img_png = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_ZENJPEG2021100000000.png")
        self.output_img_jpg = os.path.join(self.staging_area, "output_dir/GOES-East_B13_LL_v0_NRT_ZENJPEG2021100000000.jpg")
        self.compare_img_png = os.path.join(testdata_path, "test_comp12.png")
        self.compare_img_jpg = os.path.join(testdata_path, "test_comp12.jpg")

        # generate extra png input just to make sure mrfgen supports that as well (will get overwritten)
        run_command('gdal_translate -of PNG -co WORLDFILE=YES ' + testdata_path + '/jpng/GOES-East_B13_LL_v0_NRT_2021100_00:00.tiff ' + testdata_path + '/jpng/temp.png', show_output=DEBUG)

        # generate MRF
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf + ' ' + self.output_img_png, show_output=DEBUG)
        run_command('mrf_read.py --input ' + self.output_mrf + ' --output ' + self.output_img_jpg + ' --tilematrix 5 --tilecol 5 --tilerow 3', show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_pjp, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_pjp), "MRF PJP generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 10240, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Not an RGB image")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 6, "Overview count does not match")

        if DEBUG:
            print("Comparing: " + self.output_img_png + " to " + self.compare_img_png)
        self.assertTrue(filecmp.cmp(self.output_img_png, self.compare_img_png), "PNG output image does not match")

        if DEBUG:
            print("Comparing: " + self.output_img_jpg + " to " + self.compare_img_jpg)
        self.assertTrue(filecmp.cmp(self.output_img_jpg, self.compare_img_jpg), "JPEG output image does not match")

    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestMRFGeneration_defaultnocopy(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        self.tmp_area = os.path.join(self.staging_area, 'tmp')
        test_config = os.path.join(testdata_path, "mrfgen_test_config13.xml")

        # Make empty dirs for mrfgen output
        mrfgen_dirs = ('output_dir', 'working_dir', 'logfile_dir')
        [make_dir_tree(os.path.join(self.staging_area, path)) for path in mrfgen_dirs]

        # Copy empty output tile
        shutil.copytree(os.path.join(testdata_path, 'empty_tiles'), os.path.join(self.staging_area, 'empty_tiles'))

        self.output_mrf = os.path.join(self.staging_area, "output_dir/GEDI_MU2019108_.mrf")
        self.output_ppg = os.path.join(self.staging_area, "output_dir/GEDI_MU2019108_.ppg")
        self.output_idx = os.path.join(self.staging_area, "output_dir/GEDI_MU2019108_.idx")
        self.output_img_png = os.path.join(self.staging_area, "output_dir/GEDI_MU2019108_.png")
        self.compare_img_png = os.path.join(testdata_path, "test_comp13.png")

        # Use a large image to check for image artifacts
        run_command('gdal_translate -outsize 40960 19352 mrfgen_files/GEDI/GEDI_MU.tiff mrfgen_files/GEDI/GEDI_MU_resize.tiff', show_output=DEBUG)

        # generate MRF
        cmd = "mrfgen -c " + test_config
        run_command(cmd, show_output=DEBUG)
        run_command('mrf_read.py --input ' + self.output_mrf + ' --output ' + self.output_img_png + ' --tilematrix 1 --tilecol 0 --tilerow 0', show_output=DEBUG)

    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")

        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print('Driver:', str(driver.LongName))
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().
        if DEBUG:
            print('Files: {0}, {1}'.format(self.output_ppg, self.output_idx))
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")

        if DEBUG:
            print('Projection:', str(dataset.GetProjection()))
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')

        if DEBUG:
            print('Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount)
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Not a paletted image")

        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print('Origin: (',geotransform[0], ',',geotransform[3],')')
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")

        band = dataset.GetRasterBand(1)
        if DEBUG:
            print('Overviews:', band.GetOverviewCount())
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")

        if DEBUG:
            print("Comparing: " + self.output_img_png + " to " + self.compare_img_png)
        self.assertTrue(filecmp.cmp(self.output_img_png, self.compare_img_png), "PNG output image does not match")

    def tearDown(self):
        os.remove('mrfgen_files/GEDI/GEDI_MU_resize.tiff')
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


class TestRGBA2Pal(unittest.TestCase):

    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')  

        # Make source image dir
        input_dir = os.path.join(testdata_path, 'AIRS')
        make_dir_tree(os.path.join(input_dir), ignore_existing=True)
        
        # Make empty dir for output
        make_dir_tree(os.path.join(self.staging_area, 'output_dir'))

        self.output_img = os.path.join(self.staging_area, "output_dir/AIRS_L2_SST_A_LL_v6_NRT_2019344_indexed.png")
        self.compare_img = os.path.join(testdata_path, "test_comp11.png")
            
        # generate indexed PNG image
        cmd = "RGBApng2Palpng -v -lut=" + testdata_path + "/colormaps/AIRS_Temperature.xml -fill=0 -of=" + self.output_img + " " + input_dir + "/AIRS_L2_SST_A_LL_v6_NRT_2019344.png"
        print(cmd)
        run_command(cmd)

    def test_rgba2pal(self):
        # Check indexed PNG generation matches expected        
        if DEBUG:
            print("Comparing: " + self.output_img + " to " + self.compare_img)
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
    def tearDown(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.staging_area)
        else:
            print("Leaving test results in : " + self.staging_area)


if __name__ == '__main__':
    # Parse options before running tests
    available_tests = {
        'mrf_generation_paletted': TestMRFGeneration_paletted,
        'mrf_generation_paletted_nnb': TestMRFGeneration_paletted_nnb,
        'mrf_generation_nonpaletted': TestMRFGeneration_nonpaletted,
        'polar_mrf': TestMRFGeneration_polar,
        'polar_mrf_avg': TestMRFGeneration_polar_avg,
        'mercator_mrf': TestMRFGeneration_mercator,
        'mercator_mrf_avg': TestMRFGeneration_mercator_avg,
        'geo_granule': TestMRFGeneration_granule,
        'mercator_granule': TestMRFGeneration_granule_webmerc,
        'tiled_z': TestMRFGeneration_tiled_z,
        'mrf_generation_nonpaletted_colormap': TestMRFGeneration_nonpaletted_colormap,
        'email_notification': TestMRFGeneration_email_notification,
        'mixed_projections': TestMRFGeneration_mixed_projections,
        'antimeridian_crossing': TestMRFGeneration_antimeridian_crossing,
        'rgba2pal': TestRGBA2Pal,
        'jpng': TestMRFGeneration_jpng,
        'zenjpeg': TestMRFGeneration_zenjpeg,
        'defaultnocopy': TestMRFGeneration_defaultnocopy
    }
    test_help_text = 'Specify a specific test to run. Available tests: {0}'.format(list(available_tests.keys()))
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mrfgen_results.xml',
                      help='Specify XML output file (default is test_mrfgen_results.xml')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Display verbose debugging messages')
    parser.add_option('-t', '--test', action='append', type='choice', dest='test', choices=list(available_tests.keys()), help=test_help_text)
    parser.add_option('-s', '--save-results', action='store_true', dest='save_results', help='Save staging area results')
    (options, args) = parser.parse_args()
    DEBUG = options.debug
    SAVE_RESULTS = options.save_results

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    # If the user has selected individual tests to run, add them to the main suite.
    main_test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    if options.test:
        [main_test_suite.addTests(test_loader.loadTestsFromTestCase(available_tests[test])) for test in options.test]
    else:
        # Run all tests if none specified
        [main_test_suite.addTests(test_loader.loadTestsFromTestCase(test_case)) for test_case in list(available_tests.values())]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        test_runner = xmlrunner.XMLTestRunner(output=f)
        test_runner.run(main_test_suite)
