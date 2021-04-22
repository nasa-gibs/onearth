#!/usr/bin/env python3

'''
Created on Nov 15, 2013

@author: mcechini
'''

from xml.dom import minidom
from html import escape
import sys, getopt, os


# Hack for Python 2
if sys.version_info[0] < 3:
   reload(sys)
   sys.setdefaultencoding('utf8')


## Class Definitions ##

class ColorMapEntry():
   rgb         = ""
   transparent = False
   sourceValue = ""
   value       = ""
   ref         = ""
   nodata      = False

   def __hash__(self):
      return hash(self.sourceValue)

   def __cmp__(self, other):
      return self.sourceValue.cmp(other.sourceValue)

   def __eq__(self, other):
      return self.sourceValue.eq(other.sourceValue)


class Entries():
   colormapentries = []

   def __hash__(self):
      return hash(self.minLabel)

   def __cmp__(self, other):
      return self.minLabel.cmp(other.minLabel)

   def __eq__(self, other):
      return self.minLabel.eq(other.minLabel)

class LegendEntry():
   rgb         = ""
   tooltip     = ""
   label       = ""
   id          = ""
   showTick    = False
   showValue   = False

   def __hash__(self):
      return hash(self.tooltip)

   def __cmp__(self, other):
      return self.tooltip.cmp(other.tooltip)

   def __eq__(self, other):
      return self.tooltip.eq(other.tooltip)


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

#    def __cmp__(self, other):
#        return self.name.cmp(other.name)

#    def __eq__(self, other):
#        return self.name.eq(other.name)

class ColorMaps():
   colormaps = []
   product   = ""

   def __hash__(self):
      return hash(self.product)

   def __cmp__(self, other):
      return self.product.cmp(other.product)

   def __eq__(self, other):
      return self.product.eq(other.product)

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

      colorMapAttrDict = dict(colorMapNode.attributes.items())
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

   entriesAttrDict = dict(entriesNode.attributes.items())

   entries = Entries()
   entries.colormapentries = []

   for entryNode in entriesNode.getElementsByTagName("ColorMapEntry") :

      entryAttrDict = dict(entryNode.attributes.items())

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
      cmEntry.ref = entryAttrDict.get('ref', '')

      entries.colormapentries.append(cmEntry)

   return entries

## END Parse Entries ##


## START Parse Legend ##
def parseLegend(legendNode):

   legendAttrDict = dict(legendNode.attributes.items())

   legend = Legend()
   legend.type     = legendAttrDict.get('type', '')
   legend.minLabel = legendAttrDict.get('minLabel', '')
   legend.maxLabel = legendAttrDict.get('maxLabel', '')
   legend.legendentries = []

   for entryNode in legendNode.getElementsByTagName("LegendEntry") :

      legendAttrDict = dict(entryNode.attributes.items())

      legendEntry = LegendEntry()

      legendEntry.rgb       = legendAttrDict.get('rgb', '')
      legendEntry.tooltip   = legendAttrDict.get('tooltip', '')
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
def generateHTML() :

   for colorMaps in colorMapsList :
      print("<!doctype html>")
      print("<html>")
      print("<head>")
      print('<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>')
      print('<link rel="stylesheet" type="text/css" href="resources/colormap.css">')
      print("</head>")
      print("<body>")

      print("<h1>" + colorMaps.product + "</h1>")

      print("<p>Download Color Map file <a href=\"../" + colorMaps.product + "\">here</a><br><br>")

      for colorMap in colorMaps.colormaps :
         print("<h2> ColorMap : Title '{0}'  Units '{1}'</h2>".format(escape(colorMap.title),
                                                                      escape(colorMap.units)))
         print("<h3> Entries : </h3>")


         print("<table>")

         print("  <tr>")
         print("    <th>RGB</th>")
         print("    <th class='transparency'>Transparent</th>")
         print("    <th class='data-value'>SourceValue</th>")
         print("    <th class='data-value'>Value</th>")
         print("    <th class='data-value'>Reference</th>")
         print("    <th class='data-value'>NoData</th>")
         print("  </tr>")


         for entry in colorMap.entries.colormapentries :
            print("  <tr>")
            print("    <td class='color' bgcolor=" + rgb_to_hex(entry.rgb) + ">" + \
                  "<font color=\"" + ("black" if is_bright(entry.rgb) else "white") + "\">" + \
                  entry.rgb + "</font></td>")
            print("    <td class='data-value'>" + ("True" if entry.transparent else "False") + "</td>")
            print("    <td class='data-value'>{0}</td>".format(escape(entry.sourceValue) if entry.sourceValue is not None else ""))
            print("    <td class='data-value'>{0}</td>".format(escape(entry.value) if entry.value is not None else ""))
            print("    <td class='data-value'>{0}</td>".format(escape(entry.ref) if entry.ref is not None else ""))
            print("    <td class='data-value'>" + ("True" if entry.nodata else "False") + "</td>")
            print("  </tr>")

         print("</table>")

         if colorMap.legend == None:
            print("<h3>No Legend</h3>")
         else:
            print("<h3> Legend : Type '{0}'  MinLabel '{1}'  MaxLabel '{2}'</h3>".format(escape(colorMap.legend.type),
                                                                                         escape(colorMap.legend.minLabel),
                                                                                         escape(colorMap.legend.maxLabel)))


            print("<table>")

            print("  <tr>")
            print("    <th>RGB</th>")
            print("    <th class='data-value'>ToolTip</th>")
            print("    <th class='data-value'>showTick</th>")
            print("    <th class='data-value'>showLabel</th>")
            print("    <th class='data-value'>Label</th>")
            print("    <th class='data-value'>ID</th>")
            print("  </tr>")


            for entry in colorMap.legend.legendentries :
               print("  <tr>")
               print("    <td class='color' bgcolor=" + rgb_to_hex(entry.rgb) + ">" +
                     "<font color=\"" + ("black" if is_bright(entry.rgb) else "white") + "\">" +
                     entry.rgb + "</font></td>")
               print("    <td class='data-value'>{0}</td>".format(escape(entry.tooltip)))
               print("    <td class='data-value'>" + ("True" if entry.showTick else "False") + "</td>")
               print("    <td class='data-value'>" + ("True" if entry.showLabel else "False") + "</td>")
               print("    <td class='data-value'>{0}</td>".format(escape(entry.label)))
               print("    <td class='data-value'>{0}</td>".format(escape(entry.id) if entry.id is not None else ""))
               print("  </tr>")

            print("</table>")


         if not colorMap == colorMaps.colormaps[-1]:
            print("<hr>")
            print("<br>")
            print("<br>")
            print("<br>")

      print("</body>")
      print("</html>")

def main(argv):

   colormapFile = ""

   try:
      opts, args = getopt.getopt(argv,"hi:c:",["colormap="])
   except getopt.GetoptError:
      print("Usage: colorMaptoHTML.py -c <colormap>")
      print("\nOptions:")
      print("  -h, --help             show this help message and exit")
      print("  -c COLORMAP_FILE, --colormap COLORMAP_FILE")
      print("							Path to colormap file to be converted")
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print("Usage: colorMaptoHTML.py -c <colormap>")
         print("\nOptions:")
         print("  -h, --help             show this help message and exit")
         print("  -c COLORMAP_FILE, --colormap COLORMAP_FILE")
         print("							Path to colormap file to be converted")
         sys.exit()
      elif opt in ("-c", "--colormap"):
         colormapFile = arg

   parseColorMaps(colormapFile, colormapFile)
   generateHTML()

if __name__ == "__main__":
   main(sys.argv[1:])