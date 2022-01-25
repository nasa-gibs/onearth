#!/usr/bin/env python3

'''
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

'''
This script converts RGB PNG image to Palette PNG image.

Input: 
    RGB PNG image.
    Colormap in XML format.
    
Output:
    Palette PNG image.
    
Date: 12-16-2021
'''

import os
import getopt, sys
import datetime
import RgbToPalLib

start = datetime.datetime.now()

def usage():
    print("Usage: python RgbPngToPalPng.py [-h]  [-v] -c InputColormap -i InputImage \
          -o OutputImage [-f fillValue (default is 0)]")

colormapXml = ''
rgbaPng = ''
palPng = ''
fillValue = 0

returnCode = 0

verbose = False

try:
    # Options with : need values.
    opts, args = getopt.getopt(sys.argv[1:],"hvc:i:o:f:")
except getopt.GetoptError: # Not in these options.
    print('Please check your input parameters.')
    usage()
    sys.exit(-1)

for opt, arg in opts:
    if opt == '-h':
        print('Check input parameter h.')
        usage()
        sys.exit(-1)
    elif opt == "-v":
        verbose = True
        print('Verbose: ' + str(verbose))
    elif opt == "-c":
        colormapXml = arg
        # Check it is .xml file and it exists.
        fileExist = os.path.exists(colormapXml)
        if '.xml' in colormapXml.lower() and fileExist:
            print('Input colormap file: ' + colormapXml)
        else:
            print('Colormap is not XML file or does not exist')
            sys.exit(-1)
    elif opt == '-i':
        rgbaPng = arg
        # Check it is .png file and it exists.
        fileExist = os.path.exists(rgbaPng)
        if '.png' in rgbaPng.lower() and fileExist:
            print('Input RGB PNG image: ' + rgbaPng)
        else:
            print('Input image is not PNG file or does not exist.')
            sys.exit(-1)
    elif opt == '-o':
        palPng = arg
        print('Output pelette PNG image: ' + palPng)
    elif opt == '-f':
        fillValue = arg 
        if int(fillValue) < 0 or int(fillValue) > 255:
            print('Fill value is not between 0 to 255')
            sys.exit(-1)
        print('Fill value: ' + fillValue)
         
if colormapXml == '' or rgbaPng == '' or palPng == '':
    print('Miss required input parameters.')
    usage()
    sys.exit(-1)

if verbose:
    print('Start to process RGB PNG image to palette PNG image ...')

returnCode = RgbToPalLib.run(verbose, colormapXml, rgbaPng, palPng, fillValue)

end = datetime.datetime.now()

usedTime = (end - start).total_seconds()

if verbose:
    print ("Time: " + str(usedTime))
    print('Completed')
    print('Return code: '+str(returnCode))

sys.exit(returnCode)

