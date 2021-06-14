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
# Tool for converting SLD ColorMaps to a VRT ColorTable template.
#
# Example:
#
#  colormap2vrt.py 
#   -c colormap.xml
#   -o output.vrt
#   -m merge.vrt
#
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory

from optparse import OptionParser
import os
import logging
import sys
import time
import socket
import urllib.request, urllib.error, urllib.parse
import xml.dom.minidom
from oe_utils import log_sig_exit, log_sig_err, log_sig_warn, log_info_mssg, log_info_mssg_with_timestamp, log_the_command, check_abs_path

versionNumber = os.environ.get('ONEARTH_VERSION')
colormap_filename = None
    
class ColorEntry:
    """RGBA values for VRT color table"""
    
    def __init__(self, idx, r, g, b, a):
        self.idx = idx
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
        self.a = int(a)
        
    def __repr__(self):
        return '<Entry idx="%d" c1="%d" c2="%d" c3="%d" c4="%d"/>' % (self.idx, self.r, self.g, self.b, self.a)
        
def hex_to_rgb(value):
    """Converts hex to rgb values"""
    
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))
    
#-------------------------------------------------------------------------------   

print('colormap2vrt v' + versionNumber)

usageText = 'colormap2vrt.py --colormap [colormap.xml] --output [output.vrt] --merge [merge.vrt] --transparent'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--colormap',
                  action='store', type='string', dest='colormap_filename',
                  help='Full path of colormap filename.')
parser.add_option('-m', '--merge',
                  action='store', type='string', dest='merge_vrt',
                  help='Full path of VRT in which to merge colormap')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output_vrt',
                  help='Full path of the final output VRT')
parser.add_option("-t", "--transparent", action="store_true", dest="transparent", 
                  default=False, help="Use transparent alpha value as default")
parser.add_option("-s", "--send_email", action="store_true", dest="send_email", 
                  default=False, help="Send email notification for errors and warnings.")
parser.add_option('--email_server', action='store', type='string', dest='email_server',
                  default='', help='The server where email is sent from (overrides configuration file value')
parser.add_option('--email_recipient', action='store', type='string', dest='email_recipient',
                  default='', help='The recipient address for email notifications (overrides configuration file value')
parser.add_option('--email_sender', action='store', type='string', dest='email_sender',
                  default='', help='The sender for email notifications (overrides configuration file value')

# Read command line args.
(options, args) = parser.parse_args()
# colormap filename.
if not options.colormap_filename:
    parser.error('ColorMap filename not provided. --colormap must be specified.')
else:
    if '://' not in options.colormap_filename:
        colormap_filename = check_abs_path(options.colormap_filename)
    else:
        colormap_filename = options.colormap_filename
# output VRT.
if not options.output_vrt:
    parser.error('Output filename not provided. --output must be specified.')
else:
    output_vrt = options.output_vrt
# merge VRT.
merge_vrt = options.merge_vrt
# transparent
if options.transparent == False:
    alpha = 255
else:
    alpha = 0
# Send email.
send_email=options.send_email
# Email server.
email_server=options.email_server
# Email recipient
email_recipient=options.email_recipient
# Email sender
email_sender=options.email_sender
# Email metadata replaces sigevent_url
if send_email == True and email_recipient != '':
    sigevent_url = (email_server, email_recipient, email_sender)
else:
    sigevent_url = ''

log_info_mssg('colormap: ' + colormap_filename)
log_info_mssg('output VRT: ' + output_vrt)
log_info_mssg('merge VRT: ' + merge_vrt)

try:
    # Open colormap file.
    colormap_file=open(colormap_filename, 'r')
    dom = xml.dom.minidom.parse(colormap_file)
    log_info_mssg("Opening file " + colormap_filename)
    colormap_file.close()
except IOError: # try http URL
    log_info_mssg("Accessing URL " + colormap_filename)
    dom = xml.dom.minidom.parse(urllib.request.urlopen(colormap_filename))

# ColorMap parameters
colorMaps = dom.getElementsByTagName('ColorMap')
colortable = [] # Apply SLDs with multiple color maps to one color table

idx = 0

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
    if (count+1) == len(colorMaps):
        while idx < 256: # pad out with zero values to get 256 colors for MRFs
            colorEntry = ColorEntry(idx, 0, 0, 0, 0)
            colortable.append(colorEntry)
            idx+=1

# output color table as template if no merge VRT is provided
if merge_vrt == None:
    output_file = open(output_vrt, 'w')
    for colorEntry in colortable:
        output_file.writelines('        '+str(colorEntry)+'\n')
    output_file.close();
else: # merge SLD into VRT
    merge_file = open(merge_vrt, 'r')
    # check if VRT is uses palette
    if "<ColorInterp>Palette</ColorInterp>" not in merge_file.read():
        merge_file.close()
        message = merge_vrt + " is NOT paletted VRT."
        log_sig_exit('ERROR', message, sigevent_url)
    else:
        # copy merge VRT to output
        merge_file.seek(0)
        output_file = open(output_vrt, 'w')
        for line in merge_file: # stop at ColorTable
            if "<ColorTable>" in line:
                output_file.writelines(line);
                break
            else:
                output_file.writelines(line);
        for colorEntry in colortable:
            output_file.writelines('        '+str(colorEntry)+'\n')
        for line in merge_file: # go to end of ColorTable
            if "</ColorTable>" in line:
                output_file.writelines(line);
                break
        for line in merge_file:
            output_file.writelines(line);
        merge_file.close()
        output_file.close()

message = output_vrt + " created successfully."
log_info_mssg(message)
# log_sig_exit('INFO', message, sigevent_url)