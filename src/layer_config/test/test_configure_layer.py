#!/bin/env python

#
# Tests for oe_configure_layer.py
#

import os
import unittest
import subprocess
import filecmp
from shutil import copyfile, rmtree

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
    return process.returncode
                    

class TestLayerConfig(unittest.TestCase):
    
    def setUp(self):
        if os.environ.has_key('LCDIR') == False:
            self.lcdir = os.path.abspath(os.path.dirname(__file__) + '/..')
        else:
            self.lcdir = os.environ['LCDIR']
        self.legend_v = self.lcdir + "/test/MODIS_Aqua_Aerosol_V.svg"
        self.legend_h = self.lcdir + "/test/MODIS_Aqua_Aerosol_H.svg"
        self.cachedir = '/usr/share/onearth/demo/data/EPSG4326/'
        # Set up dummy data files
        if not os.path.exists(self.cachedir + "MODIS_Aqua_Aerosol"):
            os.makedirs(self.cachedir + "MODIS_Aqua_Aerosol")
        if not os.path.exists(self.cachedir + 'MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol2014364_.mrf'):
            copyfile('MODIS_Aqua_Aerosol2014364_.mrf', self.cachedir + 'MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol2014364_.mrf')

    def test_layer_config_default(self):
        #Run layer config
        layer_config_file = self.lcdir + "/test/layer_configuration_test1.xml"
        errors = run_command("oe_configure_layer -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
   
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        self.assertTrue(os.path.isfile(self.cachedir + "cache_all_wmts.config"), "cache_all_wmts.config does not exist")
        self.assertTrue(os.path.isfile("/usr/share/onearth/demo/wmts-geo/getCapabilities.xml"), "WMTS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile(self.cachedir + "MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol2014364_.mrf"), "MODIS_Aqua_Aerosol2014364_.mrf does not exist")
        self.assertTrue(os.path.isfile("/usr/share/onearth/layer_config/wmts/EPSG4326/MODIS_Aqua_Aerosol2014364_.xml"), "MODIS_Aqua_Aerosol2014364_.xml does not exist in WMTS staging area")

        self.assertTrue(os.path.isfile(self.cachedir + "cache_all_twms.config"), "cache_all_twms.config does not exist")
        self.assertTrue(os.path.isfile("/usr/share/onearth/demo/twms-geo/.lib/getCapabilities.xml"), "TWMS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile("/usr/share/onearth/demo/twms-geo/.lib/getTileService.xml"), "TWMS getTileService.xml does not exist")
        self.assertTrue(os.path.isfile(self.cachedir + "MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol2014364_.mrf"), "MODIS_Aqua_Aerosol2014364_.mrf does not exist")
        self.assertTrue(os.path.isfile("/usr/share/onearth/layer_config/twms/EPSG4326/MODIS_Aqua_Aerosol2014364__gc.xml"), "MODIS_Aqua_Aerosol2014364_gc.xml does not exist in TWMS staging area")
        self.assertTrue(os.path.isfile("/usr/share/onearth/layer_config/twms/EPSG4326/MODIS_Aqua_Aerosol2014364__gts.xml"), "MODIS_Aqua_Aerosol2014364_gts.mrf does not exist in TWMS staging area")

        
        contains_layer = False
        getCapabilities = open("/usr/share/onearth/demo/wmts-geo/getCapabilities.xml", 'r')
        for line in getCapabilities.readlines():
            if "<ows:Identifier>MODIS_Aqua_Aerosol</ows:Identifier>" in line:
                print "Layer found in WMTS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "WMTS GetCapabilities does not contain layer")
        
        contains_layer = False
        contains_zleveldata = False
        cacheConfig = open("/usr/share/onearth/demo/data/EPSG4326/cache_all_wmts.config", 'r')
        for line in cacheConfig.readlines():
            if "SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=MODIS_Aqua_Aerosol&STYLE=(default)?&TILEMATRIXSET=EPSG4326_2km&TILEMATRIX=[0-9]*&TILEROW=[0-9]*&TILECOL=[0-9]*&FORMAT=image%2Fpng" in line:
                print "Layer found in WMTS cache configuration"
                contains_layer = True
        cacheConfig.close()
        self.assertTrue(contains_layer, "WMTS cache configuration does not contain layer")
        
        contains_layer = False
        getCapabilities = open("/usr/share/onearth/demo/twms-geo/.lib/getCapabilities.xml", 'r')
        for line in getCapabilities.readlines():
            if "<Name>MODIS_Aqua_Aerosol</Name>" in line:
                print "Layer found in TWMS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "TWMS GetCapabilities does not contain layer")
        
        contains_layer = False
        getTileService = open("/usr/share/onearth/demo/twms-geo/.lib/getTileService.xml", 'r')
        for line in getTileService.readlines():
            if "<Name>MODIS_Aqua_Aerosol tileset</Name>" in line:
                print "Layer found in TWMS GetTileService"
                contains_layer = True
        getTileService.close()
        self.assertTrue(contains_layer, "GetTileService does not contain layer")
        
        contains_layer = False
        cacheConfig = open("/usr/share/onearth/demo/data/EPSG4326/cache_all_twms.config", 'r')
        for line in cacheConfig.readlines():
            if "MODIS_Aqua_Aerosol/YYYY/MODIS_Aqua_AerosolTTTTTTT_.ppg" in line:
                print "Layer found in TWMS cache configuration"
                contains_layer = True
        cacheConfig.close()
        self.assertTrue(contains_layer, "TWMS cache configuration does not contain layer")

        # check empty tile
        empty_tile = os.path.getsize(self.lcdir + "/test/empty_tile.png")
        self.assertEqual(empty_tile, 1382, "Empty tile does not match expected")
        
        print "\n***Test Case Passed***\n"
        
    def test_layer_config_legends(self):
        legend_location = "/usr/share/onearth/demo/legends/" #default    
        colormap_location = "/usr/share/onearth/demo/colormaps" #default

        # Get environment legend and colormap locations
        with open(self.lcdir + "/conf/environment_geographic.xml", 'r') as env:
            for line in env.readlines():
                if "<LegendLocation>" in line:
                    legend_location = line.replace('<LegendLocation>','').replace('</LegendLocation>','').strip()
                if "<ColorMapLocation>" in line:
                    colormap_location = line.replace('<ColorMapLocation>','').replace('</ColorMapLocation>','').strip()
            print "\nLegend Location: " + legend_location 
            print "\nColormap Location: " + colormap_location 

        # create legend and colormap dirs if they doesn't exist
        if not os.path.exists(legend_location):
            os.makedirs(legend_location)
        if not os.path.exists(colormap_location):
            os.makedirs(colormap_location)
        # remove legends and colormap if they exist
        try:
            os.remove(legend_location + "/MODIS_Aqua_Aerosol_V.svg")
            os.remove(legend_location + "/MODIS_Aqua_Aerosol_H.svg")
        except OSError:
            print "Legends do not yet exist"
        try:
            os.remove(colormap_location + "/MODIS_Aqua_Aerosol-GIBS.xml")
        except OSError:
            print "Colormap doesn't exist"
        
        # copy colormap to colormaps dir
        copyfile(self.lcdir + "/test/MODIS_Aqua_Aerosol-GIBS.xml", colormap_location + "/MODIS_Aqua_Aerosol-GIBS.xml")

        #Run layer config
        layer_config_file = self.lcdir + "/test/layer_configuration_test1.xml"
        errors = run_command("oe_configure_layer -g -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
        
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_V.svg to " + self.legend_v
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_V.svg", self.legend_v), "Legend does not match expected")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_H.svg to " + self.legend_h
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_H.svg", self.legend_h), "Legend does not match expected")
        
    def tearDown(self):
        os.remove(self.cachedir + "MODIS_Aqua_Aerosol/MODIS_Aqua_Aerosol2014364_.mrf")
        rmtree(self.cachedir + "MODIS_Aqua_Aerosol/")
        os.remove("/usr/share/onearth/layer_config/wmts/EPSG4326/MODIS_Aqua_Aerosol2014364_.xml")
        os.remove("/usr/share/onearth/layer_config/wmts/EPSG4326/MODIS_Aqua_Aerosol2014364_.mrf")
        os.remove("/usr/share/onearth/layer_config/twms/EPSG4326/MODIS_Aqua_Aerosol2014364__gc.xml")
        os.remove("/usr/share/onearth/layer_config/twms/EPSG4326/MODIS_Aqua_Aerosol2014364__gts.xml")
        os.remove(self.lcdir + "/test/empty_tile.png")

if __name__ == '__main__':
    unittest.main()
