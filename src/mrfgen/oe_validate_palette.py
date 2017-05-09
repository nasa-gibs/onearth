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
# Tool for validating image palette with GIBS colormap
#
# Example:
#
#  oe_validate_palette.py 
#   -c colormap.xml
#   -i input.png
#   -v verbose
#
#
# Global Imagery Browse Services

import logging
from optparse import OptionParser
import os
import sys
import time
import socket
import subprocess
import urllib
import urllib2
import xml.dom.minidom
import re

versionNumber = '1.1.4'
colormap_filename = None
    
class ColorEntry:
    """RGBA values for VRT color table"""
    
    def __init__(self, idx, r, g, b, a):
        self.idx = idx
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
        self.a = int(a)
        self.rgba = (str(r)+','+str(g)+','+str(b)+','+str(a)).strip()
        self.irgba = (str(idx) + ": " + str(r)+','+str(g)+','+str(b)+','+str(a)).strip()
        
    def __repr__(self):
        return '<Entry idx="%d" c1="%d" c2="%d" c3="%d" c4="%d"/>' % (self.idx, self.r, self.g, self.b, self.a)
        
def hex_to_rgb(value):
    """Converts hex to rgb values"""
    
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))
    
def sigevent(type, mssg, sigevent_url):
    """
    Send a message to sigevent service.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
                        'http://localhost:8100/sigevent/events/create'
    """
    # Constrain mssg to 256 characters (including '...').
    if len(mssg) > 256:
        mssg=str().join([mssg[0:253], '...'])
    print str().join(['sigevent ', type, ' - ', mssg])
    # Remove any trailing slash from URL.
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any question mark from URL.  It is added later.
    if sigevent_url[-1] == '?':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any trailing slash from URL.  (Again.)
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Define sigevent parameters that get encoded into the URL.
    data={}
    data['type']=type
    data['description']=mssg
    data['computer']=socket.gethostname()
    data['source']='ONEARTH'
    data['format']='TEXT'
    data['category']='MRFGEN'
    data['provider']='GIBS'
    if colormap_filename != None:
        data['data']=colormap_filename
    # Format sigevent parameters that get encoded into the URL.
    values=urllib.urlencode(data)
    # Create complete URL.
    full_url=sigevent_url+'?'+values
    data=urllib2.urlopen(full_url)

def log_info_mssg(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print mssg
    logging.info(mssg)

def log_info_mssg_with_timestamp(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print time.asctime()
    logging.info(time.asctime())
    log_info_mssg(mssg)

def log_sig_warn(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(time.asctime())
    logging.warning(mssg)
    # Send to sigevent.
    try:
        sent=sigevent('WARN', mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'

def log_sig_exit(type, mssg, sigevent_url):
    """
    Send a message to the log, to sigevent, and then exit.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Add "Exiting" to mssg.
    mssg=str().join([mssg, '  Exiting colormap2vrt.'])
    # Send to sigevent.
    try:
        sent=sigevent(type, mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'
    # Send to log.
    if type == 'INFO':
        log_info_mssg_with_timestamp(mssg)
    elif type == 'WARN':
        logging.warning(time.asctime())
        logging.warning(mssg)
    elif type == 'ERROR':
        logging.error(time.asctime())
        logging.error(mssg)
    # Exit.
    sys.exit()

def log_the_command(command_list):
    """
    Send a command list to the log.
    Arguments:
        command_list -- list containing all elements of a subprocess command.
    """
    # Add a blank space between each element.
    spaced_command=''
    for ndx in range(len(command_list)):
        spaced_command=str().join([spaced_command, command_list[ndx], ' '])
    # Send to log.
    log_info_mssg_with_timestamp(spaced_command)

def check_abs_path(directory_path):
    """
    Check if directory is absolute path.
    If not, prepend current working directory.
        Argument:
            directory_path -- path to check if absolute
    """
    if directory_path[0] != '/':
        directory_path = os.getcwd() +'/' + directory_path
    
    return directory_path

def read_colormap(colormap_filename, sigevent_url):
    """
    Read color tables from GIBS color map and returns a list of colors
    Argument:
        colormap_filename -- GIBS color map file to read color tables
    """
    colortable = []
    try:
        # Open colormap file.
        colormap_file=open(colormap_filename, 'r')
        dom = xml.dom.minidom.parse(colormap_file)
        log_info_mssg("Opening file " + colormap_filename)
        colormap_file.close()
    except IOError: # try http URL
        log_info_mssg("Unable to find file, trying as URL: " + colormap_filename)
        try:
            dom = xml.dom.minidom.parse(urllib.urlopen(colormap_filename))
        except IOError, e:
            log_sig_exit("ERROR", str(e), sigevent_url)
    # ColorMap parameters
    colorMaps = dom.getElementsByTagName('ColorMap')
    idx = 0
    alpha = 255 # default to 255
    # Read colormap
    for count, colorMap in enumerate(colorMaps): 
        # ColorMapEntry
        if colorMap.parentNode.getElementsByTagName('Opacity').length > 0:
            alpha = float(colorMap.parentNode.getElementsByTagName('Opacity')[0].firstChild.nodeValue.strip()) * 255
        colorMapEntries = colorMap.getElementsByTagName('ColorMapEntry')
        for colorMapEntry in colorMapEntries:
            entry_alpha = alpha
            try:
                if colorMapEntry.attributes["transparent"].value == "true":
                    entry_alpha = 0
                else:
                    entry_alpha = 255
            except KeyError: # check for "opacity" attribute in SLD
                try:
                    entry_alpha = float(colorMapEntry.attributes["opacity"].value) * 255
                except KeyError:
                    entry_alpha = alpha
            try:
                rgb = colorMapEntry.attributes["rgb"].value.split(",")
            except KeyError:  # check for "color" attribute in SLD
                rgb = hex_to_rgb(colorMapEntry.attributes["color"].value)
            colorEntry = ColorEntry(idx, rgb[0], rgb[1], rgb[2], entry_alpha)
            colortable.append(colorEntry)
            idx+=1
    return colortable

def read_color_table(image, sigevent_url):
    """
    Read color table from an input image and returns list of colors
    Argument:
        image -- Image to read color table
    """
    log_info_mssg("Checking for color table in " + image)
    colortable = []
    idx = 0
    has_color_table = False
    gdalinfo_command_list=['gdalinfo', image]
    gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for line in gdalinfo.stdout.readlines():
        if has_color_table == True and (" " + str(idx) + ":") in line:
            rgb = line.replace(str(idx) + ":", "").strip().split(",")
            if len(rgb) < 4:
                rgb[3] = "255" # default if alpha not define
            colorEntry = ColorEntry(idx, rgb[0], rgb[1], rgb[2], rgb[3])
            colortable.append(colorEntry)
            idx+=1
        if "Color Table" in line:
            has_color_table = True
    if has_color_table == False:
        log_sig_exit("Error", "No color table found in " + image, sigevent_url)
    return colortable
    
#-------------------------------------------------------------------------------   

print 'oe_validate_palette.py v' + versionNumber

usageText = 'oe_validate_palette.py --colormap [colormap.xml] --input [input.png] --sigevent_url [url] --no_index --ignore_colors --verbose'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--colormap',
                  action='store', type='string', dest='colormap_filename',
                  help='Full path of colormap filename.')
parser.add_option('-f', '--fill_value',
                  action='store', type='string', dest='fill_value',
                  default="0,0,0,0", help='Fill value for colormaps. Default: "0,0,0,0"')
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input_filename',
                  help='Full path of input image')
parser.add_option("-n", "--no_index", action="store_true", dest="no_index", 
                  default=False, help="Do not check for matching index location")
parser.add_option('-u', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Print out detailed log messages")
parser.add_option('-x', '--ignore_colors',
                  action='store', type='string', dest='ignore_colors',
                  help='List of RGBA color values to ignore in image palette separated by "|"')

# Read command line args
(options, args) = parser.parse_args()

# colormap filename
if not options.colormap_filename:
    parser.error('ColorMap filename not provided. --colormap must be specified.')
else:
    if '://' not in options.colormap_filename:
        colormap_filename = check_abs_path(options.colormap_filename)
    else:
        colormap_filename = options.colormap_filename
# input PNG
if not options.input_filename:
    parser.error('Input filename not provided. --input must be specified.')
else:
    input_filename = options.input_filename

# do not compare index location values
no_index = options.no_index

# print verbose log messages
verbose = options.verbose

# Sigevent URL.
sigevent_url = options.sigevent_url

# fill color value
fill_value = str(options.fill_value).strip()
r_color = re.compile(r'\d+,\d+,\d+,\d+')
if r_color.match(fill_value) is None:
    log_sig_exit("Error", "fill_value format must be %d,%d,%d,%d", sigevent_url)

# Colors to ignore
if not options.ignore_colors:
    ignore_colors = []
else:
    ignore_colors = options.ignore_colors.strip().split("|")
    for ignore_color in ignore_colors:
        if r_color.match(ignore_color) is None:
            log_sig_exit("Error", ignore_color + " ignore_color format must be %d,%d,%d,%d", sigevent_url)

# verbose logging
if verbose:
    log_info_mssg('Colormap: ' + colormap_filename)
    log_info_mssg('Input Image: ' + input_filename)
    log_info_mssg('Fill Value: ' + fill_value)
    log_info_mssg('Ignore Colors: ' + str(ignore_colors))
      
# Read palette from colormap
try:
    colortable = read_colormap(colormap_filename, sigevent_url)
except:
    log_sig_exit("Error", "Unable to read colormap " + colormap_filename, sigevent_url)
      
# Read palette from image
img_colortable = read_color_table(input_filename, sigevent_url)

# Lists to track matching colors
match_colors = []
colormap_only = []
mm_colormap_only = []
ex_colormap_only = []
image_only = []
mm_image_only = []
ex_image_only = []
img_color_idx = len(img_colortable)

# Populate initial lists
for i, img_color in enumerate(img_colortable):
    if img_color in ignore_colors:
        if verbose:
            log_info_mssg("Ignoring color: " + ignore_color)
        continue
    if img_color.rgba != fill_value:
        image_only.append(img_color.rgba if no_index else img_color.irgba)
    else:
        if i < len(img_colortable)-1:
            if img_colortable[i+1].rgba != fill_value:
                image_only.append(img_color.rgba if no_index else img_color.irgba)
            else:
                if img_color_idx == len(img_colortable):
                    img_color_idx = img_color.idx # keep track of where fill values begin

#for color in colortable:
for color in colortable:
    colormap_only.append(color.rgba if no_index else color.irgba)

if no_index == True: # Get only unique values
    image_only = list(set(image_only))
    colormap_only = list(set(colormap_only))
    
# Loop through color tables
for color in colortable:
    match = False
    for img_color in img_colortable:
        if no_index == True:
            if color.rgba == img_color.rgba:
                match = True
                if img_color.rgba not in match_colors:
                    match_colors.append(img_color.rgba)
                    if color.rgba in colormap_only:
                        colormap_only.remove(color.rgba)
                    if img_color.rgba in image_only:
                        image_only.remove(img_color.rgba)
                    if verbose:
                        log_info_mssg("Found matching color " + img_color.rgba)
        else:
            if color.irgba == img_color.irgba:
                if img_color.irgba not in match_colors:
                    match = True
                    match_colors.append(img_color.irgba)
                    if color.irgba in colormap_only:
                        colormap_only.remove(color.irgba)
                    if img_color.irgba in image_only:
                        image_only.remove(img_color.irgba)
                    if verbose:
                        log_info_mssg("Found matching color " + img_color.irgba)
    if match == False and color.rgba != fill_value:
        if verbose:
            log_info_mssg("No match for color " + color.rgba)

# Distinguish between mismatch or extra
if no_index == False:
    for i, color in enumerate(img_colortable):
        if i >= len(colortable):
            if color.irgba in image_only:
                ex_image_only.append(color.irgba)
    for color in image_only:
        if color not in ex_image_only:
            mm_image_only.append(color)
            
    for i, color in enumerate(colortable):
        if i >= img_color_idx:
            if color.irgba in colormap_only:
                ex_colormap_only.append(color.irgba)
    for color in colormap_only:
        if color not in ex_colormap_only:
            mm_colormap_only.append(color)

if verbose:
    log_info_mssg(("\nMatched palette entries   : " + str(len(match_colors)) + "\n") + "\n".join(match_colors))
else:
    log_info_mssg("\nMatched palette entries   : " + str(len(match_colors)))

if len(image_only) > 0 and no_index == False:
    log_info_mssg(("\nMismatched palette entries: " + str(len(mm_image_only)) + "\n") + "\n".join(mm_image_only))

if len(colormap_only) > 0:
    if no_index == False:
        log_info_mssg(("\nMissing palette entries   : " + str(len(ex_colormap_only)) + "\n") + "\n".join(ex_colormap_only))
    else:
        log_info_mssg(("\nMissing palette entries   : " + str(len(colormap_only)) + "\n") + "\n".join(colormap_only))

if len(image_only) > 0:
    if no_index == False:
        log_info_mssg(("\nExtra palette entries     : " + str(len(ex_image_only)) + "\n") + "\n".join(ex_image_only))
    else:
        log_info_mssg(("\nExtra palette entries     : " + str(len(image_only)) + "\n") + "\n".join(image_only))
print "\n"   

summary = "Summary:\nMatched palette entries   : " + str(len(match_colors))
if verbose or len(image_only) > 0 or len(colormap_only) > 0:
    if no_index == True:
        summary = summary + "\nMissing palette entries   : " + str(len(colormap_only))
        summary = summary + "\nExtra palette entries     : " + str(len(image_only)) + "\n"
    else:
        summary = summary + "\nMismatched palette entries: " + str(len(mm_image_only))
        summary = summary + "\nMissing palette entries   : " + str(len(ex_colormap_only))
        summary = summary + "\nExtra palette entries     : " + str(len(ex_image_only)) + "\n"

if len(image_only) > 0 or len(colormap_only) > 0:
    if len(colormap_only) == 0:
        sig_status = 'WARN'
    else:
        sig_status = 'ERROR'
else:
    sig_status = 'INFO'
try:
    sigevent(sig_status, summary, sigevent_url)
except urllib2.URLError:
    None
sys.exit(len(image_only))
