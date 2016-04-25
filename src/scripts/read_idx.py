#!/bin/env python

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
import os
import sys
import struct

versionNumber = '1.0.0'
    
#-------------------------------------------------------------------------------   

print 'read_idx.py v' + versionNumber

usageText = 'read_idx.py --index [index_file] --output [output_file]'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-i', '--index',
                  action='store', type='string', dest='index',
                  help='Full path of the MRF index file')
parser.add_option("-l", "--little_endian", action="store_true", dest="endian", 
                  default=False, help="Use little endian instead of big endian (default)")
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='Full path of output CSV file')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Verbose mode")


# Read command line args.
(options, args) = parser.parse_args()

if not options.index:
    parser.error('index filename not provided. --index must be specified.')
else:
    index = options.index
if not options.output:
    parser.error('output filename not provided. --output must be specified.')
else:
    output = options.output
    
if options.endian == True:
    data_type = '<q'
else:
    data_type = '>q'
   
out = open(output, 'w')
idx = open(index, 'r')

out.write("idx_offset,data_offset,data_size\n")

i = 0
while i <  os.path.getsize(index):
    idx.seek(i)
    byte = idx.read(16)
    offset = struct.unpack(data_type, byte[0:8])[0]
    size = struct.unpack(data_type, byte[8:16])[0]
    if options.verbose:
        print str(i) + "," + str(offset) + "," + str(size)
    out.write(str(i) + "," + str(offset) + "," + str(size)+"\n")
    i+=16
    
print str(i) + " bytes read"
print "Wrote " + output
idx.close()
out.close()
    
    
