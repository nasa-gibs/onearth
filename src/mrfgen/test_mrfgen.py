#!/bin/env python

#
# Tests for mrfgen.py
#

import os
import unittest
import subprocess
import filecmp
from osgeo import gdal

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
        self.output_dir = self.dirpath + "/test/output_dir"
        self.working_dir = self.dirpath + "/test/working_dir"
        self.logfile_dir = self.dirpath + "/test/logfile_dir"
        self.output_mrf = self.output_dir+ "/sst2014203_.mrf"
        self.output_png = self.output_dir+ "/sst2014203_.png"
        self.compare_png = self.dirpath + "/test/test_comp1.png"
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
        
        print 'Files:', ' '.join(dataset.GetFileList())
        self.assertEqual(len(dataset.GetFileList()),3,"MRF does not contain triplet")
        
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
                self.assertEqual(str(color), '(0, 0, 0, 0)', "Color does not match")
            if x == 1:
                self.assertEqual(str(color), '(43, 0, 26, 255)', "Color does not match")
        
        # Convert and compare MRF
        mrf = gdal.Open(self.output_mrf)
        driver = gdal.GetDriverByName("PNG")       
        png = driver.CreateCopy(self.output_png, mrf, 0 )
        
        print 'Generated: ' + ' '.join(png.GetFileList())
        print 'Size: ',png.RasterXSize,'x',png.RasterYSize, 'x',png.RasterCount
        self.assertEqual(png.RasterXSize, dataset.RasterXSize, "Size does not match")
        self.assertEqual(png.RasterYSize, dataset.RasterYSize, "Size does not match")
        self.assertEqual(png.RasterCount, dataset.RasterCount, "Size does not match")
        
        print "Comparing: " + self.output_png + " to " + self.compare_png
        self.assertTrue(filecmp.cmp(self.output_png, self.compare_png), "Output PNG does not match")
        
        png = None
        mrf = None

if __name__ == '__main__':
    unittest.main()