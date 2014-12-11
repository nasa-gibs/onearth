#!/bin/env python

#
# Tests for oe_configure_layer.py
#

import os
import unittest
import subprocess
import filecmp

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
        
    def test_layer_config_default(self):
        #Run layer config
        layer_config_file = self.lcdir + "/test/layer_configuration_test1.xml"
        errors = run_command("python " + self.lcdir + "/bin/oe_configure_layer.py -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
        
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        self.assertTrue(os.path.isfile(self.lcdir + "/wmts/EPSG4326/cache_wmts.config"), "cache_wmts.config does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/wmts/EPSG4326/getCapabilities.xml"), "WMTS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.mrf"), "MODIS_Aqua_AerosolTTTTTTT_.mrf does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.xml"), "MODIS_Aqua_AerosolTTTTTTT_.xml does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/cache.config"), "cache.config does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/getCapabilities.xml"), "TWMS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/getTileService.xml"), "TWMS getTileService.xml does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.mrf"), "MODIS_Aqua_AerosolTTTTTTT_.mrf does not exist")
        
        contains_layer = False
        getCapabilities = open(self.lcdir + "/wmts/EPSG4326/getCapabilities.xml", 'r')
        for line in getCapabilities.readlines():
            if "<ows:Identifier>MODIS_Aqua_Aerosol</ows:Identifier>" in line:
                print "Layer found in WMTS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "WMTS GetCapabilities does not contain layer")
        
        contains_layer = False
        cacheConfig = open(self.lcdir + "/wmts/EPSG4326/cache_wmts.config", 'r')
        for line in cacheConfig.readlines():
            if "SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=MODIS_Aqua_Aerosol&STYLE=(default)?&TILEMATRIXSET=EPSG4326_2km&TILEMATRIX=[0-9]*&TILEROW=[0-9]*&TILECOL=[0-9]*&FORMAT=image%2Fpng" in line:
                print "Layer found in WMTS cache configuration"
                contains_layer = True
        cacheConfig.close()
        self.assertTrue(contains_layer, "WMTS cache configuration does not contain layer")
        
        contains_layer = False
        getCapabilities = open(self.lcdir + "/twms/EPSG4326/getCapabilities.xml", 'r')
        for line in getCapabilities.readlines():
            if "<Name>MODIS_Aqua_Aerosol</Name>" in line:
                print "Layer found in TWMS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "TWMS GetCapabilities does not contain layer")
        
        contains_layer = False
        getTileService = open(self.lcdir + "/twms/EPSG4326/getTileService.xml", 'r')
        for line in getTileService.readlines():
            if "<Name>MODIS_Aqua_Aerosol</Name>" in line:
                print "Layer found in TWMS GetTileService"
                contains_layer = True
        getTileService.close()
        self.assertTrue(contains_layer, "GetTileService does not contain layer")
        
        contains_layer = False
        cacheConfig = open(self.lcdir + "/twms/EPSG4326/cache.config", 'r')
        for line in cacheConfig.readlines():
            if "MODIS_Terra_Chlorophyll_A/YYYY/MODIS_Terra_Chlorophyll_ATTTTTTT_.ppg" in line:
                print "Layer found in TWMS cache configuration"
                contains_layer = True
        cacheConfig.close()
        self.assertTrue(contains_layer, "TWMS cache configuration does not contain layer")
        
        # check empty tile
        empty_tile = os.path.getsize(self.lcdir + "/test/empty_tile.png")
        self.assertEqual(empty_tile, 1108, "Empty tile does not match expected")
        
        print "\n***Test Case Passed***\n"
        
    def test_layer_config_legends(self):
        #Get legend location
        environment = open(self.lcdir + "/conf/environment_geographic.xml", 'r')
        legend_location = "/usr/share/onearth/demo/legends/" #default
        for line in environment.readlines():
            if "<LegendLocation>" in line:
                legend_location = line.replace('<LegendLocation>','').replace('</LegendLocation>','').strip()
        print "\nLegend Location: " + legend_location 
        # remove legends if exist
        try:
            os.remove(legend_location + "/MODIS_Aqua_Aerosol_V.svg")
            os.remove(legend_location + "/MODIS_Aqua_Aerosol_H.svg")
        except OSError:
            print "Legends do not yet exist"
        
        #Run layer config
        layer_config_file = self.lcdir + "/test/layer_configuration_test1.xml"
        errors = run_command("python " + self.lcdir + "/bin/oe_configure_layer.py -g -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
        
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_V.svg to" + self.legend_v
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_V.svg", self.legend_v), "Legend does not match expected")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_H.svg to" + self.legend_h
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_H.svg", self.legend_h), "Legend does not match expected")
        
    def tearDown(self):
        os.remove(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.mrf")
        os.remove(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.xml")
        os.remove(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.mrf")
        os.remove(self.lcdir + "/test/empty_tile.png")

if __name__ == '__main__':
    unittest.main()