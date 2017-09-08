#!/bin/env python

# Copyright (c) 2002-2016, California Institute of Technology.
# All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
#      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
#      endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
from oe_test_utils import make_dir_tree, mrfgen_run_command as run_command

DEBUG = False

year = datetime.datetime.now().strftime('%Y')
doy = int(datetime.datetime.now().strftime('%j'))-1


class TestMRFGeneration(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config.xml")

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
        
        # download tile
#         image_url = "http://lance2.modaps.eosdis.nasa.gov/imagery/elements/MODIS/MYR4ODLOLLDY/%s/MYR4ODLOLLDY_global_%s%s_10km.png" % (year,year,doy)
#         world_url = "http://lance2.modaps.eosdis.nasa.gov/imagery/elements/MODIS/MYR4ODLOLLDY/%s/MYR4ODLOLLDY_global_%s%s_10km.pgw" % (year,year,doy)
#         image_name = self.input_dir + image_url.split('/')[-1]
#         world_name = self.input_dir + world_url.split('/')[-1]
#         print "Downloading", image_url
#         image_file=urllib.URLopener()
#         image_file.retrieve(image_url,image_name)
#         print "Downloading", world_url
#         world_file=urllib.URLopener()
#         world_file.retrieve(world_url,world_name)
            
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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_ppg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(geotransform[1], 0.087890625, "Pixel size does not match")
        self.assertEqual(geotransform[5], -0.087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 3, "Overview count does not match")

        if DEBUG:
            print 'Colors:', band.GetRasterColorTable().GetCount()
        self.assertEqual(band.GetRasterColorTable().GetCount(), 256, "Color count does not match")       
        for x in range(0, 255):
            color = band.GetRasterColorTable().GetColorEntry(x)
            if DEBUG:
                print color
            if x == 0:
                self.assertEqual(str(color), '(220, 220, 255, 0)', "Color does not match")
            if x == 1:
                self.assertEqual(str(color), '(0, 0, 0, 255)', "Color does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print 'Generated: ' + ' '.join(img.GetFileList())
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
    def tearDown(self):
        shutil.rmtree(self.staging_area)


class TestMRFGeneration_polar(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config2.xml")

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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_pjg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -4194304, "Origin does not match")
        self.assertEqual(geotransform[3], 4194304, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(int(geotransform[1]), 4096, "Pixel size does not match")
        self.assertEqual(int(geotransform[5]), -4096, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print 'Generated: ' + ' '.join(img.GetFileList())
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        filesize = os.path.getsize(self.output_img)
        print "Comparing file size: " + self.output_img + " " + str(filesize) + " bytes"
        self.assertEqual(filesize, 758400, "Output image does not match")
        
        img = None
        mrf = None
        
    def tearDown(self):
        shutil.rmtree(self.staging_area)
        

class TestMRFGeneration_mercator(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config = os.path.join(testdata_path, "mrfgen_test_config3.xml")

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
        # process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # for out in process.communicate():
        #     if DEBUG:
        #         print out
        
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        if DEBUG:
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_pjg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(str(geotransform[1]), '39135.7584766', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-39135.7584766', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        if DEBUG:
            print 'Generated: ' + ' '.join(img.GetFileList())
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        if DEBUG:
            print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None

    def tearDown(self):
        shutil.rmtree(self.staging_area)
        
class TestMRFGeneration_OBPG(unittest.TestCase):
    
    def setUp(self):
        testdata_path = os.path.join(os.getcwd(), 'mrfgen_files')
        self.input_dir = os.path.join(testdata_path, 'obpg')
        self.staging_area = os.path.join(os.getcwd(), 'mrfgen_test_data')
        test_config4a = os.path.join(testdata_path, "mrfgen_test_config4a.xml")
        test_config4b = os.path.join(testdata_path, "mrfgen_test_config4b.xml")
        test_config4c = os.path.join(testdata_path, "mrfgen_test_config4c.xml")

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
        self.compare_img_b = os.path.join(testdata_path, "test_comp4b.png")
        self.compare_img_c = os.path.join(testdata_path, "test_comp4c.png")
        
        # download tiles
        # Note that there are weird hang-up issues running these processes in shell mode.
        #pdb.set_trace()
#         quiet = '' if DEBUG else '-q'
#         cmd = 'wget -r ' + quiet + ' --no-parent --reject "index.html*" --cut-dirs=7 -nH -nc -T 60 -P ' + self.input_dir + ' https://oceancolor.gsfc.nasa.gov/BRS/MODISA/L2FRBRS/OC/LAC/2015/336/'
#         run_command(cmd, show_output=DEBUG)

        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Aqua_Chlorophyll_A.xml"), os.path.join(self.staging_area, 'working_dir'))
        if DEBUG:
            print "Generating empty MRF with No Copy option"
        # process = subprocess.call(['mrfgen', '-c', test_config4a])
        #pdb.set_trace()
        run_command("mrfgen -c " + test_config4a, show_output=DEBUG)
        if DEBUG:
            print "Generating global composite using granules with existing NoCopy MRF at z=0"
        # process = subprocess.call(['mrfgen', '-c', test_config4b])
        run_command("mrfgen -c " + test_config4b, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf+':MRF:Z0 ' + self.output_img_b, show_output=DEBUG)
        if DEBUG:
            print "Generating global image with single granules with existing NoCopy MRF at z=1"
        run_command("mrfgen -c " + test_config4c, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 512 ' + self.output_mrf+':MRF:Z1 ' + self.output_img_c, show_output=DEBUG)
           
    def test_generate_mrf_obpg(self):
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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_ppg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img_a, mrf, 0 )
        
        if DEBUG:
            print 'Generated: ' + ' '.join(img.GetFileList())
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img_b)
        if DEBUG:
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount        
            print "Comparing: " + self.output_img_b + " to " + self.compare_img_b
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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 40960, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 20480, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(float(geotransform[1]), 0.0087890625, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -0.0087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Convert and compare MRF
        img = gdal.Open(self.output_img_c)
        if DEBUG:
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount        
            print "Comparing: " + self.output_img_c + " to " + self.compare_img_c
        self.assertTrue(filecmp.cmp(self.output_img_c, self.compare_img_c), "Output granule image does not match")
        
        img = None
        
        # Test ZDB
        if DEBUG:
            print "Checking " + self.output_zdb
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print "Number of records: " + str(lid)
        self.assertEqual(lid, 2, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print key_str
        self.assertEqual(key_str, '20151202', "Time for Z=0 does not match in ZDB")
        cur.execute("SELECT key_str FROM ZINDEX where z=1;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print key_str
        self.assertEqual(key_str, '20151202000000', "Time for Z=1 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        [os.remove(os.path.join(self.input_dir, file)) for file in os.listdir(self.input_dir) if not file.endswith('.tiff')]
        shutil.rmtree(self.staging_area)
        
class TestMRFGeneration_OBPG_webmerc(unittest.TestCase):
    
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

        # download tiles
        #pdb.set_trace()
#         run_command('wget -r --no-parent --reject "index.html*" --cut-dirs=7 -nH -nc -q -T 60 -P ' + self.input_dir + ' https://oceancolor.gsfc.nasa.gov/BRS/MODISA/L2FRBRS/OC/LAC/2015/336/', show_output=DEBUG)
            
        # create copy of colormap
        shutil.copy2(os.path.join(testdata_path, "colormaps/MODIS_Aqua_Chlorophyll_A.xml"), os.path.join(self.staging_area, 'working_dir'))
        
        if DEBUG:
            print "Generating global Web Mercator image with granules "
        #pdb.set_trace()
        run_command("mrfgen -c " + test_config, show_output=DEBUG)
        run_command('gdal_translate -of PNG -outsize 1024 1024 ' + self.output_mrf+':MRF:Z0 ' + self.output_img, show_output=DEBUG)
           
    def test_generate_mrf_obpg_webmerc(self):
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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_ppg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 32768, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Number of bands do not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(float(geotransform[1]), 1222.992452392578116, "Pixel size does not match")
        self.assertEqual(float(geotransform[5]), -1222.992452392578116, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 7, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img)
        if DEBUG:
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount        
            print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output composite image does not match")        
        
        img = None
        
        # Test ZDB
        if DEBUG:
            print "Checking " + self.output_zdb
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print "Number of records: " + str(lid)
        self.assertEqual(lid, 1, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print key_str
        self.assertEqual(key_str, '20151202', "Time for Z=0 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        [os.remove(os.path.join(self.input_dir, file)) for file in os.listdir(self.input_dir) if not file.endswith('.tiff')]
        shutil.rmtree(self.staging_area)

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
        # Get sample input tiles (if they haven't been created yet)
        if not os.path.isfile(os.path.join(testdata_path, 'MORCR143LLDY/MODIS_Terra_CorrectedReflectance_TrueColor_0.jpg')):
            run_command('gdal_translate -of JPEG -co WORLDFILE=YES -outsize 512 512 -projwin -90 45 -81 36 \'<GDAL_WMS><Service name="TMS"><ServerUrl>http://map1.vis.earthdata.nasa.gov/wmts-geo/MODIS_Terra_CorrectedReflectance_TrueColor/default/2016-01-24/EPSG4326_250m/${z}/${y}/${x}.jpg</ServerUrl></Service><DataWindow><UpperLeftX>-180.0</UpperLeftX><UpperLeftY>90</UpperLeftY><LowerRightX>396.0</LowerRightX><LowerRightY>-198</LowerRightY><TileLevel>8</TileLevel><TileCountX>2</TileCountX><TileCountY>1</TileCountY><YOrigin>top</YOrigin></DataWindow><Projection>EPSG:4326</Projection><BlockSizeX>512</BlockSizeX><BlockSizeY>512</BlockSizeY><BandsCount>3</BandsCount></GDAL_WMS>\' ' + os.path.join(testdata_path, 'MORCR143LLDY/MODIS_Terra_CorrectedReflectance_TrueColor_0.jpg'), show_output=DEBUG)
        if not os.path.isfile(os.path.join(testdata_path, 'MORCR143LLDY/MODIS_Terra_CorrectedReflectance_TrueColor_1.jpg')):
            run_command('gdal_translate -of JPEG -co WORLDFILE=YES -outsize 512 512 -projwin -81 45 -72 36 \'<GDAL_WMS><Service name="TMS"><ServerUrl>http://map1.vis.earthdata.nasa.gov/wmts-geo/MODIS_Terra_CorrectedReflectance_TrueColor/default/2016-01-24/EPSG4326_250m/${z}/${y}/${x}.jpg</ServerUrl></Service><DataWindow><UpperLeftX>-180.0</UpperLeftX><UpperLeftY>90</UpperLeftY><LowerRightX>396.0</LowerRightX><LowerRightY>-198</LowerRightY><TileLevel>8</TileLevel><TileCountX>2</TileCountX><TileCountY>1</TileCountY><YOrigin>top</YOrigin></DataWindow><Projection>EPSG:4326</Projection><BlockSizeX>512</BlockSizeX><BlockSizeY>512</BlockSizeY><BandsCount>3</BandsCount></GDAL_WMS>\' ' + os.path.join(testdata_path, 'MORCR143LLDY/MODIS_Terra_CorrectedReflectance_TrueColor_1.jpg'), show_output=DEBUG)

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
            print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        if DEBUG:
            print 'Files: {0}, {1}'.format(self.output_pjg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        self.assertTrue(os.path.isfile(self.output_zdb), "MRF ZDB generation failed")
        
        if DEBUG:
            print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection().replace('  ',' ')),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        if DEBUG:
            print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 163840, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 163840, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        if DEBUG:
            print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        if DEBUG:
            print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(str(geotransform[1]), '244.598490479', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-244.598490479', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        if DEBUG:
            print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 10, "Overview count does not match")
        
        # Compare MRF
        img = gdal.Open(self.output_img)
        if DEBUG:
            print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount        
            print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output composite image does not match")        
        
        img = None
        
        # Test ZDB
        if DEBUG:
            print "Checking " + self.output_zdb
        con = sqlite3.connect(self.output_zdb)
        cur = con.cursor()
        # Check for existing key
        cur.execute("SELECT COUNT(*) FROM ZINDEX;")
        lid = int(cur.fetchone()[0])
        if DEBUG:
            print "Number of records: " + str(lid)
        self.assertEqual(lid, 1, "Number of records not matching in ZDB")
        # Check for matching keys
        cur.execute("SELECT key_str FROM ZINDEX where z=0;")
        key_str = cur.fetchone()[0]
        if DEBUG:
            print key_str
        self.assertEqual(key_str, 'test', "Time for Z=0 does not match in ZDB")
        if con:
            con.close()

    def tearDown(self):
        shutil.rmtree(self.staging_area)

if __name__ == '__main__':
    # Parse options before running tests
    available_tests = {'mrf_generation': TestMRFGeneration,
                       'polar_mrf': TestMRFGeneration_polar,
                       'mercator_mrf': TestMRFGeneration_mercator,
                       'geo_granule': TestMRFGeneration_OBPG,
                       'mercator_granule': TestMRFGeneration_OBPG_webmerc,
                       'tiled_z': TestMRFGeneration_tiled_z
                       }
    test_help_text = 'Specify a specific test to run. Available tests: {0}'.format(available_tests.keys())
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mrfgen_results.xml',
                      help='Specify XML output file (default is test_mrfgen_results.xml')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Display verbose debugging messages')
    parser.add_option('-t', '--test', action='append', type='choice', dest='test', choices=available_tests.keys(), help=test_help_text)
    (options, args) = parser.parse_args()
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    # If the user has selected individual tests to run, add them to the main suite.
    main_test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    if options.test:
        [main_test_suite.addTests(test_loader.loadTestsFromTestCase(available_tests[test])) for test in options.test]
    else:
        # Run all tests if none specified
        [main_test_suite.addTests(test_loader.loadTestsFromTestCase(test_case)) for test_case in available_tests.values()]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        test_runner = xmlrunner.XMLTestRunner(output=f)
        test_runner.run(main_test_suite)
