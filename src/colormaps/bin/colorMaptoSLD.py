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


class GIBS_ColorMapEntry():
    rgb         = [-1,-1,-1]
    label       = ""
    value       = None
    sourceValue = None
    transparent = False
    nodata      = False
    
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
        print("Invalid Hex Value")
        r=g=b=-1

    return [r,g,b]


def RGBToHex(rgbaValue, rgbaOrder):

    hexValue = "#"

    for c in rgbaOrder:
        hexValue = hexValue + ('%02X' % rgbaValue[rgbaOrder.find(c)])

    return hexValue


## START Generate SLD v1.0.0 ##
def generateSLD_v1_0_0(gibsColorMaps, layerName, rgbaOrder) :


    print("<StyledLayerDescriptor version=\"1.0.0\" ")
    print("   xsi:schemaLocation=\"http://www.opengis.net/sld StyledLayerDescriptor.xsd\"")
    print("   xmlns=\"http://www.opengis.net/sld\"")
    print("   xmlns:ogc=\"http://www.opengis.net/ogc\"")
    print("   xmlns:se=\"http://www.opengis.net/se\"")
    print("   xmlns:xlink=\"http://www.w3.org/1999/xlink\"")
    print("   xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">")

    print("  <NamedLayer>")
    print(("    <Name>" + layerName + "</Name>"))
    print("    <UserStyle>")    
    print("      <Title>GIBS Imagery Style</Title>")
    print("      <FeatureTypeStyle>")    
    print("        <Rule>")        
    print("          <RasterSymbolizer>")   
    print("            <Opacity>1.0</Opacity>")          
    print("            <ColorMap>")  

    for colorMap in gibsColorMaps:
        for cmEntry in colorMap.cmEntries:
            
            
            m = re.match(r"[\(\[]([0-9\.\-]*|\-INF)[,]*([0-9\.\-]*|\+?INF)[\)\]]", cmEntry.value)
            
            # the "INF" value is not relevant in SLDs
            if "INF" not in m.group(1):
                # if this is last entry:
                if colorMap == gibsColorMaps[-1] and cmEntry == colorMap.cmEntries[-1]:
                
                    # if it's a range, print out the extra colormap entry unless te extra is "INF"
                    if len(m.group(2)) > 0 and "INF" not in m.group(2):
                        quantity = str(m.group(1))
                        label    = str(m.group(1)) + " - " + str(m.group(2))
                    
                        print(("              <ColorMapEntry " + 
                                "color=\"" + RGBToHex(cmEntry.rgb, "RGB") + "\" " + 
                                "quantity=\""+ quantity + "\" " + 
                                "label=\""+ label + "\" />"))        
                                
                        quantity = str(m.group(2))
                        label    = str(m.group(2))
                    
                        print(("              <ColorMapEntry " + 
                                "color=\"" + RGBToHex(cmEntry.rgb, "RGB") + "\" " + 
                                "quantity=\""+ quantity + "\" " + 
                                "label=\""+ label + "\" />"))  
                    else:  
                        quantity = str(m.group(1))
                        label    = str(m.group(1))
                    
                        print(("              <ColorMapEntry " + 
                                "color=\"" + RGBToHex(cmEntry.rgb, "RGB") + "\" " + 
                                "quantity=\""+ quantity + "\" " + 
                                "label=\""+ label + "\" />"))            
                else:
                    quantity = str(m.group(1))
                    label    = str(m.group(1)) + " - " + str(m.group(2))#cmEntry.label
                    
                    print(("              <ColorMapEntry " + 
                            "color=\"" + RGBToHex(cmEntry.rgb, "RGB") + "\" " + 
                            "quantity=\""+ quantity + "\" " + 
                            "label=\""+ label + "\" />"))
 
    print("            </ColorMap>")     
    print("          </RasterSymbolizer>")    
    print("        </Rule>")    
    print("      </FeatureTypeStyle>")    
    print("    </UserStyle>")    
    print("  </NamedLayer>")
    print("</StyledLayerDescriptor>")
    
## END Generate SLD v1.0.0 ##

## START Generate SLD v1.1.0 ##
def generateSLD_v1_1_0(gibsColorMaps, layerName, rgbaOrder) :

    print("<StyledLayerDescriptor version=\"1.1.0\" ")
    print("   xsi:schemaLocation=\"http://www.opengis.net/sld StyledLayerDescriptor.xsd\"")
    print("   xmlns=\"http://www.opengis.net/sld\"")
    print("   xmlns:ogc=\"http://www.opengis.net/ogc\"")
    print("   xmlns:se=\"http://www.opengis.net/se\"")
    print("   xmlns:xlink=\"http://www.w3.org/1999/xlink\"")
    print("   xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">")

    print("  <NamedLayer>")
    print(("    <se:Name>" + layerName + "</se:Name>"))
    print("    <UserStyle>")    
    print("      <se:Name>GIBS Imagery Style</se:Name>")
    print("      <se:CoverageStyle>")    
    print("        <se:Rule>")        
    print("          <se:RasterSymbolizer>")   
    print("            <se:Opacity>1.0</se:Opacity>")          
    print("            <se:ColorMap>")       
    
    nodata_str = ""
    contents_str = ""

    firstValue = True
    for colorMap in gibsColorMaps:

        for cmEntry in colorMap.cmEntries:
            if cmEntry.nodata:
                rgba = cmEntry.rgb
                rgba.append(0)
                
                fallbackValue = RGBToHex(rgba,rgbaOrder)

                nodata_str = "              <se:Categorize fallbackValue=\"" + fallbackValue + "\">"
                nodata_str += "\n                <se:LookupValue>Rasterdata</se:LookupValue>"

            elif firstValue:
                contents_str += "                <se:Value>" + RGBToHex(cmEntry.rgb, "RGB") + "</se:Value>"
                firstValue = False
            else:
                threshold = str(re.match(r"\[([0-9\.\-\+e]*),[0-9\.\-\+e]*", cmEntry.value).group(1))
                contents_str += "\n                <se:Threshold>" + threshold + "</se:Threshold>"
                contents_str += "\n                <se:Value>" + RGBToHex(cmEntry.rgb, "RGB") + "</se:Value>"

    print(nodata_str)
    print(contents_str)
    print("              </se:Categorize>")     
    print("            </se:ColorMap>")     
    print("          </se:RasterSymbolizer>")    
    print("        </se:Rule>")    
    print("      </se:CoverageStyle>")    
    print("    </UserStyle>")    
    print("  </NamedLayer>")
    print("</StyledLayerDescriptor>")

    
## END Generate SLD v1.1.0 ##


def parseColorMap(sourceXml):

    gibsColorMaps = []
    
    xmldoc     = minidom.parse(sourceXml)

    for cMapNode in xmldoc.documentElement.getElementsByTagName("ColorMap") :
        
        entriesNode     = cMapNode.getElementsByTagName("Entries")[0]
        entriesAttrDict = dict(list(cMapNode.attributes.items()))
        
        gibsCMap            = GIBS_ColorMap()
        gibsCMap.cmEntries  = []
        
        if 'minLabel' in entriesAttrDict:
            gibsCMap.minLabel   = entriesAttrDict['minLabel']
            gibsCMap.maxLabel   = entriesAttrDict['maxLabel']

    
        for cMapEntryNode in cMapNode.getElementsByTagName("ColorMapEntry") :
            cMapEntryAttrDict = dict(list(cMapEntryNode.attributes.items()))

            gibsCMapEntry             = GIBS_ColorMapEntry()
            
            m = re.match(r"([0-9]*),([0-9]*),([0-9]*)", cMapEntryAttrDict['rgb'])
                   
            gibsCMapEntry.rgb         = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
            gibsCMapEntry.transparent = (cMapEntryAttrDict['transparent'] == 'true')
            
            if 'nodata' in cMapEntryAttrDict:
                gibsCMapEntry.nodata      = (cMapEntryAttrDict['nodata'] == 'true')
                
            if 'label' in cMapEntryAttrDict:
                gibsCMapEntry.label       = cMapEntryAttrDict['label']
                
            if 'value' in cMapEntryAttrDict:
                gibsCMapEntry.value       = cMapEntryAttrDict['value']
            
            if 'sourceValue' in cMapEntryAttrDict:
                gibsCMapEntry.sourceValue = cMapEntryAttrDict['sourceValue']
      
            gibsCMap.cmEntries.append(gibsCMapEntry)
                        
        gibsColorMaps.append(gibsCMap)
        
    return gibsColorMaps
        
## END Parse ColorMap ##



def main(argv):

    gibsColorMaps = []
    
    cMapFile  = ""
    layerName = ""
    rgbaOrder  = "RGBA"
    version   = None


    try:
        opts, args = getopt.getopt(argv,"hc:l:r:s:",["colormap=","layer=","rgba_order=","spec_version="])
    except getopt.GetoptError:
        print("Usage: colorMapToSLD.py -c <colormap> -l <layer> -r <rgb_order> -s <version>")
        print("\nOptions:")
        print("  -h, --help             show this help message and exit")
        print("  -c COLORMAP_FILE, --colormap COLORMAP_FILE")
        print("							Path to colormap file to be converted")
        print("  -l LAYER_NAME, --layer LAYER_NAME")
        print("							Value to be placed in the NamedLayer/Name element")
        print("  -r RGBA_ORDER , --rgba_order RGBA_ORDER")
        print("    						The RGBA ordering to be used when generating the fallbackValue.")
        print("    						The alpha value is optional.  Sample values \"RGB\", \"ARGB\"")
        print("  -s SLD_SPEC_VERSION, --spec_version SLD_SPEC_VERSION")
        print("  						SLD specification version: \"1.0.0\" or \"1.1.0\"")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("Usage: colorMapToSLD.py -c <colormap> -l <layer> -r <rgb_order> -s <version>")
            print("\nOptions:")
            print("  -h, --help             show this help message and exit")
            print("  -c COLORMAP_FILE, --colormap COLORMAP_FILE")
            print("							Path to colormap file to be converted")
            print("  -l LAYER_NAME, --layer LAYER_NAME")
            print("							Value to be placed in the NamedLayer/Name element")
            print("  -r RGBA_ORDER , --rgba_order RGBA_ORDER")
            print("    						The RGBA ordering to be used when generating the fallbackValue.")
            print("    						The alpha value is optional.  Sample values \"RGB\", \"ARGB\"")
            print("  -s SLD_SPEC_VERSION, --spec_version SLD_SPEC_VERSION")
            print("  						SLD specification version: \"1.0.0\" or \"1.1.0\"")
            sys.exit()
        elif opt in ("-c", "--colormap"):
            cMapFile = arg
        elif opt in ("-l", "--layer"):
            layerName = arg
        elif opt in ("-r", "--rgba_order"):
            rgbaOrder = arg
        elif opt in ("-s", "--spec_version"):
            version = arg


    gibsColorMaps = parseColorMap(cMapFile)

    if version:
        if version == "1.0.0":
            generateSLD_v1_0_0(gibsColorMaps, layerName, rgbaOrder)
        elif version == "1.1.0":
            generateSLD_v1_1_0(gibsColorMaps, layerName, rgbaOrder)
        else:
            print(("Invalid version specified: " + version + ". Must be 1.1.0 or 1.0.0"))
            exit(-1)
    else:
        print("Version not specified")
        exit(-1)
        

if __name__ == "__main__":
   main(sys.argv[1:])
