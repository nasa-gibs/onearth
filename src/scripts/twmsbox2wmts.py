#!/bin/env python

# Copyright (c) 2002-2014, California Institute of Technology.
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

# twmsbox2wmts.py
# Convert TWMS bounding box to WMTS tile.  Assumes EPSG4326.

# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014

import string
from optparse import OptionParser

units = 111319.490793274 # meters/degree
tilesize = 512 # pixels
pixelsize = 0.00028 # meters

def twmsbox2wmts(request_bbox):
    """
    Returns WMTS equivalent TILECOL and TILEROW as string.  Assumes top left is -180 90.
    Arguments:
        request_bbox -- The requested TWMS bounding box to be translated (e.g., '-81,36,-72,45').
    """

    request_bbox = request_bbox.split(",")
    
    # parse request_bbox to individual values
    request_minx = float(request_bbox[0])
    request_miny = float(request_bbox[1])
    request_maxx = float(request_bbox[2])
    request_maxy = float(request_bbox[3])
    
    x_size = request_maxx - request_minx
    y_size = request_maxy - request_miny
    
    # set top_left values
    top_left_minx = -180
    top_left_maxy = 90
    
    # calculate additional top_left values for reference
    top_left_maxx = top_left_minx + x_size
    top_left_miny = top_left_maxy - y_size
    
    print "Top Left BBOX:",str(top_left_minx)+","+str(top_left_miny)+","+str(top_left_maxx)+","+str(top_left_maxy)
    print "Request BBOX:",str(request_minx)+","+str(request_miny)+","+str(request_maxx)+","+str(request_maxy)
    
    # calculate col and row
    col = ((request_minx-top_left_minx)/x_size)
    row = ((request_miny-top_left_miny)/y_size)
    
    # calculate scale denominator for reference
    scale_denominator = (((x_size*2)/pixelsize)*units)/(tilesize*2)
    print "Scale Denominator:", str(round(scale_denominator,10))
    
    return "TILECOL=" + str(abs(int(col))) + "\n" + "TILEROW="+str(abs(int(row)))


versionNumber = '0.3'
usageText = 'twmsbox2wmts.py --bbox [bbox]'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-b', '--bbox',
                  action='store', type='string', dest='request_bbox',
                  help='The requested TWMS bounding box to be translated (e.g., "-81,36,-72,45").')

# Read command line args.
(options, args) = parser.parse_args()
if not options.request_bbox:
    parser.error('bbox is required')

print (twmsbox2wmts(options.request_bbox))
