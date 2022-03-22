#!/usr/bin/env python3

# Copyright (c) 2002-2017, California Institute of Technology.
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
# oe_generate_empty_tile.py
# The OnEarth Empty Tile Generator.
#
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory

import sys
import urllib.request, urllib.parse, urllib.error
import xml.dom.minidom
from optparse import OptionParser
import png
import os

toolName = "oe_generate_empty_tile.py"
versionNumber = os.environ.get('ONEARTH_VERSION')

class ColorMap:
    """ColorMap metadata"""
    
    def __init__(self, units, colormap_entries, style):
        self.units = units
        self.colormap_entries = colormap_entries
        self.style = str(style).lower()
        
    def __repr__(self):
        if self.units != None:
            xml = '<ColorMap units="%s">' % (self.units)
        else:
            xml = '<ColorMap>'
        for colormap_entry in self.colormap_entries:
            xml = xml + '\n    ' + colormap_entry.__repr__()
        xml = xml + '\n</ColorMap>'
        return xml

    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)


class ColorMapEntry:
    """ColorMapEntry values within a ColorMap"""
    
    def __init__(self, red, green, blue, transparent, source_value, value, label, nodata):
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.transparent = transparent
        self.source_value = source_value
        self.value = value
        self.label = label
        self.nodata = nodata
        self.color = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        if self.value != None:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" value="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.value, self.label)
        else:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.label)
        return xml
    
    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)
    

def parse_colormap(colormap_location, verbose):
    
    try:
        if verbose:
            print("Reading color map:", colormap_location)
        colormap_file = open(colormap_location,'r')
        dom = xml.dom.minidom.parse(colormap_file)
        colormap_file.close()
    except IOError:
        print("Accessing URL", colormap_location)
        try:
            dom = xml.dom.minidom.parse(urllib.request.urlopen(colormap_location))
        except:
            msg = "URL " + colormap_location + " is not accessible"
            print(msg, file=sys.stderr)
            raise Exception(msg)
    
    style = "discrete"
    colormap_entries = []
    colormapentry_elements = dom.getElementsByTagName("ColorMapEntry")
    for colormapentry in colormapentry_elements:
        rgb = colormapentry.attributes['rgb'].value
        red, green, blue = rgb.split(',')
        try:
            value = colormapentry.attributes['value'].value
            if "(" in value or "[" in value:
                style = "range"
        except KeyError:
            value = None
            style = "classification"
        try:
            transparent = True if colormapentry.attributes['transparent'].value.lower() == 'true' else False
        except KeyError:
            transparent = False
        try:
            source_value = colormapentry.attributes['sourceValue'].value
        except KeyError:
            source_value = value
        try:
            label = colormapentry.attributes['label'].value
        except KeyError:
            label = value
        try:
            nodata = True if colormapentry.attributes['nodata'].value.lower() == 'true' else False
        except KeyError:
            nodata = False
        
        colormap_entries.append(ColorMapEntry(red, green , blue, transparent, source_value, value, label, nodata))
        
    colormap = ColorMap(None, colormap_entries, style)
    if verbose:
        print("ColorMap style:", style)
        print(colormap)
    
    return colormap
    

#-------------------------------------------------------------------------------

print(toolName + ' ' + versionNumber + '\n')

usageText = toolName + " --colormap [file] --output [file] --height [int] --width [int] --type [palette]"

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--colormap',
                  action='store', type='string', dest='colormap',
                  help='Full path or URL of colormap filename.')
parser.add_option('-f', '--format',
                  action='store', type='string', dest='format', default = 'png',
                  help='Format of output file. Supported formats: png')
parser.add_option('-i', '--index',
                  action='store', type='string', dest='index',
                  help='The index of the color map to be used as the empty tile palette entry, overrides nodata value')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output file')
parser.add_option('-t', '--type',
                  action='store', type='string', dest='type', default = 'palette',
                  help='The image type: rgba or palette. Default: palette')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Print out detailed log messages")
parser.add_option('-x', '--width',
                  action='store', type='string', dest='width', default = '512',
                  help='Width of the empty tile  (default: 512)')
parser.add_option('-y', '--height',
                  action='store', type='string', dest='height', default = '512',
                  help='Height of the empty tile (default: 512)' )

# read command line args
(options, args) = parser.parse_args()

if options.colormap:
    colormap_location = options.colormap
else:
    print("colormap file must be specified...exiting")
    exit()
if options.output:
    output_location = options.output
else:
    print("output file must be specified...exiting")
    exit()
    
color_index = 0

# parse colormap and get color entry
try:
    colormap = parse_colormap(colormap_location, options.verbose)
    colormap_entry = colormap.colormap_entries[color_index] # default to first entry if none specified
    if options.index != None:
        colormap_entry = colormap.colormap_entries[int(options.index)]
        color_index = int(options.index)
    else:
        for index,entry in enumerate(colormap.colormap_entries):
            if entry.nodata == True:
                colormap_entry = entry
                color_index = index
                break # use first nodata entry found
except Exception as e:
    print(toolName + ": ERROR: " + str(e) + "\n", file=sys.stderr)
    sys.exit(1)

# generate empty_tile
try:
    if options.verbose:
        print("Using index " + str(color_index) + " with entry:\n" + str(colormap_entry))
    
    f = open(output_location, 'wb')
        
    if options.type == "palette":
            
        palette = []
        for j in range (0, 256):
            try:
                entry = colormap.colormap_entries[j]
                if entry.transparent == True:
                    alpha = 0
                else:
                    alpha = 255
                palette.append((entry.red,entry.green,entry.blue,alpha))
            except IndexError: # pad with zeroes
                palette.append((0,0,0,0))
        
        rows = []
        img = []
        for i in range (1, (int(options.width))+1):
            rows.append(color_index)
        for i in range (0, int(options.height)):
            img.append(rows)
    
        w = png.Writer(int(options.width), int(options.height), palette=palette, bitdepth=8)
        w.write(f, img)
    
    else: # use RGBA
        
        rows = []
        img = []
        for i in range (1, (int(options.width)*4)+1):
            if i%4 == 1:
                rows.append(colormap_entry.red)
            elif i%4 == 2:
                rows.append(colormap_entry.green)
            elif i%4 == 3:
                rows.append(colormap_entry.blue)
            elif i%4 == 0:
                if colormap_entry.transparent == True:
                    rows.append(0)
                else:
                    rows.append(255)
        
        for i in range (0, int(options.height)):
            img.append(rows)
    
        w = png.Writer(int(options.width), int(options.height), alpha=True, greyscale=False)
        w.write(f, img)
    
    f.close()
    
    print("\nSuccessfully generated empty tile " + output_location + " of size: " + str(options.width) + " by " + str(options.height))
    
except IOError as e:
    print(toolName + ": " + str(e), file=sys.stderr)
    sys.exit(1)
    
exit()
