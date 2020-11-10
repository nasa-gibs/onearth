#!/usr/bin/env python3

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

'''
Created on Nov 15, 2013

@author: mcechini
'''

import codecs
import colorsys
from xml.dom import minidom
from xml.dom import Node
import sys, getopt, os


## Class Definitions ##

class ColorMapEntry():
    rgb         = ""
    transparent = False
    sourceValue = ""
    value       = ""
    label       = ""
    ref         = ""
    nodata      = False

    def __hash__(self):
        return hash(self.sourceValue)

    def __eq__(self, other):
        return self.sourceValue == other.sourceValue


class Entries():
    minLabel    = ""
    maxLabel    = ""
    colormapentries = []

    def __hash__(self):
        return hash(self.minLabel)

    def __eq__(self, other):
        return self.minLabel == other.minLabel

class LegendEntry():
    rgb         = ""
    label       = ""
    id          = ""
    showTick    = False
    showValue   = False

    def __hash__(self):
        return hash(self.label)

    def __eq__(self, other):
        return self.label == other.Label


class Legend():
    type          = ""
    minLabel      = ""
    maxLabel      = ""
    legendentries = []

    def __hash__(self):
        return hash(self.type)

#    def __cmp__(self, other):
#        return self.type.cmp(other.type)

#    def __eq__(self, other):
#        return self.type.eq(other.type)


class ColorMap():
    title   = ""
    units   = ""
    entries = None
    legend  = None

    def __hash__(self):
        return hash(self.title)

class ColorMaps():
    colormaps = []
    product   = ""

    def __hash__(self):
        return hash(self.product)

    def __eq__(self, other):
        return self.product == other.product

## Global Variables ##
colorMapsList = []

## Functions ##
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


## START Parse Color Maps ##
def parseColorMaps(sourceXml, fileName) :

    xmldoc     = minidom.parse(sourceXml)

    colorMaps = ColorMaps()
    colorMaps.product = os.path.basename(fileName)

    for colorMapNode in xmldoc.documentElement.getElementsByTagName("ColorMap") :

        colorMapAttrDict = dict(list(colorMapNode.attributes.items()))
        colorMap  = ColorMap()
        colorMap.title   = colorMapAttrDict.get('title', '')
        colorMap.units   = colorMapAttrDict.get('units', '')

        colorMap.entries = parseEntries(colorMapNode.getElementsByTagName("Entries")[0])

        if len(colorMapNode.getElementsByTagName("Legend")) > 0 :
            colorMap.legend  = parseLegend(colorMapNode.getElementsByTagName("Legend")[0])

        colorMaps.colormaps.append(colorMap)

    colorMapsList.append(colorMaps)

## END Parse Color Map ##

## START Parse Entries ##
def parseEntries(entriesNode):

    entriesAttrDict = dict(list(entriesNode.attributes.items()))

    entries = Entries()
    entries.minLabel = entriesAttrDict.get('minLabel', '')
    entries.maxLabel = entriesAttrDict.get('maxLabel', '')
    entries.colormapentries = []

    for entryNode in entriesNode.getElementsByTagName("ColorMapEntry") :

       entryAttrDict = dict(list(entryNode.attributes.items()))

       cmEntry = ColorMapEntry()

       #t required, but defaults to false
       if 'transparent' in entryAttrDict :
          cmEntry.transparent = entryAttrDict['transparent']
       else:
          cmEntry.transparent = False

       #t required, but defaults to false
       if 'nodata' in entryAttrDict :
          cmEntry.nodata = entryAttrDict['nodata']
       else:
          cmEntry.nodata = False

       cmEntry.rgb = entryAttrDict.get('rgb', '')
       cmEntry.value = entryAttrDict.get('value', '')
       cmEntry.sourceValue = entryAttrDict.get('sourceValue', '')
       cmEntry.label = entryAttrDict.get('label', '')
       cmEntry.ref = entryAttrDict.get('ref', '')

       entries.colormapentries.append(cmEntry)

    return entries

## END Parse Entries ##


## START Parse Legend ##
def parseLegend(legendNode):

    legendAttrDict = dict(list(legendNode.attributes.items()))

    legend = Legend()
    legend.type     = legendAttrDict.get('type', '')
    legend.minLabel = legendAttrDict.get('minLabel', '')
    legend.maxLabel = legendAttrDict.get('maxLabel', '')
    legend.legendentries = []

    for entryNode in legendNode.getElementsByTagName("LegendEntry") :

       legendAttrDict = dict(list(entryNode.attributes.items()))

       legendEntry = LegendEntry()

       legendEntry.rgb       = legendAttrDict.get('rgb', '')
       legendEntry.label     = legendAttrDict.get('label', '')
       legendEntry.id        = legendAttrDict.get('id', '')
       legendEntry.showTick  = False if 'showTick' not in legendAttrDict else legendAttrDict.get('showTick') == "true"
       legendEntry.showLabel = False if 'showLabel' not in legendAttrDict else legendAttrDict.get('showLabel') == "true"

       legend.legendentries.append(legendEntry)

    return legend

## END Parse Legend ##


def is_bright(color):
    """
    http://24ways.org/2010/calculating-color-contrast
    """

    rgb = color_string_to_list(color)

    yiq = ((rgb[0] * 299) + (rgb[1] * 587) + (rgb[2] * 144)) / 1000
    return yiq > 128

def rgb_to_hex(color):

    rgb = color_string_to_list(color)

    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

def color_string_to_list(color):

    rgb = []

    commaIdx0 = 0
    commaIdx1 = color.find(',',commaIdx0)
    rgb.append(int(color[commaIdx0:commaIdx1]))

    commaIdx0 = commaIdx1 + 1
    commaIdx1 = color.find(',',commaIdx0)
    rgb.append(int(color[commaIdx0:commaIdx1]))

    commaIdx0 = commaIdx1 + 1
    commaIdx1 = len(color)
    rgb.append(int(color[commaIdx0:commaIdx1]))

    return rgb


## START Generate HTML ##
def generateHTML(outputHtmlFile) :

    if outputHtmlFile:
       outputHandle = open(outputHtmlFile, "w")
    else:
       outputHandle = sys.stdout

    for colorMaps in colorMapsList :
        outputHandle.write("<!doctype html>\n")
        outputHandle.write("<html>\n")
        outputHandle.write("<head>\n")
        outputHandle.write('<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>')
        outputHandle.write('<link rel="stylesheet" type="text/css" href="resources/colormap.css">')
        outputHandle.write("</head>\n")
        outputHandle.write("<body>\n")

        outputHandle.write("<h1>" + colorMaps.product + "</h1>\n")

        outputHandle.write("<p>Download Color Map file <a href=\"../" + colorMaps.product + "\">here</a><br><br>\n")

        for colorMap in colorMaps.colormaps :
            outputHandle.write("<h2> ColorMap : Title '" + colorMap.title + "'  Units '" + colorMap.units + "'</h2>\n")
            outputHandle.write("<h3> Entries : MinLabel '" + colorMap.entries.minLabel + "'  MaxLabel '" + colorMap.entries.maxLabel + "'</h3>\n")

            outputHandle.write("<table>\n")

            outputHandle.write("  <tr>\n")
            outputHandle.write("    <th>RGB</th>\n")
            outputHandle.write("    <th class='transparency'>Transparent</th>\n")
            outputHandle.write("    <th class='data-value'>SourceValue</th>\n")
            outputHandle.write("    <th class='data-value'>Value</th>\n")
            outputHandle.write("    <th class='data-value'>Label</th>\n")
            outputHandle.write("    <th class='data-value'>Reference</th>\n")
            outputHandle.write("    <th class='data-value'>NoData</th>\n")
            outputHandle.write("  </tr>\n")


            for entry in colorMap.entries.colormapentries :
                outputHandle.write("  <tr>\n")
                outputHandle.write("    <td class='color' bgcolor=" + rgb_to_hex(entry.rgb) + ">" + \
                       "<font color=\"" + ("black" if is_bright(entry.rgb) else "white") + "\">" + \
                       entry.rgb + "</font></td>\n")
                outputHandle.write("    <td class='transparency'>" + str(entry.transparent) + "</td>\n")
                outputHandle.write("    <td class='data-value'>" + (str(entry.sourceValue) if entry.sourceValue != None else "") + "</td>\n")
                outputHandle.write("    <td class='data-value'>" + (str(entry.value) if entry.value != None else "") + "</td>\n")
                outputHandle.write("    <td class='data-value'>" + entry.label + "</td>\n")
                outputHandle.write("    <td class='data-value'>" + (str(entry.ref) if entry.ref != None else "") + "</td>\n")
                outputHandle.write("    <td class='data-value'>" +  str(entry.nodata) + "</td>\n")
                outputHandle.write("  </tr>\n")

            outputHandle.write("</table>\n")

            if colorMap.legend == None:
                outputHandle.write("<h3>No Legend</h3>\n")
            else:
                outputHandle.write("<h3> Legend : Type '" + colorMap.legend.type + "'  MinLabel '" + colorMap.legend.minLabel + "'  MaxLabel '" + colorMap.legend.maxLabel + "'</h3>\n")

                outputHandle.write("<table>\n")

                outputHandle.write("  <tr>\n")
                outputHandle.write("    <th>RGB</th>\n")
                outputHandle.write("    <th class='data-value'>showTick</th>\n")
                outputHandle.write("    <th class='data-value'>showLabel</th>\n")
                outputHandle.write("    <th class='data-value'>Label</th>\n")
                outputHandle.write("    <th class='data-value'>ID</th>\n")
                outputHandle.write("  </tr>\n")


                for entry in colorMap.legend.legendentries:
                    outputHandle.write("  <tr>\n")
                    
                    outputHandle.write("    <td class='color' bgcolor=" + rgb_to_hex(entry.rgb) + ">" + "<font color=\"" + \
                                          ("black" if is_bright(entry.rgb) else "white") + "\">" + entry.rgb + "</font></td>\n")
                    outputHandle.write("    <td class='data-value'>" + ("True" if entry.showTick else "False") + "</td>\n")
                    outputHandle.write("    <td class='data-value'>" + ("True" if entry.showTick else "False") + "</td>\n")
                    outputHandle.write("    <td class='data-value'>" + entry.label + "</td>\n")
                    outputHandle.write("    <td class='data-value'>" + (str(entry.id) if entry.id != None else "") + "</td>\n")
                    outputHandle.write("  </tr>\n")

                outputHandle.write("</table>\n")


            if not colorMap == colorMaps.colormaps[-1]:
               outputHandle.write("<hr>\n")
               outputHandle.write("<br>\n")
               outputHandle.write("<br>\n")
               outputHandle.write("<br>\n")

        outputHandle.write("</body>\n")
        outputHandle.write("</html>\n")


    if outputHtmlFile:
       outputHandle.close()

def usage():
   print("Usage: colorMaptoHTML.py [OPTIONS]")
   print("\nOptions:")
   print("  -h, --help         show this help message and exit")
   print("  -c COLORMAP_FILE, --colormap COLORMAP_FILE")
   print("                     Path to colormap file to be converted.  (Required)")
   print("  -o OUTPUT_HTML_FILE, --output OUTPUT_HTML_FILE")
   print("                     Path to output html file.  If not provided, results are printed to stdout")


def main(argv):

    colormapFile   = None
    outputHtmlFile = None

    try:
        opts, args = getopt.getopt(argv,"hi:c:o:",["colormap=","output="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-c", "--colormap"):
            colormapFile = arg
        elif opt in ("-o", "--output"):
            outputHtmlFile = arg

    if not colormapFile:
       print("Colormap File must be provided")
       sys.exit(-1)

    parseColorMaps(colormapFile, colormapFile)
    generateHTML(outputHtmlFile)


if __name__ == "__main__":
   main(sys.argv[1:])

