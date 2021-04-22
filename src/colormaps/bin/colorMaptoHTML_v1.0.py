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
   value       = ""
   label       = ""
   ref         = ""

   def __hash__(self):
      return hash(self.value)

   def __cmp__(self, other):
      return self.value.cmp(other.value)

   def __eq__(self, other):
      return self.value.eq(other.value)


class ColorMap():
   units           = ""
   colormapentries = []

   def __hash__(self):
      return hash(self.title)

#    def __cmp__(self, other):
#        return self.name.cmp(other.name)

#    def __eq__(self, other):
#        return self.name.eq(other.name)



## Functions ##
def getText(nodelist):
   rc = []
   for node in nodelist:
      if node.nodeType == node.TEXT_NODE:
         rc.append(node.data)
   return ''.join(rc)


## START Parse Color Maps ##
def parseColorMap(sourceXml) :

   xmldoc     = minidom.parse(sourceXml)

   colorMapAttrDict = dict(xmldoc.documentElement.attributes.items())

   colorMap = ColorMap()
   colorMap.colormapentries = []
   colorMap.units   = colorMapAttrDict.get('units', '')

   for entryNode in xmldoc.documentElement.getElementsByTagName("ColorMapEntry") :

      entryAttrDict = dict(entryNode.attributes.items())

      cmEntry = ColorMapEntry()

      #t required, but defaults to false
      if 'transparent' in entryAttrDict :
         cmEntry.transparent = entryAttrDict['transparent']
      else:
         cmEntry.transparent = False

      cmEntry.rgb = entryAttrDict.get('rgb', '')
      cmEntry.value = entryAttrDict.get('value', '')
      cmEntry.label = entryAttrDict.get('label', '')
      cmEntry.ref = entryAttrDict.get('ref', '')

      colorMap.colormapentries.append(cmEntry)

   return colorMap

## END Parse Color Map ##


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
def generateHTML(colorMap, product) :

   print("<!doctype html>")
   print("<html>")
   print("<head>")
   print('<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>')
   print('<link rel="stylesheet" type="text/css" href="resources/colormap.css">')
   print("</head>")
   print("<body>")

   print("<h1>" + product + "</h1>")

   print("<p>Download Color Map file <a href=\"../" + product + "\">here</a><br><br>")

   print("<h2> ColorMap : Units '" + escape(colorMap.units) + "'</h2>")
   print("<h3> Entries </h3>")

   print("<table>")

   print("  <tr>")
   print("    <th>RGB</th>")
   print("    <th class='transparency'>Transparent</th>")
   print("    <th class='data-value'>Value</th>")
   print("    <th class='data-value'>Label</th>")
   print("  </tr>")

   for entry in colorMap.colormapentries :
      print("  <tr>")
      print("    <td class='color' bgcolor=" + rgb_to_hex(entry.rgb) + ">" + \
            "<font color=\"" + ("black" if is_bright(entry.rgb) else "white") + "\">" + \
            entry.rgb + "</font></td>")
      print("    <td class='transparency'>{0}</td>".format(entry.transparent))
      print("    <td class='data-value'>{0}</td>".format(escape(entry.value) if entry.value is not None else ""))
      print("    <td class='data-value'>{0}</td>".format(escape(entry.label)))
      print("  </tr>")


   print("</table>")
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

   colorMap = parseColorMap(colormapFile)
   generateHTML(colorMap, os.path.basename(colormapFile))

if __name__ == "__main__":
   main(sys.argv[1:])