#!/bin/env python

# Copyright (c) 2002-2014, California Institute of Technology.
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
# oe_generate_legend.py
# The OnEarth Legend Generator.
#
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014

import sys
import urllib
import xml.dom.minidom
from optparse import OptionParser
from matplotlib import pyplot
from matplotlib import rcParams
import matplotlib as mpl
import matplotlib.pyplot as plt
from StringIO import StringIO

# for SVG tooltips
try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    ET.register_namespace("","http://www.w3.org/2000/svg")

toolName = "oe_generate_legend.py"
versionNumber = "v0.4"

class ColorMap:
    """ColorMap metadata"""
    
    def __init__(self, units, colormap_entries, style):
        self.units = units
        self.colormap_entries = colormap_entries
        self.style = str(style).lower()
        
    def __repr__(self):
        if self.units != None:
            xml = '<ColorMap units="%s">' % (self.units)
        else:
            xml = '<ColorMap>'
        for colormap_entry in self.colormap_entries:
            xml = xml + '\n    ' + colormap_entry.__repr__()
        xml = xml + '\n</ColorMap>'
        return xml

    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)


class ColorMapEntry:
    """ColorMapEntry values within a ColorMap"""
    
    def __init__(self, red, green, blue, transparent, source_value, value, label):
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.transparent = transparent
        self.source_value = source_value
        self.value = value
        self.label = label
        self.color = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        if self.value != None:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" sourceValue="%s" value="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.source_value, self.value, self.label)
        else:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" sourceValue="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.source_value, self.label)
        return xml
    
    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)
    

def parse_colormap(colormap_location):
    
    try:    
        print "Reading color map:", colormap_location
        colormap_file = open(colormap_location,'r')
        dom = xml.dom.minidom.parse(colormap_file)
        colormap_file.close()
    except IOError:
        print "Accessing URL", colormap_location
        dom = xml.dom.minidom.parse(urllib.urlopen(colormap_location))
        
    colormap_element = dom.getElementsByTagName("ColorMap")[0]
    try:
        units = colormap_element.attributes['units'].value
    except KeyError:
        units = None
    print "ColorMap units:", units
    
    style = "discrete"
    colormap_entries = []
    colormapentry_elements = colormap_element.getElementsByTagName("ColorMapEntry")
    for colormapentry in colormapentry_elements:
        rgb = colormapentry.attributes['rgb'].value
        red, green, blue = rgb.split(',')
        try:
            value = colormapentry.attributes['value'].value
            if "(" in value or "[" in value:
                style = "range"
        except KeyError:
            value = None
            style = "classification"
        try:
            transparent = True if colormapentry.attributes['transparent'].value.lower() == 'true' else False
        except KeyError:
            transparent = False
        try:
            source_value = colormapentry.attributes['sourceValue'].value
        except KeyError:
            source_value = value
        try:
            label = colormapentry.attributes['label'].value
        except KeyError:
            label = value
        
        colormap_entries.append(ColorMapEntry(red, green , blue, transparent, source_value, value, label))
        
    print "ColorMap style:", style
    colormap = ColorMap(units, colormap_entries, style)
    print colormap
    
    return colormap


def generate_legend(colormap, output, output_format):
    
    # set ticklines out
    rcParams['xtick.direction'] = 'out'
    rcParams['ytick.direction'] = 'out'
    
    fig = pyplot.figure(figsize=(1.5,3))
    ax = fig.add_axes([0.2, 0.05, 0.15, 0.9])
    
    is_large_colormap = False
    has_values = False
    center_ticks = False
    bounds = []
    colors = []
    ticks = []
    ticklabels = []
    labels = []
    
    legendcolors = []
    legendlabels = []
    
    # remove transparent values
    colormap_entries = []
    for colormap_entry in colormap.colormap_entries:
        if colormap_entry.transparent == False:
            labels.append(colormap_entry.label)
            if colormap_entry.value != None:
                has_values = True
                colormap_entries.append(colormap_entry)
                colors.append(colormap_entry.color)
            elif colormap.style == "classification" and colormap_entry.value == None:
                legendcolors.append(colormap_entry.color)
                legendlabels.append(colormap_entry.label)
    
    if len(colors) > 10:
        is_large_colormap = True
    
    for idx in range(0, len(colormap_entries)):
        if colormap.style == "range" or ("(" in colormap_entries[idx].value or "[" in colormap_entries[idx].value): # break apart values for ranges
            bounds.append(float(colormap_entries[idx].value.split(',')[0].replace('[','').replace('(','')))
            ticklabels.append(float(colormap_entries[idx].value.split(',')[0].replace('[','').replace('(','')))
            if idx == len(colormap_entries)-1 and ("(" in colormap_entries[idx].value or "[" in colormap_entries[idx].value): # add ending range value
                ticklabels.append(float(colormap_entries[idx].value.split(',')[1].replace(')','').replace(']','')))
                bounds.append(float(colormap_entries[idx].value.split(',')[1].replace(')','').replace(']','')))
                
        else: # assume discrete values
            bounds.append(float(colormap_entries[idx].value))
            ticklabels.append(colormap_entries[idx].value)
            if is_large_colormap == False:
                center_ticks = True
                if idx == len(colormap_entries)-1:
                    increment = (float(colormap_entries[idx].value) - float(colormap_entries[idx-1].value))
                    ticks.append(float(colormap_entries[idx].value) + increment/2)
                    bounds.append(float(colormap_entries[idx].value)+ increment)
                else:
                    increment = (float(colormap_entries[idx+1].value) - float(colormap_entries[idx].value))
                    ticks.append(float(colormap_entries[idx].value) + increment/2)
                
    # use legend for classifications
    if colormap.style == "classification":
        patches = []
        for color in legendcolors:
            polygon = mpl.patches.Rectangle((0, 0), 10, 10, facecolor=color)
            polygon.set_linewidth(0.5)
            patches.append(polygon)
        if len(legendcolors) < 7 and has_values == False:
            fig.set_figheight(1.5)
        if len(legendcolors) > 14:
            fig.set_figwidth(3)
            col = 2
            fontsize = 8
        else: 
            col = 1
            fontsize = 9

        if has_values == True:
            fig.set_figwidth(3)
            legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, 0.5], loc='center left', ncol=1, fancybox=True, prop={'size':fontsize})
            legend.get_frame().set_alpha(0)
        else:
            legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, 0.5], loc='center', ncol=col, fancybox=True, prop={'size':fontsize})
            legend.get_frame().set_alpha(0.5)
            ax.set_axis_off()
 
    if has_values == True:
        cmap = mpl.colors.ListedColormap(colors)        
        ax.set_yticklabels(ticklabels)
        if is_large_colormap == True:
            norm = mpl.colors.Normalize(bounds[0], bounds[len(bounds)-1])
        else:
            norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap,
                                       norm=norm,
                                       orientation='vertical')
        cb.solids.set_edgecolor("face")
                
        for tick in cb.ax.yaxis.get_ticklabels():
            tick.set_fontsize(10)
    
        if center_ticks == True:
            cb.set_ticks(ticks)
            cb.ax.set_yticklabels(ticklabels)
        
        # set units on first and last labels, if applicable
        if colormap.units != None:
            if len(cb.ax.get_yticklabels()) > 0:
                ticklabels = cb.ax.get_yticklabels()
                ticklabels = [label.get_text() for label in ticklabels]
            ticklabels[0] = str(ticklabels[0]) + " " + colormap.units
            ticklabels[-1] = str(ticklabels[-1]) + " " + colormap.units
            cb.ax.set_yticklabels(ticklabels)
            
            if colormap.style == "classification":
                # resize colorbar if classification
                cb.ax.set_position((0.2, 0.05, 0.075, 0.9))     
        
    fig.savefig(output, transparent=True, format=output_format)
    
    # Add tooltips to SVG    
    if output_format == 'svg' and has_values == True and is_large_colormap == False:
        
        for i, ticklabel in enumerate(ax.get_yticklabels()):
            if i < len(labels):
                text = labels[i]
                ax.annotate(text, 
                xy=ticklabel.get_position(),
                textcoords='offset points', 
                color='black', 
                ha='center', 
                fontsize=10,
                gid='tooltip',
                bbox=dict(boxstyle='round,pad=.3', fc=(1,1,.9,1), ec=(.1,.1,.1), lw=1, zorder=1),
                )

        # Set id for the annotations
        for i, t in enumerate(ax.texts):
            t.set_gid('tooltip_%d'%i)
            
        # Save the figure
        f = StringIO()
        plt.savefig(f, transparent=True, format="svg")     
        
        # Create XML tree from the SVG file
        tree, xmlid = ET.XMLID(f.getvalue())
        tree.set('onload', 'init(evt)')
        
        # Hide the tooltips
        for i, t in enumerate(ax.texts):
            el = xmlid['tooltip_%d'%i]
            el.set('visibility', 'hidden')            
        
        # Add mouseover events to color bar
        el = xmlid['QuadMesh_1']
        elements = list(el)
        elements.pop(0) # remove definitions
        for i, t in enumerate(elements):
            el = elements[i]
            el.set('onmouseover', "ShowTooltip("+str(i)+")")
            el.set('onmouseout', "HideTooltip("+str(i)+")")
        
        # This is the script defining the ShowTooltip and HideTooltip functions.
        script = """
            <script type="text/ecmascript">
            <![CDATA[
            
            function init(evt) {
                if ( window.svgDocument == null ) {
                    svgDocument = evt.target.ownerDocument;
                    }
                }
                
            function ShowTooltip(idx) {
                var tip = svgDocument.getElementById('tooltip_'+idx);
                tip.setAttribute('visibility',"visible")
                }
                
            function HideTooltip(idx) {
                var tip = svgDocument.getElementById('tooltip_'+idx);
                tip.setAttribute('visibility',"hidden")
                }
                
            ]]>
            </script>
            """
        
        # Insert the script at the top of the file and save it.
        tree.insert(0, ET.XML(script))
        ET.ElementTree(tree).write(output)

    print output + " generated successfully"
    

#-------------------------------------------------------------------------------

print toolName + ' ' + versionNumber + '\n'

usageText = toolName + " --colormap [file] --output [file]"

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--colormap',
                  action='store', type='string', dest='colormap',
                  help='Full path or URL of colormap filename.')
parser.add_option('-f', '--format',
                  action='store', type='string', dest='format', default = 'svg',
                  help='Format of output file. Default: SVG')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output file')
parser.add_option('-u', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')

# read command line args
(options, args) = parser.parse_args()

if options.colormap:
    colormap_location = options.colormap
else:
    print "colormap file must be specified...exiting"
    exit()
if options.output:
    output_location = options.output
else:
    print "output file must be specified...exiting"
    exit()
    
# parse colormap
try:
    colormap = parse_colormap(colormap_location)
except IOError,e:
    print str(e)
    exit()

# generate legend
try:
    generate_legend(colormap, output_location, options.format)
except IOError,e:
    print str(e)
    exit()
