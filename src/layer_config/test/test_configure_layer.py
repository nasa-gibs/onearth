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
# Tests for oe_configure_layer.py
#

import os
import unittest
import subprocess
import filecmp
from shutil import copyfile, rmtree
import xml.etree.ElementTree as ET

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
        self.oe_configure_layer = '/usr/bin/oe_configure_layer'
        if os.path.isfile(self.oe_configure_layer) == False:
            self.oe_configure_layer = os.path.abspath(os.path.dirname(__file__) + '/../bin/oe_configure_layer.py')
            if os.path.isfile(self.oe_configure_layer) == False:
                raise Exception("oe_configure_layer not found")
        if os.environ.has_key('LCDIR') == False:
            self.lcdir = os.path.abspath(os.path.dirname(__file__) + '/..')
            if os.path.isdir(self.lcdir + "/conf") == False:
                self.lcdir = '/usr/share/onearth/layer_config' # use default layer config directory
        else:
            self.lcdir = os.environ['LCDIR']
        self.legend_v = self.lcdir + "/test/MODIS_Aqua_Aerosol_V.svg"
        self.legend_h = self.lcdir + "/test/MODIS_Aqua_Aerosol_H.svg"
        
        # get config directories
        try:
            config_path = self.lcdir+'/conf/environment_geographic.xml'
            config_file = open(config_path,'r')
            tree = ET.parse(config_file)
            root = tree.getroot()
            print ('\nUsing config: ' + config_path)
        except IOError:
            raise Exception('Cannot read configuration file: ' + config_path)        
        for child in root:
            if child.tag == "GetCapabilitiesLocation":
                if child.attrib['service'] == 'wmts':
                    self.wmts_getcapabilities = child.text
                if child.attrib['service'] == 'twms':
                    self.twms_getcapabilities = child.text
            if child.tag == "GetTileServiceLocation":
                self.gettileservice = child.text
            if child.tag == "CacheLocation":
                self.cachedir = child.text
        config_file.close()

        # Set up dummy data files
        if not os.path.exists(self.cachedir + "MODIS_Aqua_Aerosol"):
            os.makedirs(self.cachedir + "MODIS_Aqua_Aerosol")
        if not os.path.exists(self.cachedir + "MODIS_Aqua_Aerosol/2014"):
            os.makedirs(self.cachedir + "MODIS_Aqua_Aerosol/2014")
        if not os.path.exists(self.cachedir + "MODIS_Aqua_Aerosol/YYYY"):
            os.makedirs(self.cachedir + "MODIS_Aqua_Aerosol/YYYY")
        if not os.path.isfile(self.cachedir + 'MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf'):
            copyfile('MODIS_Aqua_AerosolTTTTTTT_.mrf', self.cachedir + 'MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf')
        if not os.path.isfile(self.cachedir + 'MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.zdb'):
            copyfile('MODIS_Aqua_AerosolTTTTTTT_.zdb', self.cachedir + 'MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.zdb')

    def test_layer_config_default(self):
        #Run layer config
        layer_config_file = self.lcdir + "/test/layer_configuration_test1.xml"
        errors = run_command(self.oe_configure_layer + " -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
   
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        self.assertTrue(os.path.isfile(self.cachedir + "cache_all_wmts.config"), "cache_all_wmts.config does not exist")
        self.assertTrue(os.path.isfile(self.wmts_getcapabilities + "getCapabilities.xml"), "WMTS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile(self.cachedir + "MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf"), "MODIS_Aqua_Aerosol2014364_.mrf does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.xml"), "MODIS_Aqua_AerosolTTTTTTT_.xml does not exist in WMTS staging area")

        self.assertTrue(os.path.isfile(self.cachedir + "cache_all_twms.config"), "cache_all_twms.config does not exist")
        self.assertTrue(os.path.isfile(self.twms_getcapabilities + "getCapabilities.xml"), "TWMS getCapabilities.xml does not exist")
        self.assertTrue(os.path.isfile(self.gettileservice + "getTileService.xml"), "TWMS getTileService.xml does not exist")
        self.assertTrue(os.path.isfile(self.cachedir + "MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf"), "MODIS_Aqua_Aerosol2014364_.mrf does not exist")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT__gc.xml"), "MODIS_Aqua_AerosolTTTTTTT_gc.xml does not exist in TWMS staging area")
        self.assertTrue(os.path.isfile(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT__gts.xml"), "MODIS_Aqua_AerosolTTTTTTT_gts.mrf does not exist in TWMS staging area")

        
        contains_layer = False
        getCapabilities = open(self.wmts_getcapabilities + "getCapabilities.xml", 'r')
        for line in getCapabilities.readlines():
            if "<ows:Identifier>MODIS_Aqua_Aerosol</ows:Identifier>" in line:
                print "Layer found in WMTS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "WMTS GetCapabilities does not contain layer")
        
        contains_layer = False
        contains_zleveldata = False
        cacheConfig = open(self.cachedir + "cache_all_wmts.config", 'r')
        for line in cacheConfig.readlines():
            if "SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=MODIS_Aqua_Aerosol&STYLE=(default)?&TILEMATRIXSET=EPSG4326_2km&TILEMATRIX=[0-9]*&TILEROW=[0-9]*&TILECOL=[0-9]*&FORMAT=image%2Fpng" in line:
                print "Layer found in WMTS cache configuration"
                contains_layer = True
            if "MODIS_Aqua_Aerosol/YYYY/MODIS_Aqua_AerosolTTTTTTT_.zdb" in line:
                print "z level data found in WMTS cache configuration"
                contains_zleveldata = True
        cacheConfig.close()
        self.assertTrue(contains_layer, "WMTS cache configuration does not contain layer")
        self.assertTrue(contains_zleveldata, "WMTS cache configuration does not contain z level data")
        
        contains_layer = False
        getCapabilities = open(self.gettileservice + "getTileService.xml", 'r')
        for line in getCapabilities.readlines():
            if "<Name>MODIS_Aqua_Aerosol tileset</Name>" in line:
                print "Layer found in TWMS GetCapabilities"
                contains_layer = True
        getCapabilities.close()
        self.assertTrue(contains_layer, "TWMS GetCapabilities does not contain layer")
        
        contains_layer = False
        getTileService = open(self.gettileservice + "getTileService.xml", 'r')
        for line in getTileService.readlines():
            if "<Name>MODIS_Aqua_Aerosol tileset</Name>" in line:
                print "Layer found in TWMS GetTileService"
                contains_layer = True
        getTileService.close()
        self.assertTrue(contains_layer, "GetTileService does not contain layer")
        
        contains_layer = False
        cacheConfig = open(self.cachedir + "cache_all_twms.config", 'r')
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
        errors = run_command(self.oe_configure_layer + " -g -l " + self.lcdir + " -c " + layer_config_file)
        print "Errors: " + str(errors)
        
        self.assertEqual(errors, 0, "Errors detected with layer configuration tool")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_V.svg to " + self.legend_v
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_V.svg", self.legend_v), "Legend does not match expected")
        print "Comparing: " + legend_location + "/MODIS_Aqua_Aerosol_H.svg to " + self.legend_h
        self.assertTrue(filecmp.cmp(legend_location + "/MODIS_Aqua_Aerosol_H.svg", self.legend_h), "Legend does not match expected")
        
    def tearDown(self):
        os.remove(self.cachedir + "MODIS_Aqua_Aerosol/2014/MODIS_Aqua_Aerosol2014364_.mrf")
        rmtree(self.cachedir + "MODIS_Aqua_Aerosol/")
        os.remove(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.xml")
        os.remove(self.lcdir + "/wmts/EPSG4326/MODIS_Aqua_AerosolTTTTTTT_.mrf")
        os.remove(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT__gc.xml")
        os.remove(self.lcdir + "/twms/EPSG4326/MODIS_Aqua_AerosolTTTTTTT__gts.xml")
        os.remove(self.lcdir + "/test/empty_tile.png")

if __name__ == '__main__':
    unittest.main()
