#!/usr/bin/env python3

# Copyright (c) 2002-2016, California Institute of Technology.
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

#
# oe_generate_legend.py
# The OnEarth Legend Generator.
#
#
# Global Imagery Browse Services

import sys
import urllib.request, urllib.parse, urllib.error
import xml.dom.minidom
from optparse import OptionParser
import matplotlib as mpl
mpl.use('Agg')
print((mpl.matplotlib_fname()))
from matplotlib import pyplot
from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from io import BytesIO
#import numpy as np
import math
import re
import os

# for SVG tooltips
try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    ET.register_namespace("","http://www.w3.org/2000/svg")

toolName = "oe_generate_legend.py"
versionNumber = os.environ.get('ONEARTH_VERSION')

class ColorMaps:
    """Collection of ColorMaps"""
    
    def __init__(self, colormaps):
        self.colormaps = colormaps
        
    def __repr__(self):
        xml = '<ColorMaps>'
        for colormap in self.colormaps:
            xml = xml + '\n    ' + colormap.__repr__()
        xml = xml + '\n</ColorMaps>'
        return xml

    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)
        

class ColorMap:
    """ColorMap metadata"""
    
    def __init__(self, units, colormap_entries, style, title, legend):
        self.units = units
        self.colormap_entries = colormap_entries
        self.style = str(style).lower()
        self.title = title
        self.legend = legend
        
    def __repr__(self):
        if self.units != None:
            xml = '<ColorMap title="%s" units="%s">' % (self.title, self.units)
        else:
            xml = '<ColorMap>'
        for colormap_entry in self.colormap_entries:
            xml = xml + '\n    ' + colormap_entry.__repr__()
        xml = xml + '\n</ColorMap>'
        if self.legend:
            xml = xml + '\n' + self.legend.__repr__()
        return xml

    def __str__(self):
        return self.__repr__()


class ColorMapEntry:
    """ColorMapEntry values within a ColorMap"""
    
    def __init__(self, red, green, blue, transparent, source_value, value, label, nodata, ref):
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.transparent = transparent
        self.source_value = source_value
        self.value = value
        self.label = label                   # Not present in v1.3
        self.nodata = nodata
        self.ref = ref
        self.color = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        return '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" nodata="%s"' % (self.red, self.green, self.blue, self.transparent, self.nodata) + \
               ((' sourceValue="%s"' % (self.source_value)) if self.source_value else '') + \
               ((' value="%s"' % (self.value)) if self.value else '') + \
               ((' label="%s"' % (self.label)) if self.label else '') + \
               ' ref="%s"/>' % (self.ref)
    
    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)


class Legend:
    """Legend metadata"""
    
    def __init__(self, max_label, min_label, legend_type, legend_entries):
        self.max_label = max_label
        self.min_label = min_label
        self.legend_type = legend_type
        self.legend_entries = legend_entries
        
    def __repr__(self):
        if self.max_label != None and self.min_label != None:
            xml = '<Legend maxLabel="%s" minLabel="%s" type="%s">' % (self.max_label, self.min_label, self.legend_type)
        else:
            xml = '<Legend>'
        for legend_entry in self.legend_entries:
            xml = xml + '\n    ' + legend_entry.__repr__()
        xml = xml + '\n</Legend>'
        return xml

    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)    
    
    
class LegendEntry:
    """LegendEntry values within a Legend"""
    
    def __init__(self, entry_id, red, green, blue, transparent, tooltip, label, showtick, showlabel):
        self.entry_id    = int(entry_id)
        self.red         = int(red)
        self.green       = int(green)
        self.blue        = int(blue)
        self.transparent = transparent
        self.tooltip     = None if tooltip==None else tooltip.replace('\u2013', '-')
        self.label       = None if label==None else label.replace('\u2013', '-')
        self.showtick    = showtick
        self.showlabel   = showlabel
        self.color       = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        return '<LegendEntry rgb="%d,%d,%d" ' % (self.red, self.green, self.blue) + \
               ' tooltip="%s"' % (self.tooltip) + \
               ((' label="%s"' % (self.label)) if self.label else '') + \
               ' showTick="%s" showLabel="%s" id="%s"/>' % (self.showtick, self.showlabel, self.entry_id)
    
    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)



def parse_colormaps(colormap_location, verbose):
    """Parse the color map XML file"""

    try:
        if verbose:
            print("Reading color map:", colormap_location)
        colormap_file = open(colormap_location,'r')
        try:
            dom = xml.dom.minidom.parse(colormap_file)
        except:
            msg = "ERROR: Unable to parse XML file"
            print(msg, file=sys.stderr)
            raise Exception(msg)
            sys.exit(1)            
        colormap_file.close()
    except IOError:
        print("Accessing URL", colormap_location)
        try:
            dom = xml.dom.minidom.parse(urllib.request.urlopen(colormap_location))
        except:
            msg = "ERROR: URL " + colormap_location + " is not accessible"
            print(msg, file=sys.stderr)
            raise Exception(msg)
            sys.exit(1)
    
    xmlParser = ET.XMLParser(encoding='utf-8')
    tree=ET.fromstring(dom.toxml().encode('utf-8'), parser=xmlParser)
    colormaps = []   
    if tree.tag == 'ColorMap':
        colormaps.append(tree)
        if verbose:
            print('-------------------\n' +  ET.tostring(tree, encoding='utf8', method='xml').decode("utf-8") + '\n-------------------')
    for colormap in tree.findall('ColorMap'):
        colormaps.append(colormap)
        if verbose:
            print('-------------------\n' + ET.tostring(colormap, encoding='utf8', method='xml').decode("utf-8") + '\n-------------------')
    
    return colormaps

def parse_colormap(colormap_xml, verbose):
    
    dom = xml.dom.minidom.parseString(ET.tostring(colormap_xml))
           
    colormap_element = dom.getElementsByTagName("ColorMap")[0]
    try:
        title = colormap_element.attributes['title'].value
    except KeyError:
        title = None
    if verbose:
        print("ColorMap title:", title)
    try:
        units = colormap_element.attributes['units'].value
    except KeyError:
        units = None
    if verbose:
        print("ColorMap units:", units)
    
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
            label = None
        try:
            nodata = True if colormapentry.attributes['nodata'].value.lower() == 'true' else False
        except KeyError:
            nodata = False
        try:
            ref = colormapentry.attributes['ref'].value
        except KeyError:
            ref = 0
        
        colormap_entries.append(ColorMapEntry(red, green , blue, transparent, source_value, value, label, nodata, ref))
    
    legend = None
    legend_elements = dom.getElementsByTagName("Legend")
    if len(legend_elements) > 0:
        legend = parse_legend(colormap_xml, colormap_entries) #should only have one legend per color map
        style = legend.legend_type
        
    colormap = ColorMap(units, colormap_entries, style, title, legend)
    
    if verbose:
        print("ColorMap style:", style)
        print(colormap)
    
    return colormap

def parse_legend(legend_xml, colormap_entries):
    
    legend_entries = []
    legend_element = legend_xml.find('Legend')

    legend_entry_elements = legend_element.findall("LegendEntry")
    for legend_entry in legend_entry_elements:   
        entry_id = legend_entry.get("id")
        if entry_id == None: 
            print("ERROR: A LegendEntry is missing the required 'id' attribute. Colormap is invalid.")
            sys.exit(1)
        red, green, blue = legend_entry.get("rgb").split(",")

        try:
            tooltip = legend_entry.get('tooltip')
        except KeyError:
            tooltip = None

        try:
            label = legend_entry.get('label')
        except KeyError:
            label = None

        try:
            showtick = legend_entry.get('showTick')
            if showtick != None:
                showtick = True if showtick.lower() == 'true' else False
            else:
                showtick = False
        except KeyError:
            showtick = False
            
        try:
            showlabel = legend_entry.get('showLabel')
            if showlabel != None:
                showlabel = True if showlabel.lower() == 'true' else False
            else:
                showlabel = False
        except KeyError:
            showlabel = False

        # link transparency to color map
        for entry in colormap_entries:
            if entry_id == entry.ref:
                transparent = entry.transparent
                break
        
        if transparent is None:
            print("ERROR: No ColorMapEntry has 'ref={0}' to match the LegendEntry with 'id={0}'. Colormap is invalid.".format(entry_id))
            sys.exit(1)
        
        legend_entry = LegendEntry(entry_id, red, green, blue, transparent, tooltip, label, showtick, showlabel)
        legend_entries.append(legend_entry)
    
    try:
        max_label = legend_element.get("maxLabel")
    except KeyError:
        max_label = None
    try:
        min_label = legend_element.get("minLabel")
    except KeyError:
        min_label = None
    
    legend = Legend(max_label, min_label,legend_element.get("type"), legend_entries)
    
    return legend

# Handle splitting a line of text into multiple lines based on # of characters.
# Returns the split text and the number of characters in the longest line of the split text.
def split_text(text, num_splits):
    split_len = int(len(text) / num_splits)
    text_words = text.split(" ")
    lines = [""]
    line_len = 0
    for word in text_words:
        # Add words to the line until we've reached as close to len(text)/num_splits as possible
        # or if we're on the last line.
        if len(lines) > num_splits - 1 or abs(line_len + len(word) - split_len) < abs(line_len - split_len):
            lines[-1] += " " + word if len(lines[-1]) > 0 else word
            line_len += len(lines[-1])
        else:
            lines.append(word)
            line_len = len(word)
    text = '\n'.join(lines)
    return text, len(max(lines, key=len))

# Handle resizing classification legends (should be same regardless of vertical or horizontal)
def resize_classification_title(title):
    fs = 10
    if len(title) > 16:
        fs = 9
    if len(title) > 18:
        title, max_line_len = split_text(title, 2)
        if max_line_len > 18:
            fs = 7
        else:
            fs = 8
    return title, fs

def generate_legend(colormaps, output, output_format, orientation, label_color, colorbar_only, stroke_color):
    
    # set ticklines out
    rcParams['xtick.direction'] = 'out'
    rcParams['ytick.direction'] = 'out'
    
    lc = len(colormaps)
    t = 0
    has_values = False
    
    for colormap in colormaps:
        if colormap.title != None:
            t = 0.15
        if colormap.legend != None:
            if colormap.legend.legend_type != "classification":
                has_values = True
             
    if orientation == 'horizontal':        
        t = 0.15
        fig = pyplot.figure(figsize=(4.2,t+0.8+(1*(lc-1))))
    else: # default vertical orientation
        fig = pyplot.figure(figsize=(1.5+(2*(lc-1)),3.2))
   
    colors = []
    legend_entries = []
    legend_count = 0
    labels = []
    label_index = []
        
    for colormap in colormaps:
        legend_count += 1
        bounds = []
        ticks = []
        ticklabels=[]
        legendcolors = []
        legendlabels = []
    
        if colormap.legend == None:
            entries = colormap.colormap_entries
            # ensure showTick and showLabel exist if no legend
            for idx in range(0, len(entries)):
                entries[idx].showtick = False
                entries[idx].showlabel = False
        else:
            entries = colormap.legend.legend_entries
            colormap.style = colormap.legend.legend_type
            if colormap.legend.legend_type != "classification":
            # clear colors if not classification
                colors = []
                legend_entries = []
        
        for legend_entry in entries:
            if legend_entry.transparent == False:
                if colormap.style == "classification":
                    legendcolors.append(legend_entry.color)
                    
                    if legend_entry.tooltip:
                        legendlabels.append(legend_entry.tooltip)
                        labels.append(legend_entry.tooltip)
                    else:
                        legendlabels.append(legend_entry.label)
                        labels.append(legend_entry.label)
                       
                else:
                    has_values = True
                    legend_entries.append(legend_entry)
                    colors.append(legend_entry.color)      
        
        if colormap.style != "classification":
            for idx in range(0, len(legend_entries)):
                if legend_entries[idx].showtick == True or legend_entries[idx].showlabel == True or idx == 0 or idx == len(legend_entries)-1:
                    if colormap.style == "discrete":
                        ticks.append(idx + 0.5)
                    else:
                        if idx == len(legend_entries)-1:
                            ticks.append(idx+1) # add end label
                        else:
                            ticks.append(idx)
                    
                    if legend_entries[idx].showlabel == True:
                        ticklabels.append(legend_entries[idx].label)
                        labels.append(legend_entries[idx].label)
                    elif idx == 0 and colormap.legend.min_label != None:
                        ticklabels.append(colormap.legend.min_label)
                        labels.append(colormap.legend.min_label)
                    elif idx == len(legend_entries)-1 and colormap.legend.max_label != None:
                        ticklabels.append(colormap.legend.max_label)
                        labels.append(colormap.legend.max_label)
                    else:
                        ticklabels.append("")
                        labels.append("")
                    label_index.append(idx)

        # Handle +/- INF
        lowerinf = False
        upperinf = False
        if len(bounds) > 0:
            lowerinf = math.isinf(bounds[0])
            upperinf = math.isinf(bounds[-1])
            bounds =  [x for x in bounds if math.isinf(x) == False]
            ticks = [x for x in ticks if math.isinf(x) == False]
            
        # Check for long labels
        longlabels = False
        for legendlabel in legendlabels:
            if len(legendlabel) > 14:
                longlabels = True

        if orientation == 'horizontal':        
            if lc == 1:
                bottom = 0.6 - t
            else:
                bottom = 0.90 - ((0.9/lc)*(legend_count-1)) - (0.20/lc)
            height = 0.20/lc  
        
            # use legend for classifications
            if colormap.style == "classification":
                if lc == 1:
                    fig.set_figheight(3)
                    if longlabels:
                        fig.set_figwidth(3)
                    else:
                        fig.set_figwidth(1.5)
                else:
                    bottom = bottom
                patches = []
                for color in legendcolors:
                    polygon = mpl.patches.Rectangle((0, 0), 10, 10, facecolor=color)
                    polygon.set_linewidth(0.5)
                    patches.append(polygon)
                if len(legendcolors) < 7 and has_values == False:
                    if lc == 1:
                        fig.set_figheight(1.5)
                bottom_box_pos = 0.5
                if len(legendcolors) <= (15/lc): 
                    col = 1
                    fontsize = 9
                if len(legendcolors) > (15/lc):
                    if lc == 1:
                        fig.set_figwidth(3)
                    col = 2
                    fontsize = 8
                    for i, label in enumerate(legendlabels):
                        if len(label) > 18:
                            legendlabels[i] = split_text(label, 2)[0]
                            fontsize = 7
                            bottom_box_pos = 0.45
                if len(legendcolors) > (30/lc):
                    if lc == 1:
                        fig.set_figwidth(4.2)
                    col = 3
                    fontsize = 7
                if has_values == True:
                    if lc == 1:
                        fig.set_figwidth(4.2)
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.025, bottom+(0.3/lc)], loc='upper left', ncol=col, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0)
                else:
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, bottom_box_pos], loc='center', ncol=col, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0.5)
                for text in legend.get_texts():
                    text.set_color(label_color)
                    if stroke_color:
                        text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])
            
            if has_values == True and (colormap.style != "classification" or colormap.legend == None):
                if colorbar_only:
                    fig.set_figheight(height)
                    fig.set_figwidth(2.56)
                    ax = fig.add_axes([0, 0.03, 0.995, 0.97])
                else:
                    ax = fig.add_axes([0.075, bottom, 0.85, height])
                cmap = mpl.colors.ListedColormap(colors)

                if len(bounds) > 0:
                    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_xticklabels(ticks) 
                else:
                    norm = mpl.colors.BoundaryNorm(list(range(len(colors)+1)), cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_xticklabels(ticklabels) 
                    
                cb.solids.set_edgecolor("face")
            
                for tick in cb.ax.xaxis.get_ticklabels():
                    tick.set_fontsize(8)
                    tick.set_color(label_color)
                    if colorbar_only:
                        tick.set_alpha(0)
                if colorbar_only: # hide ticks if we want to show colorbar only
                    for tickline in cb.ax.xaxis.get_ticklines():
                        tickline.set_alpha(0)
                elif stroke_color:
                    for tickline in cb.ax.xaxis.get_ticklines():
                        tickline.set_path_effects([path_effects.Stroke(linewidth=2, foreground=stroke_color), path_effects.Normal()])
                cb.ax.tick_params(axis='x', colors=label_color)
                if colormap.legend != None and len(bounds)>0:
                    if len(cb.ax.get_xticklabels()) > 0:
                        xticklabels = cb.ax.get_xticklabels()
                        xticklabels = [label.get_text() for label in xticklabels]
                        # Check for infinity
                        if lowerinf:
                            xticklabels[0] = "<=" + xticklabels[0]
                        if upperinf:
                            xticklabels[-1] = ">=" + xticklabels[-1]
                            
                        # show only those with showLabel
                        for idx in range(0, len(xticklabels)):
                            try:
                                if float(xticklabels[idx]) not in ticklabels:
                                    xticklabels[idx] = ""
                            except ValueError:
                                xticklabels[idx] = ""
                                        
                        # Use min/max labels
                        if colormap.legend.min_label != None:
                            xticklabels[0] = colormap.legend.min_label
                        if colormap.legend.max_label != None:
                            xticklabels[-1] = colormap.legend.max_label
                         
                        # use int labels if all values are integers
#                         xticklabels = [int(float(label)) for label in xticklabels if float(label).is_integer()]
                        cb.ax.set_xticklabels(xticklabels)
                
                if colormap.units != None and colorbar_only == False:
                    fig_text = fig.text(0.5, bottom-height-(0.20/lc), colormap.units, fontsize=10, horizontalalignment='center', color=label_color)
                    if stroke_color:
                        fig_text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])
                    
            if colormap.title != None and colorbar_only == False:
                if lc ==1:
                    title_loc = 1-t
                else:
                    title_loc = bottom+height+(0.07/lc)
                fs = 10
                if colormap.style == "classification":
                    colormap.title, fs = resize_classification_title(colormap.title)
                fig_text = fig.text(0.5, title_loc, colormap.title, fontsize=fs, horizontalalignment='center', weight='bold', color=label_color)
                if stroke_color:
                    fig_text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])

        else: # default vertical orientation
            left = ((1.00/lc) * legend_count) - (0.73/lc)
            width = 0.15/lc
                        
            # use legend for classifications
            if colormap.style == "classification":
                if longlabels and fig.get_figwidth() < 3:
                    fig.set_figwidth(3.2)
                patches = []
                for color in legendcolors:
                    polygon = mpl.patches.Rectangle((0, 0), 10, 10, facecolor=color)
                    polygon.set_linewidth(0.5)
                    patches.append(polygon)
                if len(legendcolors) < 7 and has_values == False:
                    if lc <= 2:
                        fig.set_figheight(1.5)
                bottom_box_pos = 0.5
                if len(legendcolors) <= 14: 
                    col = 1
                    fontsize = 9
                if len(legendcolors) > 14:
                    if lc <= 2:
                        fig.set_figwidth(3.2)
                    col = 2
                    fontsize = 8
                    for i, label in enumerate(legendlabels):
                        if len(label) > 18:
                            legendlabels[i] = split_text(label, 2)[0]
                            fontsize = 7
                            bottom_box_pos = 0.45
                if len(legendcolors) > 28:
                    if lc <= 2:
                        fig.set_figwidth(4.2)
                    col = 3
                    fontsize = 7
                if has_values == True:
                    if lc <= 2:
                        fig.set_figwidth(3.2)
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[left-(0.15/lc), 0.9], loc='upper left', ncol=1, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0)
                else:
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, bottom_box_pos], loc='center', ncol=col, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0.5)
                for text in legend.get_texts():
                    text.set_color(label_color)
                    if stroke_color:
                        text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])

            if has_values == True and (colormap.style != "classification" or colormap.legend == None):
                if colorbar_only:
                    fig.set_figheight(2.56)
                    fig.set_figwidth(0.2)
                    ax = fig.add_axes([0.02, 0.005, 0.94, 0.995])
                else:
                    ax = fig.add_axes([left, 0.1, width, 0.8])
                cmap = mpl.colors.ListedColormap(colors)

                if len(bounds) > 0:
                    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_yticklabels(ticks) 
                else:
                    norm = mpl.colors.BoundaryNorm(list(range(len(colors)+1)), cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_yticklabels(ticklabels)                         
                    
                cb.solids.set_edgecolor("face")
                        
                for tick in cb.ax.yaxis.get_ticklabels():
                    tick.set_fontsize(10)
                    tick.set_color(label_color)
                    if stroke_color:
                        tick.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])
                    if colorbar_only:
                        tick.set_alpha(0)
                if colorbar_only: # hide ticks if we want to show colorbar only
                    for tickline in cb.ax.yaxis.get_ticklines():
                        tickline.set_alpha(0)
                elif stroke_color:
                    for tickline in cb.ax.yaxis.get_ticklines():
                        tickline.set_path_effects([path_effects.Stroke(linewidth=2, foreground=stroke_color), path_effects.Normal()])
                cb.ax.tick_params(axis='y', colors=label_color)
                if colormap.legend != None and len(bounds)>0:
                    if len(cb.ax.get_yticklabels()) > 0:
                        yticklabels = cb.ax.get_yticklabels()
                        yticklabels = [label.get_text() for label in yticklabels]
                        # Check for infinity
                        if lowerinf:
                            yticklabels[0] = "<=" + yticklabels[0]
                        if upperinf:
                            yticklabels[-1] = ">=" + yticklabels[-1]
                            
                        # show only those with showLabel
                        for idx in range(0, len(yticklabels)):
                            try:
                                if float(yticklabels[idx]) not in ticklabels:
                                    yticklabels[idx] = ""
                                else:
                                    if float(yticklabels[idx]).is_integer():
                                        yticklabels[idx] = int(float(yticklabels[idx]))
                            except ValueError:
                                yticklabels[idx] = ""
                        
                        # Use min/max labels
                        if colormap.legend.min_label != None:
                            yticklabels[0] = colormap.legend.min_label
                        if colormap.legend.max_label != None:
                            yticklabels[-1] = colormap.legend.max_label
                                                                    
                        # use int labels if all values are integers
#                         yticklabels = [int(float(label)) for label in yticklabels if float(label).is_integer()]
                        cb.ax.set_yticklabels(yticklabels)
                
                if colormap.units != None and colorbar_only == False:
                    fs = 10
                    if len(colormap.units) > 12:
                        fs = 9
                    if len(colormap.units) > 14:
                        fs = 8
                    if len(colormap.units) > 17:
                        fs = 7
                    fig_text = fig.text(left + (0.08/lc), 0.01, colormap.units, fontsize=fs, horizontalalignment='center', color=label_color)
                    if stroke_color:
                        fig_text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])

                                            
            if colormap.title != None and colorbar_only == False:
                title_left = left+(0.08/lc)
                title_top = 0.935
                fs = 10
                if colormap.style == "classification":
                    if lc == 1:
                        title_left = 0.5 #center if only one classification legend
                        title_top = 1-t
                    colormap.title, fs = resize_classification_title(colormap.title)
                else:
                    if len(colormap.title) > 10:
                        fs = 9
                    if len(colormap.title) > 14:
                        fs = 8
                    if len(colormap.title) > 16:
                        colormap.title, max_line_len = split_text(colormap.title, 2)
                        # For multiple legends, clipping has only been observed on the leftmost legend
                        # so only shrink that one further
                        if legend_count == 1 and max_line_len > 18:
                            fs = 6
                fig_text = fig.text(title_left, title_top, colormap.title, fontsize=fs, horizontalalignment='center', weight='bold', color=label_color) 
                if stroke_color:
                    fig_text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=stroke_color), path_effects.Normal()])
    
    fig.savefig(output, transparent=True, format=output_format)
        
    # Add tooltips to SVG    
    if output_format == 'svg' and has_values == True:
        tooltip_counts = []
        axes = fig.get_axes()
        for i in range(len(axes)):
            ax = axes[i]           
            entries = colormaps[i].legend.legend_entries
            tooltip_counts.append(0)
            for j, entry in enumerate(entries):
                if entry.tooltip:
                    tooltip_counts[i] += 1
                    text = entry.tooltip
                    if colormaps[i].units:
                        text = text + " " + colormaps[i].units
                else:
                    text = entry.label
                if orientation == "horizontal":
                    position = (float(j)/float(len(entries)),1)
                else:
                    position = (1,float(j)/float(len(entries)))
                ax.annotate(text, 
                xy=position,
            xytext=position,
                textcoords='offset points', 
                color='black', 
                ha='center', 
                fontsize=10,
                gid='tooltip',
                bbox=dict(boxstyle='round,pad=.3', fc=(1,1,.9,1), ec=(.1,.1,.1), lw=1, zorder=1),
                )
        
            # Set id for the annotations
            for j, t in enumerate(ax.texts):
                t.set_gid('tooltip_%d' % (j + sum(tooltip_counts[:i])))
            
        # Save the figure
        f = BytesIO()
        plt.savefig(f, transparent=True, format="svg")     
            
        # Create XML tree from the SVG file
        tree, xmlid = ET.XMLID(f.getvalue())
        tree.set('onload', 'init(evt)')
            
        # Hide the tooltips
        for i in range(sum(tooltip_counts)):
            try:
                el = xmlid['tooltip_%d' % i]
                el.set('visibility', 'hidden')
            except KeyError:
                None
        
        # Add mouseover events to color bar
        # Handle colorbar with discrete colors
        if 'QuadMesh_1' in xmlid.keys():
            el = xmlid['QuadMesh_1']
            elements = list(el)

        else: # Handle continuous colorbars, which are represented as image elements
            elements = []
            svg_ns = {
                'svg': 'http://www.w3.org/2000/svg', 
                'xlink': 'http://www.w3.org/1999/xlink'
            }
            colorbar_parents = tree.findall(".//svg:image/..", svg_ns)
            if len(colorbar_parents) == 0:
                print("Warning: Unable to add tooltips")
            else:
                for parent in colorbar_parents:
                    colorbar_imgs = parent.findall("svg:image", svg_ns)
                    for i, colorbar_el in enumerate(colorbar_imgs):
                        colorbar_size = float(colorbar_el.get("width")) if orientation == "horizontal" else float(colorbar_el.get("height"))
                        tooltip_size = colorbar_size / tooltip_counts[i]
                        # overlay small invisible rectangles on top of the colorbar
                        # to serve as the mouseover targets
                        for j in range(tooltip_counts[i]):
                            el = ET.SubElement(parent, "rect")
                            el.set("fill", "none")
                            el.set("pointer-events", "all")
                            el.set("transform", colorbar_el.get("transform"))
                            if orientation == "horizontal":
                                el_pos = float(colorbar_el.get("x")) + j * tooltip_size
                                el.set("x", str(el_pos))
                                el.set("y", colorbar_el.get("y"))
                                el.set("width", str(tooltip_size))
                                el.set("height", colorbar_el.get("height"))
                            else:
                                el_pos = float(colorbar_el.get("y")) + j * tooltip_size
                                el.set("y", str(el_pos))
                                el.set("x", colorbar_el.get("x"))
                                el.set("width", colorbar_el.get("width"))
                                el.set("height", str(tooltip_size))
                            elements.append(el)

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
        print("SVG tooltips added")
    
    print(output + " generated successfully")
    

#-------------------------------------------------------------------------------

print(toolName + ' ' + versionNumber + '\n')

usageText = toolName + " --colormap [file] --output [file]"

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option("-b", "--colorbar_only",
                  action="store_true", dest="colorbar_only", 
                  default=False, help="Generate only the colorbar (i.e., no labels)")
parser.add_option('-c', '--colormap',
                  action='store', type='string', dest='colormap',
                  help='Full path or URL of colormap filename.')
parser.add_option('-f', '--format',
                  action='store', type='string', dest='format', default = 'svg',
                  help='Format of output file. Supported formats: eps, pdf, pgf, png, ps, raw, rgba, svg (default), svgz.')
parser.add_option('-l', '--label_color',
                  action='store', type='string', dest='label_color', default = 'black',
                  help='Color of labels. Supported colors: black (default), blue, green, red, cyan, magenta, yellow, white or hexstring')
parser.add_option('-s', '--stroke_color',
                  action='store', type='string', dest='stroke_color', default=False,
                  help='Color of labels stroke. Supported colors: black (default), blue, green, red, cyan, magenta, yellow, white or hexstring')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output file')
parser.add_option('-r', '--orientation',
                  action='store', type='string', dest='orientation', default = 'vertical',
                  help='Orientation of the legend: horizontal or vertical (default)')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Print out detailed log messages")

# read command line args
(options, args) = parser.parse_args()

if options.colormap:
    colormap_location = options.colormap
else:
    print("colormap file must be specified...exiting")
    exit()
if options.output:
    output_location = options.output
else:
    print("output file must be specified...exiting")
    exit()
    
# check orientation
if options.orientation:
    if options.orientation not in ['horizontal','vertical']:
        print(str(options.orientation) + " is not a valid legend orientation. Please choose horizontal or vertical.")
        exit()
        
# check label color
if options.label_color:
    label_color = str(options.label_color).lower()
    if label_color not in ["blue","green","red","cyan","magenta","yellow","black","white"]:
        print("Using custom color " + label_color)
        colormatch = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', label_color)
        if colormatch == False:
            print("Invalid label color")
            exit()
else:
    label_color = "black"

# check stroke color
if options.stroke_color:
    stroke_color = str(options.stroke_color).lower()
    if stroke_color not in ["blue","green","red","cyan","magenta","yellow","black","white"]:
        print("Using custom color " + stroke_color)
        colormatch = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', stroke_color)
        if colormatch == False:
            print("Invalid stroke color")
            exit()
else:
    stroke_color = False

colormaps = []
# parse colormap file
try:
    colormap_elements = parse_colormaps(colormap_location, options.verbose)
except IOError as e:
    print(str(e))
    exit()
    
# parse colormaps
for colormap_xml in colormap_elements:
    
    try:
        colormap = parse_colormap(colormap_xml, options.verbose)
        has_entries = False
        for entry in colormap.colormap_entries:
            if entry.transparent == False:
                has_entries = True
        if has_entries:
            colormaps.append(colormap)
    except IOError as e:
        print(str(e))
        exit()

# generate legend
try:
    generate_legend(colormaps, output_location, options.format, options.orientation, label_color, options.colorbar_only, stroke_color)
except IOError as e:
    print(str(e))
    exit()
    
exit()
