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
import unittest
import subprocess
import filecmp
import urllib
import shutil
import datetime
from osgeo import gdal

year = datetime.datetime.now().strftime('%Y')
doy = int(datetime.datetime.now().strftime('%j'))-1

def run_command(cmd):
    """
    Runs the provided command on the terminal.
    Arguments:
        cmd -- the command to be executed.
    """
    print '\nRunning command: ' + cmd
    process = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    process.wait()
    for output in process.stdout:
        print output.strip()
    for error in process.stderr:
        print error.strip()
        raise Exception(error.strip())
                    

class TestMRFGeneration(unittest.TestCase):
    
    def setUp(self):
        self.dirpath = os.path.dirname(__file__)
        self.test_config = self.dirpath + "/test/mrfgen_test_config.xml"
        self.input_dir = self.dirpath + "/test/input_dir/"
        self.output_dir = self.dirpath + "/test/output_dir"
        self.working_dir = self.dirpath + "/test/working_dir"
        self.logfile_dir = self.dirpath + "/test/logfile_dir"
        self.output_mrf = self.output_dir+ "/MYR4ODLOLLDY2014277_.mrf"
        self.output_ppg = self.output_dir+ "/MYR4ODLOLLDY2014277_.ppg"
        self.output_idx = self.output_dir+ "/MYR4ODLOLLDY2014277_.idx"
        self.output_img = self.output_dir+ "/MYR4ODLOLLDY2014277_.png"
        self.compare_img = self.dirpath + "/test/test_comp1.png"
        if not os.path.exists(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        if not os.path.exists(self.logfile_dir):
            os.makedirs(self.logfile_dir)
        
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
        run_command("python mrfgen.py -c " + self.test_config)
        
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        print 'Files: {0}, {1}'.format(self.output_ppg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_ppg), "MRF PPG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 2048, "Size does not match")
        self.assertEqual(dataset.RasterCount, 1, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -180.0, "Origin does not match")
        self.assertEqual(geotransform[3], 90.0, "Origin does not match")
        print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(geotransform[1], 0.087890625, "Pixel size does not match")
        self.assertEqual(geotransform[5], -0.087890625, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 3, "Overview count does not match")

        print 'Colors:', band.GetRasterColorTable().GetCount()
        self.assertEqual(band.GetRasterColorTable().GetCount(), 256, "Color count does not match")       
        for x in range(0, 255):
            color = band.GetRasterColorTable().GetColorEntry(x)
            print color
            if x == 0:
                self.assertEqual(str(color), '(220, 220, 255, 0)', "Color does not match")
            if x == 1:
                self.assertEqual(str(color), '(0, 0, 0, 255)', "Color does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        print 'Generated: ' + ' '.join(img.GetFileList())
        print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
        print "\n***Test Case Passed***\n"
        
    def tearDown(self):
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.logfile_dir)
        shutil.rmtree(self.output_dir)


class TestMRFGeneration_polar(unittest.TestCase):
    
    def setUp(self):
        self.dirpath = os.path.dirname(__file__)
        self.test_config = self.dirpath + "/test/mrfgen_test_config2.xml"
        self.input_dir = self.dirpath + "/test/input_dir/"
        self.output_dir = self.dirpath + "/test/output_dir"
        self.working_dir = self.dirpath + "/test/working_dir"
        self.logfile_dir = self.dirpath + "/test/logfile_dir"
        self.output_mrf = self.output_dir+ "/MORCR143ARDY2014203_.mrf"
        self.output_pjg = self.output_dir+ "/MORCR143ARDY2014203_.pjg"
        self.output_idx = self.output_dir+ "/MORCR143ARDY2014203_.idx"
        self.output_img = self.output_dir+ "/MORCR143ARDY2014203_.jpg"
        self.compare_img = self.dirpath + "/test/test_comp2.jpg"
        if not os.path.exists(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        if not os.path.exists(self.logfile_dir):
            os.makedirs(self.logfile_dir)
        
        # download tiles
        for r in range(0,8):
            for c in range(0,8):
                try:
                    image_url = "http://lance2.modaps.eosdis.nasa.gov/imagery/subsets/Arctic_r%02dc%02d/%s%03d/Arctic_r%02dc%02d.%s%03d.aqua.250m.jpg" % (r,c,year,doy,r,c,year,doy)
                    world_url = "http://lance2.modaps.eosdis.nasa.gov/imagery/subsets/Arctic_r%02dc%02d/%s%03d/Arctic_r%02dc%02d.%s%03d.aqua.250m.jgw" % (r,c,year,doy,r,c,year,doy)
                    image_name = self.input_dir + image_url.split('/')[-1]
                    world_name = self.input_dir + world_url.split('/')[-1]
                    print "Downloading", image_url
                    image_file=urllib.URLopener()
                    image_file.retrieve(image_url,image_name)
                    print "Downloading", world_url
                    world_file=urllib.URLopener()
                    world_file.retrieve(world_url,world_name)
                except Exception,e:
                    print str(e)
            
        #generate MRF
        run_command("python mrfgen.py -c " + self.test_config)
           
    def test_generate_mrf_polar(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")

        # This part of the test previously looked for a triplet of files in dataset.GetFileList().         
        print 'Files: {0}, {1}'.format(self.output_pjg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 4096, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -4194304, "Origin does not match")
        self.assertEqual(geotransform[3], 4194304, "Origin does not match")
        print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(int(geotransform[1]), 2048, "Pixel size does not match")
        self.assertEqual(int(geotransform[5]), -2048, "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 3, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("JPEG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        print 'Generated: ' + ' '.join(img.GetFileList())
        print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
#         filesize = os.path.getsize(self.output_img)
#         print "Comparing file size: " + self.output_img + " " + str(filesize) + " bytes"
#         self.assertEqual(filesize, 3891603, "Output image does not match")
        
        img = None
        mrf = None
        
        print "\n***Test Case Passed***\n"
        
    def tearDown(self):
        shutil.rmtree(self.input_dir)
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.logfile_dir)
        shutil.rmtree(self.output_dir)
        
class TestMRFGeneration_mercator(unittest.TestCase):
    
    def setUp(self):
        self.dirpath = os.path.dirname(__file__)
        self.test_config = self.dirpath + "/test/mrfgen_test_config3.xml"
        self.output_dir = self.dirpath + "/test/output_dir"
        self.working_dir = self.dirpath + "/test/working_dir"
        self.logfile_dir = self.dirpath + "/test/logfile_dir"
        self.output_mrf = self.output_dir+ "/BlueMarbleSmall2014237_.mrf"
        self.output_pjg = self.output_dir+ "/BlueMarbleSmall2014237_.pjg"
        self.output_idx = self.output_dir+ "/BlueMarbleSmall2014237_.idx"
        self.output_img = self.output_dir+ "/BlueMarbleSmall2014237_.png"
        self.compare_img = self.dirpath + "/test/test_comp3.png"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        if not os.path.exists(self.logfile_dir):
            os.makedirs(self.logfile_dir)
            
        #generate MRF
        run_command("python mrfgen.py -c " + self.test_config)
        
    def test_generate_mrf(self):
        # Check MRF generation succeeded
        self.assertTrue(os.path.isfile(self.output_mrf), "MRF generation failed")
        
        # Read MRF
        dataset = gdal.Open(self.output_mrf)
        driver = dataset.GetDriver()
        print 'Driver:', str(driver.LongName)
        self.assertEqual(str(driver.LongName), "Meta Raster Format", "Driver is not Meta Raster Format")
        
        # This part of the test previously looked for a triplet of files in dataset.GetFileList(). 
        print 'Files: {0}, {1}'.format(self.output_pjg, self.output_idx)
        self.assertTrue(os.path.isfile(self.output_pjg), "MRF PJG generation failed")
        self.assertTrue(os.path.isfile(self.output_idx), "MRF IDX generation failed")
        
        print 'Projection:', str(dataset.GetProjection())
        self.assertEqual(str(dataset.GetProjection()),'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"],AUTHORITY["EPSG","3857"]]')
        
        print 'Size: ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount
        self.assertEqual(dataset.RasterXSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterYSize, 1024, "Size does not match")
        self.assertEqual(dataset.RasterCount, 3, "Size does not match")
        
        geotransform = dataset.GetGeoTransform()
        print 'Origin: (',geotransform[0], ',',geotransform[3],')'
        self.assertEqual(geotransform[0], -20037508.34, "Origin does not match")
        self.assertEqual(geotransform[3], 20037508.34, "Origin does not match")
        print 'Pixel Size: (',geotransform[1], ',',geotransform[5],')'
        self.assertEqual(str(geotransform[1]), '39135.7584766', "Pixel size does not match")
        self.assertEqual(str(geotransform[5]), '-39135.7584766', "Pixel size does not match")
        
        band = dataset.GetRasterBand(1)
        print 'Overviews:', band.GetOverviewCount()
        self.assertEqual(band.GetOverviewCount(), 2, "Overview count does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        img = driver.CreateCopy(self.output_img, mrf, 0 )
        
        print 'Generated: ' + ' '.join(img.GetFileList())
        print 'Size: ',img.RasterXSize,'x',img.RasterYSize, 'x',img.RasterCount
        self.assertEqual(img.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(img.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(img.RasterCount, dataset.RasterCount, "Size does not match")
        
        print "Comparing: " + self.output_img + " to " + self.compare_img
        self.assertTrue(filecmp.cmp(self.output_img, self.compare_img), "Output image does not match")
        
        img = None
        mrf = None
        
        print "\n***Test Case Passed***\n"
        
    def tearDown(self):
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.logfile_dir)
        shutil.rmtree(self.output_dir)

if __name__ == '__main__':
    unittest.main()
