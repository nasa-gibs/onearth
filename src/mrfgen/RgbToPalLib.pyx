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
This script converts Python codes to Cython codes.

Date: 12-27-2021
'''

import numpy as np
from PIL import Image
import xml.etree.ElementTree as xmlet
import math

cpdef run(verbose, colormapXml, rgbaPng, palPng, fillValue):

    Image.MAX_IMAGE_PIXELS = None

    returnCode = 0

    # Only print less than 100.
    MAX_NOT_FOUND=100

    # Read colormap data from XML file to colormap.
    try:
        cmtree = xmlet.parse(colormapXml)
    except Exception as e:
        print('Reading error for file ' + colormapXml + ': ' + e)
        return -1

    # Detect colormap size.
    cmSize = 0
    for child in cmtree.iter():
        if child.tag == 'ColorMapEntry': 
            cmSize += 1

    if verbose:
        print('Colormap size is: ' + str(cmSize))
        
    # Define colormap (palette) array.
    cdef unsigned char [:,:] colormap = np.zeros((cmSize, 4), dtype='B')
    cdef int row = 0
    for child in cmtree.iter():
        if child.tag == 'ColorMapEntry': 
            rgbStr = child.get('rgb').split(",")
            transparent = child.get('transparent')
            if transparent == 'true':
                transparency = 0
            else:
                transparency = 255
            colormap[row][0] = int(rgbStr[0])
            colormap[row][1] = int(rgbStr[1])
            colormap[row][2] = int(rgbStr[2])
            colormap[row][3] = transparency

            row += 1

    cdef unsigned char [:] c = np.zeros((4), dtype='B')
    if verbose:
        print('Colormap: ')
        for c in colormap:
            print(np.asarray(c))

    # Read RGB data and convert them to palette index.
    try:
        img = Image.open(rgbaPng) 

        if img.mode == "RGB":
            img = img.convert("RGBA") # Set A to 255.
        elif img.mode == "RGBA":
            pass
        else:
            print('Not right input image type.')
            return -1
    except Exception as e:
        print('Reading error for file ' + rgbaPng + ': ' + e)
        return -1

    cdef int width, height
    width, height = img.size

    if verbose:
        print('Image width, height, mode: ' + str(width) + ', ' + str(height) + ', ' + img.mode)

    # Define image array.
    cdef unsigned char [:, :] imgData = np.zeros((height, width), dtype='B')
    cdef unsigned char [:,:] notFoundData = np.zeros((MAX_NOT_FOUND, 4), dtype='B')
    cdef int notFoundDataNumber = 0
    cdef int y, x
    cdef int [:] pixel
    cdef int index
    cdef unsigned char[:,:,:] imgA = np.array(img)

    for x in range(height):
        for y in range(width):
            hasData = False
            for index in range(cmSize):
                if imgA[x][y][0] == colormap[index][0] and \
                   imgA[x][y][1] == colormap[index][1] and \
                   imgA[x][y][2] == colormap[index][2] and \
                   imgA[x][y][3] == colormap[index][3]:
                    imgData[x][y] = index
                    hasData = True
                    break
            if hasData == False:
                imgData[x][y] = int(fillValue)

                # Add unique not found values.
                notFound = False
                for k in range(notFoundDataNumber):
                    if imgA[x][y][0] == notFoundData[k][0] and \
                       imgA[x][y][1] == notFoundData[k][1] and \
                       imgA[x][y][2] == notFoundData[k][2] and \
                       imgA[x][y][3] == notFoundData[k][3]:
                        notFound = True
                        break
                if notFound == False:
                    if notFoundDataNumber < MAX_NOT_FOUND:
                        notFoundData[notFoundDataNumber]=(imgA[x][y])
                        notFoundDataNumber += 1

    if notFoundDataNumber > 0:
        returnCode = notFoundDataNumber
        print('Not found data number ' + str(notFoundDataNumber) + ": ")
        for k in range(notFoundDataNumber):
            print(np.asarray(notFoundData[k]))
    
        # Now not exit. If want, just uncomment below line.
        #return returnCode
    
    # Make image from data.
    img = Image.fromarray(np.uint8(imgData))
    img = img.convert('P')

    # Add color map to image.
    img.putpalette((np.uint8(colormap)).flatten(), rawmode='RGBA')

    try:
        img.save(palPng)
    except Exception as e:
        print('Writing error for file ' + palPng + ': ' + e)
        return -1

    return returnCode

