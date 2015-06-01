#!/usr/bin/python


from xml.dom import minidom
from xml.dom import Node
import re
import sys, getopt


class SLD_v1_0_0_ColorMapEntry():
    quantity  = None
    opacity   = None
    rgb       = [-1,-1,-1]
    
    def __hash__(self):
        return hash(self.quantity)
        
    def __cmp__(self, other):
        return self.quantity.cmp(other.quantity)

    def __eq__(self, other):
        return self.quantity.eq(other.quantity)


class GIBS_ColorMapEntry():
    rgb         = [-1,-1,-1]
    label       = ""
    value       = None
    sourceValue = None
    transparent = False
    nodata      = False
    
    def __hash__(self):
        return hash(self.rgb)
        
    def __cmp__(self, other):
        return self.rgb.cmp(other.rgb)

    def __eq__(self, other):
        return self.rgb.eq(other.rgb)

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
		print("Invalid Hex Value")
		r=g=b=-1

    return [r,g,b]



## START Parse SLD v1.0.0 ##
def parseSLD_v1_0_0(sourceXml, layerName, units, offset, factor) :
    
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
                    attrDict = dict(colorMapEntryNode.attributes.items())

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
                        
                prevValue   = sldCMapEntries[0].quantity
                prevOpacity = (sldCMapEntries[0].opacity == 0.0)
                prevRGB     = sldCMapEntries[0].rgb
                        
                gibsCMap.minLabel = "" + str(prevValue) + ("" if not units else (" " + units))
                        
                for sldCMapEntry in sldCMapEntries[1:-1]:
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = str(prevValue) + " - " + str(sldCMapEntry.quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [str(prevValue), str(sldCMapEntry.quantity)]
                    gibsCMapEntry.sourceValue = [str((prevValue - offset) / factor), str((sldCMapEntry.quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                            
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                           
                    prevValue   = sldCMapEntry.quantity
                    prevOpacity = (sldCMapEntry.opacity == 0.0)
                    prevRGB     = sldCMapEntry.rgb

                
                
                # If the last entry has the same color as it's previous entry, then update the last 
                # colormap entry to include this upper bound
                if prevRGB == sldCMapEntries[-1].rgb:
                
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = "&gt;= " + str(prevValue) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [prevValue,sldCMapEntries[-1].quantity]
                    gibsCMapEntry.sourceValue = [prevValue, str((sldCMapEntries[-1].quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                else:
                    # Add ColorMapEntry for [-1] entry
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = prevRGB
                    gibsCMapEntry.label       = str(prevValue) + " - " + str(sldCMapEntries[-1].quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [str(prevValue), str(sldCMapEntries[-1].quantity)]
                    gibsCMapEntry.sourceValue = [str((prevValue - offset) / factor), str((sldCMapEntries[-1].quantity - offset) / factor)]
                    gibsCMapEntry.transparent = prevOpacity
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                    gibsCMapEntry             = GIBS_ColorMapEntry()
                    gibsCMapEntry.rgb         = sldCMapEntries[-1].rgb
                    gibsCMapEntry.label       = str(sldCMapEntries[-1].quantity) + ("" if not units else (" " + units))	
                    gibsCMapEntry.value       = [sldCMapEntries[-1].quantity]
                    gibsCMapEntry.sourceValue = [str((sldCMapEntries[-1].quantity - offset) / factor), "+INF"]
                    gibsCMapEntry.transparent = (sldCMapEntries[-1].opacity == 0.0)
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                
                gibsCMap.maxLabel    = gibsCMap.cmEntries[-1].label
                gibsCMap.showLegend  = True
                        
                gibsColorMaps.append(gibsCMap)


    return gibsColorMaps

## END Parse SLD v1.0.0 ##



## START Parse SLD v1.1.0 ##
def parseSLD_v1_1_0(sourceXml, layerName, units, offset, factor, rgbOrder) :
    
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
                attrDict = dict(categorizeNode.attributes.items())
                        
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
                    
                    gibsCMap  = GIBS_ColorMap()
                    gibsCMap.cmEntries = []
                    gibsCMap.cmEntries.append(gibsCMapEntry)
                    gibsColorMaps.append(gibsCMap)
                    
                    
                
                # Process the SLD entries into the XML ColorMap
                gibsCMap  = GIBS_ColorMap()
                        
                prevValue      = "-INF"
                currRGB        = [-1,-1,-1]

                for catChildNode in [ n for n in categorizeNode.childNodes if n.nodeType == Node.ELEMENT_NODE ]:
                                   
                    # <se:Value>#00ff00</se:Value>
                    if catChildNode.nodeName == "se:Value":
                        currRGB = hexToRGB(catChildNode.firstChild.nodeValue)
                    
                    # <se:Threshold>52</se:Threshold>
                    if catChildNode.nodeName == "se:Threshold":
                        currValue = float(catChildNode.firstChild.nodeValue)
                        
                        gibsCMapEntry             = GIBS_ColorMapEntry()
                        gibsCMapEntry.rgb         = currRGB
                        gibsCMapEntry.transparent = (defaultOpacity == 0.0)
                        
                        if prevValue == "-INF":
                            gibsCMap.minLabel         = "&lt; " + str(currValue) + ("" if not units else (" " + units))
                        
                            gibsCMapEntry.label       = "&lt; " + str(currValue) + ("" if not units else (" " + units))
                            gibsCMapEntry.value       = [prevValue, str(currValue)]
                            gibsCMapEntry.sourceValue = [prevValue, str((currValue - offset) / factor)]
                        else:
                            gibsCMapEntry.label       = str(prevValue) + " - " + str(currValue) + ("" if not units else (" " + units))	
                            gibsCMapEntry.value       = [str(prevValue), str(currValue)]
                            gibsCMapEntry.sourceValue = [str((prevValue - offset) / factor), str((currValue - offset) / factor)]
                            
                        
                        gibsCMap.cmEntries.append(gibsCMapEntry)
                        
                        prevValue = currValue
                        
                gibsCMapEntry             = GIBS_ColorMapEntry()
                gibsCMapEntry.rgb         = currRGB
                gibsCMapEntry.transparent = (defaultOpacity == 0.0)
                        
                gibsCMap.maxLabel         = "&gt;= " + str(prevValue) + ("" if not units else (" " + units))	
                gibsCMap.showUnits        = True	
                gibsCMap.showLegend       = True
                gibsCMapEntry.label       = "&gt;= " + str(prevValue) + ("" if not units else (" " + units))	
                gibsCMapEntry.value       = [str(prevValue), "+INF"]
                gibsCMapEntry.sourceValue = [str((prevValue - offset) / factor), "+INF"]
                            
                gibsCMap.cmEntries.append(gibsCMapEntry)
                        
            	gibsColorMaps.append(gibsCMap)


    return gibsColorMaps

## END Parse SLD v1.1.0 ##



def generateColorMap(gibsColorMaps, units):

    print("<ColorMaps>")
    
    for colorMap in gibsColorMaps:

        # <ColorMap title="Sea Ice Concentration" units="%">
        print("  <ColorMap" + 
            ((" units=\"" + units + "\"") if colorMap.showUnits and units else "") + ">")

        # <Entries minLabel="0 %" maxLabel="100 %">      
        print("    <Entries" + 
            ("" if not colorMap.minLabel else (" minLabel=\"" + colorMap.minLabel + "\" ")) + 
            ("" if not colorMap.maxLabel else (" maxLabel=\"" + colorMap.maxLabel + "\"")) + 	">")
    
        refNum = 1;
        for cMapEntry in colorMap.cmEntries:
            # <ColorMapEntry rgb="9,9,255" transparent="false" sourceValue="[9,10)" value="[9,10)" label="3.6 %" ref="1"/>
        
            rgb = str(cMapEntry.rgb[0]) + "," + str(cMapEntry.rgb[1]) + "," + str(cMapEntry.rgb[2])
            
            if cMapEntry.value: 
                if len(cMapEntry.value) == 1:
                    value = "[" + str(cMapEntry.value[0]) + "]"
                else:
                    value = "[" + str(cMapEntry.value[0]) + "," + str(cMapEntry.value[1]) + ")"
            
            if cMapEntry.sourceValue: 
                if len(cMapEntry.sourceValue) == 1:
                    sourceValue = "[" + str(cMapEntry.sourceValue[0]) + "]"
                else:
                    sourceValue = "[" + str(cMapEntry.sourceValue[0]) + "," + str(cMapEntry.sourceValue[1]) + ")"
        
            print("      <ColorMapEntry rgb=\"" + rgb + "\" " + 
               "transparent=\"" + ("true" if cMapEntry.transparent else "false") + "\" " + 
               ("" if not cMapEntry.sourceValue else ("sourceValue=\"" + value + "\" ")) + 
               ("" if not cMapEntry.value else ("value=\"" + value + "\" ")) + 
               "label=\"" + cMapEntry.label + "\" " + 
               ("" if not cMapEntry.nodata else ("nodata=\"true\" ")) +
               ("" if not colorMap.showLegend else ("ref=\"" + str(refNum) + "\" ")) + 
               "/>")
            
            refNum = refNum + 1

        print("    </Entries>")
        
        
        if colorMap.showLegend:
            # <Entries minLabel="0 %" maxLabel="100 %">      
            print("    <Legend type=\"continuous\" " + 
                ("" if not colorMap.minLabel else (" minLabel=\"" + colorMap.minLabel + "\" ")) + 
                ("" if not colorMap.maxLabel else (" maxLabel=\"" + colorMap.maxLabel + "\"")) + 	">")
    
            refNum = 1;
            for cMapEntry in colorMap.cmEntries:
        
                rgb = str(cMapEntry.rgb[0]) + "," + str(cMapEntry.rgb[1]) + "," + str(cMapEntry.rgb[2])
            
                if cMapEntry.value: 
                    if len(cMapEntry.value) == 1:
                        value = "[" + str(cMapEntry.value[0]) + "]"
                    else:
                        value = "[" + str(cMapEntry.value[0]) + "," + str(cMapEntry.value[1]) + ")"
        
                print("      <LegendEntry rgb=\"" + rgb + "\" " + 
                   ("" if not cMapEntry.value else ("value=\"" + value + "\" ")) + 
                   ("" if not colorMap.showLegend else ("id=\"" + str(refNum) + "\" ")) + 
                   "/>")
            
                refNum = refNum + 1

            print("    </Legend>")
    
        print("  </ColorMap>")
        
    print("</ColorMaps>")


def main(argv):

    gibsColorMaps = []
    
    sldFile   = ""
    units     = None
    layerName = ""
    offset    = 0.0
    factor    = 1.0
    rgbaOrder  = "RGBA"


    try:
        opts, args = getopt.getopt(argv,"hs:l:u:o:f:r:",["sld=","layer=","units=","offset=","factor=","rgba_order="])
    except getopt.GetoptError:
        print("Usage: SLDtoColorMap.py -s <sld> -l <layer> -u <units> -o <offset> -f <factor> -r <rgba_order>")
        print("\nOptions:")
        print("  -h, --help             show this help message and exit")
        print("  -s SLD_FILE, --sld SLD_FILE")
        print("  						Path to SLD file to be converted")
        print("  -l LAYER_NAME, --layer LAYER_NAME")
        print("							Value to be placed in the NamedLayer/Name element")
        print("  -u UNITS, --units UNITS")
        print("							Units to be appended to data values when generating labels.  (Optional)")
        print("  -o OFFSET, --offset OFFSET")
        print("							Floating point value used as an offset when calculating raw data values from SLD values.  (Optional)")
        print("  -f FACTOR, --factor FACTOR")
        print("							Floating point value used as factor when calculating raw data values from SLD values.  (Optional)")
        print("  -r RGBA_ORDER , --rgba_order RGBA_ORDER")
        print("							The RGBA ordering to be used when parsing the SLD v1.1.0 fallbackValue.")
        print("							The alpha value is optional.  Sample values \"RGB\", \"ARGB\"")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("Usage: SLDtoColorMap.py -s <sld> -l <layer> -u <units> -o <offset> -f <factor> -r <rgba_order>")
            print("\nOptions:")
            print("  -h, --help             show this help message and exit")
            print("  -s SLD_FILE, --sld SLD_FILE")
            print("							Path to SLD file to be converted")
            print("  -l LAYER_NAME, --layer LAYER_NAME")
            print("							Value to be placed in the NamedLayer/Name element")
            print("  -u UNITS, --units UNITS")
            print("							Units to be appended to data values when generating labels.  (Optional)")
            print("  -o OFFSET, --offset OFFSET")
            print("							Floating point value used as an offset when calculating raw data values from SLD values.  (Optional)")
            print("  -f FACTOR, --factor FACTOR")
            print("							Floating point value used as factor when calculating raw data values from SLD values.  (Optional)")
            print("  -r RGBA_ORDER , --rgba_order RGBA_ORDER")
            print("							The RGBA ordering to be used when parsing the SLD v1.1.0 fallbackValue.")
            print("							The alpha value is optional.  Sample values \"RGB\", \"ARGB\"")
            sys.exit()
        elif opt in ("-s", "--sld"):
            sldFile = arg
        elif opt in ("-l", "--layer"):
            layerName = arg
        elif opt in ("-u", "--units"):
            units = arg
        elif opt in ("-f", "--factor"):
            factor = float(arg)
        elif opt in ("-o", "--offset"):
            offset = float(arg)
        elif opt in ("-r", "--rgba_order"):
            rgbaOrder = arg

    sldXmldoc = minidom.parse(sldFile)
    attrDict = dict(sldXmldoc.documentElement.attributes.items())
    
    if 'version' in attrDict:
        if attrDict['version'] == "1.0.0":
            gibsColorMaps = parseSLD_v1_0_0(sldFile, layerName, units, offset, factor)
        elif attrDict['version'] == "1.1.0":
            gibsColorMaps = parseSLD_v1_1_0(sldFile, layerName, units, offset, factor, rgbaOrder)
        else:
            print("Invalid version specified: " + attrDict['version'])
            exit(-1)
        
        generateColorMap(gibsColorMaps, units)
    else:
        print("Version not specified in the SLD")
        exit(-1)


if __name__ == "__main__":
   main(sys.argv[1:])
