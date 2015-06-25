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

# NASA Jet Propulsion Laboratory
# 2015

from optparse import OptionParser
import os
import sys

versionNumber = '0.6.4'
    
#-------------------------------------------------------------------------------   

print 'read_mrfdata.py v' + versionNumber

usageText = 'read_mrfdata.py --input [mrf_data_file] --output [output_file] --offset INT --size INT'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input',
                  help='Full path of the MRF data file')
parser.add_option('-f', '--offset',
                  action='store', type='int', dest='offset',
                  help='data offset')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='Full path of output image file')
parser.add_option('-s', '--size',
                  action='store', type='int', dest='size',
                  help='data size')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Verbose mode")


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
    
if not options.offset:
    parser.error('offset not provided. --offset must be specified.')
else:
    offset = options.offset
if not options.size:
    parser.error('size not provided. --size must be specified.')
else:
    size = options.size
   
out = open(output, 'w')
mrf_data = open(input, 'r')

mrf_data.seek(offset)
image = mrf_data.read(size)
out.write(image)


print "Wrote " + output
mrf_data.close()
out.close() 
