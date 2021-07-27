#!/usr/bin/env python3

# Copyright (c) 2002-2015, California Institute of Technology.
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

# NASA Jet Propulsion Laboratory
# 2015

from optparse import OptionParser
from xml.dom import minidom
import os
import sys
import struct
import math

versionNumber = '1.0'
    
#-------------------------------------------------------------------------------   

print('mrf_read.py v' + versionNumber)

usageText = 'mrf_read.py --input [mrf_file] --output [output_file] (--tilematrix INT --tilecol INT --tilerow INT) OR (--offset INT --size INT) OR (--tile INT)'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input',
                  help='Full path of the MRF data file')
parser.add_option('-f', '--offset',
                  action='store', type='int', dest='offset',
                  help='data offset')
parser.add_option("-l", "--little_endian", action="store_true", dest="endian", 
                  default=False, help="Use little endian instead of big endian (default)")
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='Full path of output image file')
parser.add_option('-s', '--size',
                  action='store', type='int', dest='size',
                  help='data size')
parser.add_option('-t', '--tile',
                  action='store', type='int', dest='tile',
                  help='tile within index file')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Verbose mode")
parser.add_option('-w', '--tilematrix',
                  action='store', type='int', dest='tilematrix',
                  help='Tilematrix (zoom level) of tile')
parser.add_option('-x', '--tilecol',
                  action='store', type='int', dest='tilecol',
                  help='The column of tile')
parser.add_option('-y', '--tilerow',
                  action='store', type='int', dest='tilerow',
                  help='The row of tile')
parser.add_option('-z', '--zlevel',
                  action='store', type='int', dest='zlevel',
                  help='the z-level of the data')


# Read command line args.
(options, args) = parser.parse_args()

if not options.input:
    parser.error('input filename not provided. --input must be specified.')
else:
    input = options.input
if not options.output:
    parser.error('output filename not provided. --output must be specified.')
else:
    output = options.output
    
mrfDoc = minidom.parse(input)
mrf_x  = None
mrf_y  = None
mrf_z  = None
mrf_type = "PNG"

if len(mrfDoc.getElementsByTagName('Raster')) > 0:
    rasterElem = mrfDoc.getElementsByTagName('Raster')[0]

    if len(rasterElem.getElementsByTagName('Size')):
        sizeElem  = rasterElem.getElementsByTagName('Size')[0]
        sizeAttrs = dict(sizeElem.attributes.items())

        mrf_x = int(sizeAttrs['x'])
        mrf_y = int(sizeAttrs['y'])

        if 'z' in sizeAttrs:
            mrf_z = int(sizeAttrs['z'])

    if len(rasterElem.getElementsByTagName('Compression')):
        compressionElem = rasterElem.getElementsByTagName('Compression')[0]
        mrf_type = str(compressionElem.firstChild.nodeValue).strip()

        if mrf_type == "PBF":
            mrf_type = "MVT"

else:
    print("\nMissing Raster element in MRF, exiting.")
    exit(-1)


if options.verbose:
    print("\nMRF type: " + mrf_type)

size = None

if options.verbose:
    print("MRF x: " + str(mrf_x) + " y: " + str(mrf_y))
    print("Ratio " + str(mrf_x/mrf_y))
    
index = input.replace(".mrf",".idx")
if mrf_type == "JPEG":
    datafile = input.replace(".mrf",".pjg")
elif mrf_type == "MVT":
    datafile = input.replace(".mrf",".pvt")
else:
    datafile = input.replace(".mrf",".ppg")

if not options.tile:
    tile = None
else:
    tile = options.tile-1
  
if tile == None and str(options.tilematrix) == "None":    
    if not options.offset:
        parser.error('offset not provided. --offset must be specified.')
    else:
        offset = options.offset
    if not options.size:
        parser.error('size not provided. --size must be specified.')
    else:
        size = options.size
    
if options.endian == True:
    data_type = '<q'
else:
    data_type = '>q'
  
if str(options.zlevel) == "None":
    z = -1
    z_size = None
    if mrf_z:
        print("Error: z-level must be specified for this input")
        exit(1)
else:
    z = options.zlevel
    z_size = mrf_z
    if options.verbose:
        print("Using z-level:" + str(z) + " and MRF z-size:" + str(z_size))
    if z >= z_size:
        print("Error: Specified z-level is greater than the maximum size")
        exit(1)
    
w = int(math.ceil(float(mrf_x)/512))
h = int(math.ceil(float(mrf_y)/512))
if z >= 0:
    len_base = w * h * z_size
    low = z_size
else:
    len_base = w * h
    low = 1
idx_size = os.path.getsize(index)
len_tiles = idx_size/16

if options.verbose:
    print("Number of tiles " + str(len_tiles))
    print("\n--Pyramid structure--")

levels = []
rows = []
cols = []

levels.append(0)
rows.append(h)
cols.append(w)

while len_base > low:
    levels.append(len_base)
    w = int(math.ceil(w / 2.0))
    h = int(math.ceil(h / 2.0))
    if z >= 0:
        len_base = w * h * z_size
    else:
        len_base = w * h
    rows.append(h)
    cols.append(w)
    
if z >= 0:
    levels.append(1*z_size)
else:
    levels.append(1)

if options.verbose:   
    for idx, val in enumerate(levels):
        if idx > 0: 
            print("Level " + str(len(levels)-idx-1) + ": " + str(levels[idx]) + " tiles, " + str(rows[idx-1]) + " rows, " + str(cols[idx-1]) + " columns")
    print("\n")

if options.tilematrix != None:
    if options.tilerow == None or options.tilecol == None:
        parser.error('tilerow and tilecol not provided. --tilecol INT and --tilerow INT must be specified when using MRF file.')
    tilematrix = options.tilematrix + 2
    level = levels[len(levels)-tilematrix]
    row = rows[len(levels)-tilematrix]
    col = cols[len(levels)-tilematrix]
    
    if options.verbose:
        message = "Looking up tilematrix level:" + str(options.tilematrix) + ", tile row:" + str(options.tilerow) + ", tile col:" + str(options.tilecol)
        if z >= 0:
            message = message + ", z-level:" + str(z)
        print(message)
        print("Level contains " + str(row) + " rows, " + str(col) + " columns")
    
    if (options.tilerow) > row-1:
        print("Tile row exceeds the maximum (" + str(row-1) + ") for this level")
        exit(1)
    if (options.tilecol) > col-1:
        print("Tile col exceeds the maximum (" + str(col-1) + ") for this level")
        exit(1)
      
    level_start = 0
    for idx, val in enumerate(levels):
        if levels[idx-1]==level:
            break
        level_start+=val
    tile = ((options.tilerow) * col) + options.tilecol + level_start
    if z >= 0:
        level_size = (levels[len(levels)-tilematrix+1]/z_size)
        tile = tile + (z * level_size) 
    
    if options.verbose:
        print("Tiles for level begin at: " + str(level_start+1))
        print("Using tile: " + str(tile+1))
    
if index != None and tile != None:
    if options.verbose:
        print("\nReading " + index)
    idx = open(index, 'rb')
    
    idx.seek(16*tile)
    byte = idx.read(16)
    offset = struct.unpack(data_type, byte[0:8])[0]
    size = struct.unpack(data_type, byte[8:16])[0]
    idx.close() 
    
    if options.verbose: 
        print("Read from index at offset " + str(16*tile) + " for 16 bytes")
        print("Got data file offset " + str(offset) + ", size " + str(size))
   

if options.verbose:
    print("\nReading " + datafile)   

if size != None and offset !=None:
    if options.verbose:
        print("Read from data file at offset " + str(offset) + " for " + str(size) + " bytes")
        
    out = open(output, 'wb')
    mrf_data = open(datafile, 'rb')
    mrf_data.seek(offset)
    image = mrf_data.read(size)
    out.write(image)
    
    print("Wrote " + output)
    mrf_data.close()
    out.close()  
else:
    print("Error: Tile could not be located")
    exit(1)