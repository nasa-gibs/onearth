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
# wmts2twmsbox.py
# Convert WMTS row and column to equivalent TWMS bounding box.  Assumes EPSG4326.

# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014
# Joe.T.Roberts@jpl.nasa.gov

import string
from optparse import OptionParser

units = 108710.44022780626 # meters/degree, not sure why this number is used

def wmts2twmsbox(top_left_bbox, col, row):
    """
    Returns TWMS equivalent bounding box based on TILECOL and TILEROW.
    Arguments:
        top_left_bbox -- The TWMS bounding box for the top-left corner tile (e.g., '-180,81,-171,90').
        col -- WMTS TILECOL value.
        row -- WMTS TILEROW value.
    """
    
    print "Top Left BBOX:",top_left_bbox
    print "TILECOL="+str(int(col))
    print "TILEROW="+str(int(row))

    # parse top_left_bbox to individual values
    top_left_bbox = top_left_bbox.split(",")
    top_left_minx = float(top_left_bbox[0])
    top_left_miny = float(top_left_bbox[1])
    top_left_maxx = float(top_left_bbox[2])
    top_left_maxy = float(top_left_bbox[3])
    
    # get dimensions of bounding box
    x_size = top_left_maxx - top_left_minx
    y_size = top_left_maxy - top_left_miny
    
    # calculate new bounding box based on col and row
    request_minx = top_left_minx + (col*x_size) 
    request_miny = top_left_maxy - (row*y_size) - y_size
    request_maxx = top_left_minx + (col*x_size) + x_size
    request_maxy = top_left_maxy - (row*y_size)
    
    # calculate scale denominator for reference
    scale_denominator = ((x_size*2)/0.28)*units
    print "Scale Denominator:", str(round(scale_denominator,10))
    
    return "Request BBOX: " + str(request_minx)+","+str(request_miny)+","+str(request_maxx)+","+str(request_maxy)

def wmts2twmsbox_scale(scale_denominator, col, row):
    """
    Returns TWMS equivalent bounding box based on TILECOL and TILEROW.
    Arguments:
        scale_denominator -- WMTS scale denominator value from getCapabilities.
        col -- WMTS TILECOL value.
        row -- WMTS TILEROW value.
    """
    
    print "Scale Denominator:",str(scale_denominator)
    print "TILECOL="+str(col)
    print "TILEROW="+str(row)
    
    size = (scale_denominator/units)*0.28/2
    
    # set top_left values
    top_left_minx = -180
    top_left_maxy = 90
    
    # calculate additional top_left values for reference
    top_left_maxx = -180 + size
    top_left_miny = 90 - size
    print "Top Left BBOX: " + str(top_left_minx)+","+str(top_left_miny)+","+str(top_left_maxx)+","+str(top_left_maxy)
    
    # calculate new bounding box based on col and row
    request_minx = top_left_minx + (col*size) 
    request_miny = top_left_maxy - (row*size) - size
    request_maxx = top_left_minx + (col*size) + size
    request_maxy = top_left_maxy - (row*size)
    
    return "Request BBOX: " + str(round(request_minx,10))+","+str(round(request_miny,10))+","+str(round(request_maxx,10))+","+str(round(request_maxy,10))


versionNumber = '0.2'
usageText = 'wmts2twmsbox.py --col [TILECOL] --row [TILEROW] --scale_denominator [value] OR --top_left_bbox [bbox]'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--col',
                  action='store', type='string', dest='col',
                  help='WMTS TILECOL value.')
parser.add_option('-r', '--row',
                  action='store', type='string', dest='row',
                  help='WMTS TILEROW value.')
parser.add_option('-s', '--scale_denominator',
                  action='store', type='string', dest='scale_denominator',
                  help='WMTS scale denominator value from getCapabilities.')
parser.add_option('-t', '--top_left_bbox',
                  action='store', type='string', dest='top_left_bbox',
                  help='The TWMS bounding box for the top-left corner tile (e.g., "-180,81,-171,90").')

# Read command line args.
(options, args) = parser.parse_args()
if not options.col:
    parser.error('col is required')
if not options.row:
    parser.error('row is required')

# Run translation based on given parameters
if options.scale_denominator:
    print (wmts2twmsbox_scale(float(options.scale_denominator),int(options.col),int(options.row)))
elif options.top_left_bbox:
    print (wmts2twmsbox(options.top_left_bbox,int(options.col),int(options.row)))
else:
    parser.error('Either top_left_bbox or scale_denominator is required')
