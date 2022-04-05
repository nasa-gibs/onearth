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

from xml.dom import minidom
from xml.dom import Node
import re
import sys, getopt
from math import modf, ceil

class SLD_v1_0_0_ColorMapEntry():
    quantity  = None
    opacity   = None
    rgb       = [-1,-1,-1]
    
    def __hash__(self):
        return hash(self.quantity)

    def __eq__(self, other):
        return self.quantity == other.quantity


class GIBS_ColorMapEntry():
    rgb         = [-1,-1,-1]
    label       = ""
    value       = None
    sourceValue = None
    transparent = False
    nodata      = False
    ref         = -1
    
    def __hash__(self):
        return hash(self.rgb)

    def __eq__(self, other):
        return self.rgb == other.rgb


class GIBS_ColorMap():
    showUnits  = False
    showLegend = False
    minLabel  = None
    maxLabel  = None
    cmEntries = []


def hexToRGB(hexValue):

    if re.match("#[0-9A-Fa-f]{6}", hexValue):
        r = int(hexValue[1:3], 16)
        g = int(hexValue[3:5], 16)
        b = int(hexValue[5:7], 16)
    elif re.match("[0-9A-Fa-f]{6}", hexValue):
        r = int(hexValue[0:2], 16)
        g = int(hexValue[2:4], 16)
        b = int(hexValue[4:6], 16)
    else:
        print(("Invalid Hex Value: " + str(hexValue)))
        r=g=b=-1

    return [r,g,b]


def dataDensify(startValue, endValue, steps):

    dataSteps = []
    
    stepsize = (endValue - startValue) / steps
    
    for step in range(1, steps):
        dataSteps.append(startValue + (stepsize * step))
        
    dataSteps.append(endValue)
    
    return dataSteps


def rampDensify(startColor, endColor, steps):

    colorSteps = []
    
    # color conversion utils
    f2c = lambda f: int(f * 255.0) & 0xff
    c2f = lambda c: float(c) / 255.0
    
    # start color...
    #print(startColor)
    r1 = c2f(startColor[0])
    g1 = c2f(startColor[1])
    b1 = c2f(startColor[2])
    
    # end color...
    #print(endColor)
    r2 = c2f(endColor[0])
    g2 = c2f(endColor[1])
    b2 = c2f(endColor[2])
 
    # generate a gradient of one step from color to color:
    delta = 1.0 / steps
    for j in range(int(steps)):
        t = j * delta
        a = 1.0
        r = (1.0 - t) * r1 + t * r2
        g = (1.0 - t) * g1 + t * g2
        b = (1.0 - t) * b1 + t * b2
        
        color = [f2c(r), f2c(g), f2c(b)]
        #print(color)
        colorSteps.append(color)

    return colorSteps


def stepDensify(startColor, steps, direction):

    colorSteps = []
   
    colorSteps.append([startColor[0],startColor[1],startColor[2]])
   
    lastColor   = startColor
    colorsAdded = 0
    colorsAvail = [True,True,True]
   
    while colorsAdded < steps:
        for index in range(0,3):
       
            newColor = lastColor[index] + (1 * direction)
       
            if newColor < 0 or newColor > 255: 
                colorsAvail[index] = False
                continue
        
            lastColor[index] = newColor
            colorSteps.append([lastColor[0],lastColor[1],lastColor[2]])
            
            colorsAdded = colorsAdded + 1
            
            if colorsAdded >= steps: break
            
        if (not colorsAvail[0]) and (not colorsAvail[1]) and (not colorsAvail[2]):
            exit("Step densification failed!")
           
    return colorSteps


## START Parse SLD v1.0.0 ##
def parseSLD_v1_0_0(sourceXml, layerName, units, offset, factor, format) :
    
    gibsColorMaps = []
    
    xmldoc     = minidom.parse(sourceXml)

    #for childNode in xmldoc.documentElement.childNodes :
    for nlNode in xmldoc.documentElement.getElementsByTagName("NamedLayer") :
    
        nameNode = nlNode.getElementsByTagName("Name")[0]
        
        if nameNode.firstChild.nodeValue != layerName:
            break
        
        
        for userStyleNode in nlNode.getElementsByTagName("UserStyle"):
            # <xsd:element ref="sld:Name" minOccurs="0"/>
            # <xsd:element ref="sld:Title" minOccurs="0"/>


            for rasterSymNode in userStyleNode.getElementsByTagName("RasterSymbolizer"):
                # <xsd:element ref="sld:Name" minOccurs="0"/>
                # <xsd:element ref="sld:Title" minOccurs="0"/>
                    
                colorMapNode   = rasterSymNode.getElementsByTagName("ColorMap")[0]
                sldCMapEntries = []
                
                for colorMapEntryNode in colorMapNode.getElementsByTagName("ColorMapEntry"):
                    attrDict = dict(list(colorMapEntryNode.attributes.items()))

                    sldCMapEntry = SLD_v1_0_0_ColorMapEntry()
                                        
                    if 'opacity' in attrDict :
                        sldCMapEntry.opacity = float(attrDict['opacity'])
                    else:
                        sldCMapEntry.opacity = 1.0
                                            
                    if 'quantity' in attrDict :
                        sldCMapEntry.quantity = float(attrDict['quantity'])
                                            
                    sldCMapEntry.rgb   = hexToRGB(str(attrDict['color']))
                    
                    sldCMapEntries.append(sldCMapEntry)

                    
                # Process the SLD entries into the XML ColorMap
                gibsCMap  = GIBS_ColorMap()
                
                currRef = 1

                prevValue   = sldCMapEntries[0].quantity
                prevOpacity = (sldCMapEntries[0].opacity == 0.0)
                prevRGB     = sldCMapEntries[0].rgb
                        
                gibsCMap.minLabel = "" + format.format(prevValue) + ("" if not units else (" " + units))
                        
                for sldCMapEntry in sldCMapEntries[1:-1]:
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = format.format(prevValue) + " - " + format.format(sldCMapEntry.quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [prevValue, sldCMapEntry.quantity]
                    gibsCMapEntry.sourceValue = [((prevValue - offset) / factor), ((sldCMapEntry.quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                    gibsCMapEntry.ref         = currRef
                            
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                           
                    prevValue   = sldCMapEntry.quantity
                    prevOpacity = (sldCMapEntry.opacity == 0.0)
                    prevRGB     = sldCMapEntry.rgb

                    currRef += 1
                
                
                # If the last entry has the same color as it's previous entry, then update the last 
                # colormap entry to include this upper bound
                if prevRGB == sldCMapEntries[-1].rgb:
                
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = "&gt;= " + format.format(prevValue) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [prevValue,sldCMapEntries[-1].quantity]
                    gibsCMapEntry.sourceValue = [prevValue, ((sldCMapEntries[-1].quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                    gibsCMapEntry.ref         = currRef
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                else:
                    # Add ColorMapEntry for [-1] entry
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = format.format(prevValue) + " - " + format.format(sldCMapEntries[-1].quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [prevValue, sldCMapEntries[-1].quantity]
                    gibsCMapEntry.sourceValue = [((prevValue - offset) / factor), ((sldCMapEntries[-1].quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                    gibsCMapEntry.ref         = currRef
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                    currRef += 1

                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = sldCMapEntries[-1].rgb
                    gibsCMapEntry.label       = format.format(sldCMapEntries[-1].quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [sldCMapEntries[-1].quantity]
                    gibsCMapEntry.sourceValue = [((sldCMapEntries[-1].quantity - offset) / factor), "+INF"]
                    gibsCMapEntry.transparent = (sldCMapEntries[-1].opacity == 0.0)
                    gibsCMapEntry.ref         = currRef
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                gibsCMap.maxLabel    = gibsCMap.cmEntries[-1].label
                gibsCMap.showLegend  = True
                        
                gibsColorMaps.append(gibsCMap)


    return gibsColorMaps

## END Parse SLD v1.0.0 ##



## START Parse SLD v1.1.0 ##
def parseSLD_v1_1_0(sourceXml, layerName, units, offset, factor, rgbOrder, format, densify) :
    
    gibsColorMaps = []
    
    xmldoc     = minidom.parse(sourceXml)

    #for childNode in xmldoc.documentElement.childNodes :
    for nlNode in xmldoc.documentElement.getElementsByTagName("NamedLayer") :
    
        nameNode = nlNode.getElementsByTagName("se:Name")[0]


        if nameNode.firstChild.nodeValue != layerName:
            break
        
        
        for userStyleNode in nlNode.getElementsByTagName("UserStyle"):

            # <xsd:element ref="sld:Name" minOccurs="0"/>
            # <xsd:element ref="sld:Title" minOccurs="0"/>


            for rasterSymNode in userStyleNode.getElementsByTagName("se:RasterSymbolizer"):
                # <xsd:element ref="sld:Name" minOccurs="0"/>
                # <xsd:element ref="sld:Title" minOccurs="0"/>
                
                defaultOpacity = rasterSymNode.getElementsByTagName("se:Opacity")[0].firstChild.nodeValue
                
                colorMapNode   = rasterSymNode.getElementsByTagName("se:ColorMap")[0]
                categorizeNode = rasterSymNode.getElementsByTagName("se:Categorize")[0]
                
                # <se:Categorize fallbackValue="#78c818">
                attrDict = dict(list(categorizeNode.attributes.items()))
                        
                
                # Add a colormap for the no data value based on the fallbackValue
                if 'fallbackValue' in attrDict :
                    hexValue = ""
                    
                    for c in "RGB":
                        s = (-2 * rgbOrder[::-1].find(c)) -2
                        e = (-2 * rgbOrder[::-1].find(c))
                        e = e if e != 0 else None
                        hexValue = hexValue + attrDict['fallbackValue'][s:e]
                
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = hexToRGB(hexValue)
                    gibsCMapEntry.transparent = True
                    gibsCMapEntry.label       = "No Data"
                    gibsCMapEntry.nodata      = True
                    gibsCMapEntry.ref         = 1
                    
                    gibsCMap  = GIBS_ColorMap()
                    gibsCMap.showLegend = True
                    gibsCMap.cmEntries = []
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                    gibsColorMaps.append(gibsCMap)
                    
                    
                
                # Process the SLD entries into the XML ColorMap
                gibsCMap  = GIBS_ColorMap()
                        
                prevValue      = sys.maxsize
                currValue      = sys.maxsize
                firstValue     = sys.maxsize
                prevRGB        = [-1,-1,-1]
                currRGB        = [-1,-1,-1]
                firstRGB       = [-1,-1,-1]
                currRef        = 1

                sldColorMap    = []
                gibsColorMap   = []
                
                
                # Loop through the <Value> and <Threshold> elements and create a list of [value,rgb] pairs from the SLD
                for catChildNode in [ n for n in categorizeNode.childNodes if n.nodeType == Node.ELEMENT_NODE ]:
                
                    # <se:Value>#00ff00</se:Value>
                    if catChildNode.nodeName == "se:Value":
                        currRGB = hexToRGB(catChildNode.firstChild.nodeValue)
                    
                        if prevValue != sys.maxsize:
                            sldColorMap.append([currValue,currRGB])
                   
                    # <se:Threshold>52</se:Threshold>
                    if catChildNode.nodeName == "se:Threshold":
                        currValue = float(catChildNode.firstChild.nodeValue)

                        if prevValue == sys.maxsize:
                            sldColorMap.append([currValue,currRGB])
                        
                        prevValue = currValue
                
                
                # If densifying, then expand the colormap
                if densify:
                    m = re.match(r"([sro])([0-9]*)", densify)

                    
                    # "Ramp" Densification
                    # Generate extra colormap entries for intermediate data values with visibly different colors
                    # from the previous RGB to the current RGB, but using the previous data range.  This data
                    # range lags behind the RGB range because we don't know which color to ramp to due to how the 
                    # <Threshold> values are read in the XML parsing.
                    if m.group(1) == "r":
                                        
                        # First color is always the same
                        gibsColorMap.append(sldColorMap[0])
                        
                        densifyColorMap = sldColorMap[1:-1]
                        densifyDataMap  = sldColorMap[1:]
                        fullColorList   = []
                        
                        numStepsPerBin   = int(m.group(2))
                        numDataBins      = len(densifyDataMap) * numStepsPerBin
                        numStepsPerColor = int(ceil(numDataBins / len(densifyColorMap))) + 1

                        #print(numStepsPerColor)
                        #print(densifyColorMap)
                        
                        # Generate the densified list of possible colors (there will be extra)
                        for i in range(0,len(densifyColorMap) - 1):
                            colorPair  = densifyColorMap[i:i+2]
                            #print(colorPair)
                          
                            colorSteps = rampDensify(colorPair[0][1], colorPair[1][1], numStepsPerColor)
                            
                            #print(len(colorSteps))
                            fullColorList.extend(colorSteps)

                        #print(len(fullColorList))
                        
                        colorIdx = 0
                        # Generate the densified list of data bins and assign colors
                        for i in range(0,len(densifyDataMap) - 1):
                            dataPair  = densifyDataMap[i:i+2]
                            #print(dataPair)
                            
                            dataSteps = dataDensify(dataPair[0][0], dataPair[1][0], numStepsPerBin)
                            
                            #print(dataSteps)
                            for dataStep in dataSteps:
                                #print(colorIdx)
                                gibsColorMap.append([dataStep,fullColorList[colorIdx]])
                                
                                colorIdx = colorIdx +1
                        
                        gibsColorMap.append(sldColorMap[-1])
                else:

                    # First color is always the same
                    gibsColorMap.append(sldColorMap[0])
                        
                    densifyColorMap = sldColorMap[1:-1]
                    densifyDataMap  = sldColorMap[2:]
                    
                    fullColorList   = []

                    # Generate the densified list of possible colors (there will be extra)
                    for i in range(0,len(densifyColorMap)):
                        fullColorList.append(densifyColorMap[i][1])

                    colorIdx = 0
                    # Generate the densified list of data bins and assign colors
                    for i in range(0,len(densifyDataMap)):
                        gibsColorMap.append([densifyDataMap[i][0],fullColorList[colorIdx]])
                                
                        colorIdx = colorIdx +1
                        
                    gibsColorMap.append(sldColorMap[-1])
                    
                #print(gibsColorMap)
                #exit()
                
                prevValue = sys.maxsize

                # Loop through the GIBS colormap entries.
                for cmItem in gibsColorMap[0:-1]:
                                   
                    # If prevValue is sys.maxint, then this is the first Threshold. Add a colormap entry for (-INF,currValue)
                    if prevValue == sys.maxsize:
                        gibsCMapEntry             = GIBS_ColorMapEntry()
                        gibsCMapEntry.transparent = (defaultOpacity == 0.0)
                        gibsCMapEntry.rgb         = cmItem[1]
                        gibsCMapEntry.label       = "&lt; " + format.format(cmItem[0]) + ("" if not units else (" " + units))
                        gibsCMapEntry.value       = ["-INF", cmItem[0]]
                        gibsCMapEntry.sourceValue = ["-INF", ((cmItem[0] - offset) / factor)]
                        gibsCMapEntry.ref         = currRef
                            
                        gibsCMap.cmEntries.append(gibsCMapEntry)
                        gibsCMap.minLabel         = "&lt; " + format.format(cmItem[0]) + ("" if not units else (" " + units))
                            
                        currRef = currRef + 1
                            
                    # If not not the first item, then add a Colormap entry for [prevValue, currValue)
                    else:
                        gibsCMapEntry             = GIBS_ColorMapEntry()
                        gibsCMapEntry.transparent = (defaultOpacity == 0.0)
                        gibsCMapEntry.rgb         = cmItem[1]
                        gibsCMapEntry.label       = format.format(prevValue) + " - " + format.format(cmItem[0]) + ("" if not units else (" " + units))	
                        gibsCMapEntry.value       = [prevValue, cmItem[0]]
                        gibsCMapEntry.sourceValue = [((prevValue - offset) / factor), ((cmItem[0] - offset) / factor)]
                        gibsCMapEntry.ref         = currRef
                            
                        gibsCMap.cmEntries.append(gibsCMapEntry)
                            
                        currRef = currRef + 1                        

                    prevValue  = cmItem[0]
                
                # End: Loop through the <Value> and <Threshold> elements
                
                # Now process the final color entry
                gibsCMapEntry             = GIBS_ColorMapEntry()
                gibsCMapEntry.rgb         = gibsColorMap[-1][1]
                gibsCMapEntry.transparent = (defaultOpacity == 0.0)
                gibsCMapEntry.label       = "&gt;= " + format.format(gibsColorMap[-1][0]) + ("" if not units else (" " + units))	
                gibsCMapEntry.value       = [gibsColorMap[-1][0], "+INF"]
                gibsCMapEntry.sourceValue = [((gibsColorMap[-1][0] - offset) / factor), "+INF"]
                gibsCMapEntry.ref         = currRef
                            
                gibsCMap.cmEntries.append(gibsCMapEntry)
                        
                gibsCMap.maxLabel         = "&gt;= " + format.format(gibsColorMap[-1][0]) + ("" if not units else (" " + units))	
                gibsCMap.showUnits        = True	
                gibsCMap.showLegend       = True
                        
                gibsColorMaps.append(gibsCMap)
               
    return gibsColorMaps

## END Parse SLD v1.1.0 ##



def generateColorMap(gibsColorMaps, units, format, colormapFile):

    if colormapFile:
       outputHandle = open(colormapFile, "w")
    else:
       outputHandle = sys.stdout

    outputHandle.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    outputHandle.write("""<ColorMaps xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:noNamespaceSchemaLocation="http://gibs.earthdata.nasa.gov/schemas/ColorMap_v1.3.xsd">\n""")
    
    for colorMap in gibsColorMaps:

        # <ColorMap title="Sea Ice Concentration" units="%">
        outputHandle.write("  <ColorMap" + 
            ((" units=\"" + units + "\"") if colorMap.showUnits and units else "") + 
            (" title=\"No Data\"" if colorMap.cmEntries[0].nodata else "") + ">\n")

        # <Entries minLabel="0 %" maxLabel="100 %">      
        outputHandle.write("    <Entries" + 
            ("" if not colorMap.minLabel else (" minLabel=\"" + colorMap.minLabel + "\" ")) + 
            ("" if not colorMap.maxLabel else (" maxLabel=\"" + colorMap.maxLabel + "\"")) + 	">\n")
    
        for cMapEntry in colorMap.cmEntries:
            # <ColorMapEntry rgb="9,9,255" transparent="false" sourceValue="[9,10)" value="[9,10)" label="3.6 %" ref="1"/>
        
            rgb = str(cMapEntry.rgb[0]) + "," + str(cMapEntry.rgb[1]) + "," + str(cMapEntry.rgb[2])
            
            if cMapEntry.value: 
                if len(cMapEntry.value) == 1:
                    value = "[" + (cMapEntry.value[0] if isinstance(cMapEntry.value[0], str) else format.format(cMapEntry.value[0])) + "]"
                else:
                    value = "[" + (cMapEntry.value[0] if isinstance(cMapEntry.value[0], str) else format.format(cMapEntry.value[0])) + "," + \
                                  (cMapEntry.value[1] if isinstance(cMapEntry.value[1], str) else format.format(cMapEntry.value[1])) + ")"
            
            if cMapEntry.sourceValue: 
                if len(cMapEntry.sourceValue) == 1:
                    sourceValue = "[" + (cMapEntry.sourceValue[0] if isinstance(cMapEntry.sourceValue[0], str) else format.format(cMapEntry.sourceValue[0])) + "]"
                else:
                    sourceValue = "[" + (cMapEntry.sourceValue[0] if isinstance(cMapEntry.sourceValue[0], str) else format.format(cMapEntry.sourceValue[0])) + "," + \
                                        (cMapEntry.sourceValue[1] if isinstance(cMapEntry.sourceValue[1], str) else format.format(cMapEntry.sourceValue[1])) + ")"

            outputHandle.write("      <ColorMapEntry rgb=\"" + rgb + "\" " + 
               "transparent=\"" + ("true" if cMapEntry.transparent else "false") + "\" " + 
               ("" if not cMapEntry.sourceValue else ("sourceValue=\"" + sourceValue + "\" ")) + 
               ("" if not cMapEntry.value else ("value=\"" + value + "\" ")) + 
               "label=\"" + cMapEntry.label + "\" " + 
               ("" if not cMapEntry.nodata else ("nodata=\"true\" ")) +
               ("" if not colorMap.showLegend else ("ref=\"" + str(cMapEntry.ref) + "\" ")) + 
               "/>\n")

        outputHandle.write("    </Entries>\n")
        
        
        if colorMap.showLegend:
            # <Entries minLabel="0 %" maxLabel="100 %">      
            outputHandle.write("    <Legend type=\"" +
                ("classification" if colorMap.cmEntries[0].nodata else "continuous") + "\" " + 
                ("" if not colorMap.minLabel else (" minLabel=\"" + colorMap.minLabel + "\" ")) + 
                ("" if not colorMap.maxLabel else (" maxLabel=\"" + colorMap.maxLabel + "\"")) + 	">\n")
    
    
            prevRef = -1
            
            for cMapEntry in colorMap.cmEntries:
             
                if cMapEntry.ref != prevRef:
                    rgb = str(cMapEntry.rgb[0]) + "," + str(cMapEntry.rgb[1]) + "," + str(cMapEntry.rgb[2])
            
                    if cMapEntry.value: 
                        if len(cMapEntry.value) == 1:
                            value = "[" + (cMapEntry.value[0] if isinstance(cMapEntry.value[0], str) else format.format(cMapEntry.value[0])) + "]"
                        else:
                            value = "[" + (cMapEntry.value[0] if isinstance(cMapEntry.value[0], str) else format.format(cMapEntry.value[0])) + "," + \
                                           (cMapEntry.value[1] if isinstance(cMapEntry.value[1], str) else format.format(cMapEntry.value[1])) + ")"
        
                    outputHandle.write("      <LegendEntry rgb=\"" + rgb + "\" " + 
                       ("" if not colorMap.showLegend else ("id=\"" + str(cMapEntry.ref) + "\" ")) + "/>\n")
                       
                    
                prevRef    = cMapEntry.ref

            outputHandle.write("    </Legend>\n")
    
        outputHandle.write("  </ColorMap>\n")
        
    outputHandle.write("</ColorMaps>\n")

    if colormapFile:
       outputHandle.close()

def usage():
   print("Usage: SLDtoColorMap.py [OPTIONS]")
   print("\nOptions:")
   print("  -h, --help             show this help message and exit")
   print("  -s SLD_FILE, --sld SLD_FILE")
   print("                    Path to SLD file to be converted")
   print("  -c COLORMAP_FILE, --sld COLORMAP_FILE")
   print("                    Path to colormap file to be created.  If not provided, output is printed to stdout")
   print("  -l LAYER_NAME, --layer LAYER_NAME")
   print("                     Value to be placed in the NamedLayer/Name element")
   print("  -u UNITS, --units UNITS")
   print("                     Units to be appended to data values when generating labels.  (Optional)")
   print("  -o OFFSET, --offset OFFSET")
   print("                     Floating point value used as an offset when calculating raw data values from SLD values.  (Optional)")
   print("  -f FACTOR, --factor FACTOR")
   print("                     Floating point value used as factor when calculating raw data values from SLD values.  (Optional)")
   print("  -r RGBA_ORDER , --rgba_order RGBA_ORDER")
   print("                     The RGBA ordering to be used when parsing the SLD v1.1.0 fallbackValue.")
   print("                     The alpha value is optional.  Sample values \"RGB\", \"ARGB\"")
   print("  -p PRECISION, --precision PRECISION")
   print("                     The number of decimal places to round values to plus the format specifier for floating point (f) ")
   print("                     or exponential (e).  Example: '2f' or '3e'  (Optional)")
   print("  -d DENSIFY, --densify DENSIFY")
   print("                     The algorithm used to densify an SLD into a GIBS colormap by adding additional colors and data steps.")
   print("                     Format: '[ors][0-9]*'. The first character specifies the algorithm (o = override / r = ramp / s = step).")
   print("                     An integer value follows the algorithm specifying how much to densify.  Example: 'r20' or 's5'   (Optional)")


def main(argv):

    gibsColorMaps = []
    
    sldFile      = None
    colormapFile = None
    units        = None
    layerName    = ""
    offset       = 0.0
    factor       = 1.0
    rgbaOrder    = "RGBA"
    format       = "{}"
    densify      = None


    try:
        opts, args = getopt.getopt(argv,"hs:c:l:u:o:p:f:r:d:",["sld=","colormap=","layer=","units=","offset=","precision=","factor=","rgba_order=","densify="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-s", "--sld"):
            sldFile = arg
        elif opt in ("-c", "--colormap"):
            colormapFile = arg
        elif opt in ("-l", "--layer"):
            layerName = arg
        elif opt in ("-u", "--units"):
            units = arg
        elif opt in ("-f", "--factor"):
            factor = float(arg)
        elif opt in ("-o", "--offset"):
            offset = float(arg)
        elif opt in ("-p", "--precision"):
            format = "{:." + arg + "}"
        elif opt in ("-r", "--rgba_order"):
            rgbaOrder = arg        
        elif opt in ("-d", "--densify"):
            if not re.match("[sro][0-9]*", arg):
                print("Invalid densification.  Please try again.")
                exit(-1)
            else:
                densify = arg

    if not sldFile:
       print("SLD File must be provided")
       sys.exit(-1)

    sldXmldoc = minidom.parse(sldFile)
    attrDict = dict(list(sldXmldoc.documentElement.attributes.items()))
    
    if 'version' in attrDict:
        if attrDict['version'] == "1.0.0":
            gibsColorMaps = parseSLD_v1_0_0(sldFile, layerName, units, offset, factor, format)
        elif attrDict['version'] == "1.1.0":
            gibsColorMaps = parseSLD_v1_1_0(sldFile, layerName, units, offset, factor, rgbaOrder, format, densify)
        else:
            print(("Invalid version specified: " + attrDict['version']))
            exit(-1)
        
        generateColorMap(gibsColorMaps, units, format, colormapFile)
    else:
        print("Version not specified in the SLD")
        exit(-1)


if __name__ == "__main__":
   main(sys.argv[1:])
