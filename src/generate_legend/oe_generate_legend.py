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
# 2015

import sys
import urllib
import xml.dom.minidom
from optparse import OptionParser
import matplotlib as mpl
mpl.use('Agg')
print(mpl.matplotlib_fname())
from matplotlib import pyplot
from matplotlib import rcParams
import matplotlib.pyplot as plt
from StringIO import StringIO
import numpy as np
import math

# for SVG tooltips
try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    ET.register_namespace("","http://www.w3.org/2000/svg")

toolName = "oe_generate_legend.py"
versionNumber = "v0.6.3"

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
        return self.__repr__().encode(sys.stdout.encoding)


class ColorMapEntry:
    """ColorMapEntry values within a ColorMap"""
    
    def __init__(self, red, green, blue, transparent, source_value, value, label, nodata):
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.transparent = transparent
        self.source_value = source_value
        self.value = value
        self.label = label
        self.nodata = nodata
        self.color = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        if self.value != None:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" value="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.value, self.label)
        else:
            xml = '<ColorMapEntry rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" label="%s"/>' % (self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.label)
        return xml
    
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
    
    def __init__(self, entry_id, red, green, blue, transparent, source_value, value, label, nodata, showtick, showvalue):
        self.entry_id = int(entry_id)
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.transparent = transparent
        self.source_value = source_value
        self.value = value
        self.label = None if label==None else label.replace(u'\u2013', '-')
        self.nodata = nodata
        self.showtick = showtick
        self.showvalue = showvalue
        self.color = [float(red)/255.0,float(green)/255.0,float(blue)/255.0]
        
    def __repr__(self):
        if self.value != None:
            xml = '<LegendEntry id="%d" rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" value="%s" label="%s" showTick="%s" showValue="%s"/>' % (self.entry_id, self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.value, self.label, self.showtick, self.showvalue)
        else:
            xml = '<LegendEntry id="%d" rgb="%d,%d,%d" transparent="%s" nodata="%s" sourceValue="%s" label="%s" showTick="%s" showValue="%s"/>' % (self.entry_id, self.red, self.green, self.blue, self.transparent, self.nodata, self.source_value, self.label, self.showtick, self.showvalue)
        return xml
    
    def __str__(self):
        return self.__repr__().encode(sys.stdout.encoding)


def parse_colormaps(colormap_location, verbose):
    """Parse the color map XML file"""

    try:
        if verbose:
            print "Reading color map:", colormap_location
        colormap_file = open(colormap_location,'r')
        try:
            dom = xml.dom.minidom.parse(colormap_file)
        except:
            msg = "ERROR: Unable to parse XML file"
            print >> sys.stderr, msg
            raise Exception(msg)
            sys.exit(1)            
        colormap_file.close()
    except IOError:
        print "Accessing URL", colormap_location
        try:
            dom = xml.dom.minidom.parse(urllib.urlopen(colormap_location))
        except:
            msg = "ERROR: URL " + colormap_location + " is not accessible"
            print >> sys.stderr, msg
            raise Exception(msg)
            sys.exit(1)
    
    tree=ET.fromstring(dom.toxml())
    colormaps = []   
    if tree.tag == 'ColorMap':
        colormaps.append(tree)
        if verbose:
            print '-------------------\n' +  ET.tostring(tree, encoding='utf8', method='xml') + '\n-------------------'
    for colormap in tree.findall('ColorMap'):
        colormaps.append(colormap)
        if verbose:
            print '-------------------\n' + ET.tostring(colormap, encoding='utf8', method='xml') + '\n-------------------'
    
    return colormaps

def parse_colormap(colormap_xml, verbose):
    
    dom = xml.dom.minidom.parseString(ET.tostring(colormap_xml))
           
    colormap_element = dom.getElementsByTagName("ColorMap")[0]
    try:
        title = colormap_element.attributes['title'].value
    except KeyError:
        title = None
    if verbose:
        print "ColorMap title:", title
    try:
        units = colormap_element.attributes['units'].value
    except KeyError:
        units = None
    if verbose:
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
        try:
            nodata = True if colormapentry.attributes['nodata'].value.lower() == 'true' else False
        except KeyError:
            nodata = False
        
        colormap_entries.append(ColorMapEntry(red, green , blue, transparent, source_value, value, label, nodata))
    
    legend = None
    legend_elements = dom.getElementsByTagName("Legend")
    if len(legend_elements) > 0:
        legend = parse_legend(colormap_xml) #should only have one legend per color map
        style = legend.legend_type
        
    colormap = ColorMap(units, colormap_entries, style, title, legend)
    
    if verbose:
        print "ColorMap style:", style
        print colormap
    
    return colormap

def parse_legend(legend_xml):
    
    legend_entries = []
    legend_element = legend_xml.find('Legend')
    legend_entry_elements = legend_element.findall("LegendEntry")
    for legend_entry in legend_entry_elements:    
        red, green, blue = legend_entry.get("rgb").split(",")
        try:
            transparent = legend_entry.get('transparent')
            if transparent != None:
                transparent = True if transparent.lower() == 'true' else False
            else:
                transparent = False
        except KeyError:
            transparent = False
        try:
            value = legend_entry.get('value')
        except KeyError:
            value = None
        try:
            source_value = legend_entry.get('sourceValue')
        except KeyError:
            source_value = value
        try:
            label = legend_entry.get('label')
        except KeyError:
            label = value
        try:
            nodata = legend_entry.get('nodata')
            if nodata != None:
                nodata = True if nodata.lower() == 'true' else False
            else:
                nodata = False
        except KeyError:
            nodata = False
        try:
            showtick = legend_entry.get('showTick')
            if showtick != None:
                showtick = True if showtick.lower() == 'true' else False
            else:
                showtick = False
        except KeyError:
            showtick = False
        try:
            showvalue = legend_entry.get('showValue')
            if showvalue != None:
                showvalue = True if showvalue.lower() == 'true' else False
            else:
                showvalue = False
        except KeyError:
            showvalue = False
        entry_id = legend_entry.get("id")
        if entry_id == None: 
            entry_id = 0
        legend_entry = LegendEntry(entry_id, red, green, blue, transparent, source_value, value, label, nodata, showtick, showvalue)
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
    

def generate_legend(colormaps, output, output_format, orientation):
    
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
    colormap_entries = []
    colormap_count = 0
    labels = []
        
    for colormap in colormaps:
        colormap_count += 1
        is_large_colormap = False
        center_ticks = False
        bounds = []
        ticks = []
        ticklabels=[]
        legendcolors = []
        legendlabels = []
    
        if colormap.legend == None:
            entries = colormap.colormap_entries
            # ensure showTick and showValue exist if no legend
            for idx in range(0, len(entries)):
                entries[idx].showtick = False
                entries[idx].showvalue = False
        else:
            entries = colormap.legend.legend_entries
            colormap.style = colormap.legend.legend_type
            if colormap.legend.legend_type != "classification":
            # clear colors if not classification
                colors = []
                colormap_entries = []
        
        # use only entries with showTick or showValues in newer colormap schema
        show_all = True
        for colormap_entry in entries:
            if colormap_entry.showtick == True or colormap_entry.showvalue == True:
                show_all = False                    
            
        for colormap_entry in entries:
            if colormap_entry.transparent == False:
                labels.append(colormap_entry.label)
                if colormap.style == "classification":
                    legendcolors.append(colormap_entry.color)
                    legendlabels.append(colormap_entry.label)
                else:
                    if colormap_entry.value != None:
                        has_values = True
                        colormap_entries.append(colormap_entry)
                        colors.append(colormap_entry.color)
                        
            if len(colors) > 12:
                # legacy linear interpolation of values if large colormap
                is_large_colormap = True         
        
        if colormap.style != "classification":
            for idx in range(0, len(colormap_entries)):
                if "(" in colormap_entries[idx].value or "[" in colormap_entries[idx].value and ',' not in colormap_entries[idx].value:
                    colormap_entries[idx].value = colormap_entries[idx].value.replace('[','').replace(']','')
                if colormap.style == "range" or ("(" in colormap_entries[idx].value or "[" in colormap_entries[idx].value): # break apart values for ranges
                    bounds.append(float(colormap_entries[idx].value.split(',')[0].replace('[','').replace(']','').replace('(','')))
                    if idx == 0:
                        # always add the first value
                        value = float(colormap_entries[idx].value.split(',')[0].replace('[','').replace(']','').replace('(',''))
                        if math.isinf(value) == True:
                            value = float(colormap_entries[idx].value.split(',')[1].replace(')','').replace('[','').replace(']',''))
                        ticks.append(value)
                        ticklabels.append(value)
                    elif idx != len(colormap_entries)-1 :
                        if show_all==True or colormap_entries[idx].showtick == True or colormap_entries[idx].showvalue == True:
                            ticks.append(float(colormap_entries[idx].value.split(',')[0].replace('[','').replace(']','').replace('(','')))
                        if show_all==True or colormap_entries[idx].showvalue == True:
                            ticklabels.append(float(colormap_entries[idx].value.split(',')[0].replace('[','').replace(']','').replace('(','')))
                    if idx == len(colormap_entries)-1 and ("(" in colormap_entries[idx].value or "[" in colormap_entries[idx].value): # add ending range value
                        bounds.append(float(colormap_entries[idx].value.split(',')[1].replace(')','').replace('[','').replace(']','')))
                        # always add the last value
                        value = float(colormap_entries[idx].value.split(',')[1].replace(')','').replace('[','').replace(']',''))
                        if math.isinf(value) == True:
                            value = float(colormap_entries[idx].value.split(',')[0].replace('[','').replace(']','').replace('(',''))
                        ticks.append(value)
                        ticklabels.append(value)

                else:  # discrete values
                        bounds.append(float(colormap_entries[idx].value))
                        center_ticks = True
                        if idx == len(colormap_entries)-1:
                            increment = (float(colormap_entries[idx].value) - float(colormap_entries[idx-1].value))
                            bounds.append(float(colormap_entries[idx].value)+ increment)
                            ticks.append(float(colormap_entries[idx].value) + increment/2)
                            ticklabels.append(float(colormap_entries[idx].value))
                        else:
                            increment = (float(colormap_entries[idx+1].value.replace('[','').replace(']','')) - float(colormap_entries[idx].value))
                            if show_all==True or colormap_entries[idx].showtick == True or colormap_entries[idx].showvalue == True or idx == 0:
                                ticks.append(float(colormap_entries[idx].value) + increment/2)   
                            if show_all==True or colormap_entries[idx].showvalue == True or idx == 0:
                                ticklabels.append(float(colormap_entries[idx].value))                                  

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
                bottom = 0.90 - ((0.9/lc)*(colormap_count-1)) - (0.20/lc)
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
                if len(legendcolors) <= (15/lc): 
                    col = 1
                    fontsize = 9
                if len(legendcolors) > (15/lc):
                    if lc == 1:
                        fig.set_figwidth(3)
                    col = 2
                    fontsize = 8
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
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, 0.5], loc='center', ncol=col, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0.5)
            
            if has_values == True and (colormap.style != "classification" or colormap.legend == None):
                labels = bounds
                ax = fig.add_axes([0.075, bottom, 0.85, height])
                cmap = mpl.colors.ListedColormap(colors)

                if show_all == True:
                    if is_large_colormap == True:
                        norm = mpl.colors.Normalize(bounds[0], bounds[len(bounds)-1])
                        v = np.linspace(bounds[0], bounds[len(bounds)-1], 9, endpoint=True)
                        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=v, orientation=orientation)
                    else:
                        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation=orientation)
                        if center_ticks == True:
                            cb.set_ticks(ticks)
                            cb.ax.set_xticklabels(ticklabels)
                else:
                    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_xticklabels(ticks) 
                    
                cb.solids.set_edgecolor("face")
            
                for tick in cb.ax.xaxis.get_ticklabels():
                    tick.set_fontsize(8)

                if colormap.legend != None:
                    if len(cb.ax.get_xticklabels()) > 0:
                        xticklabels = cb.ax.get_xticklabels()
                        xticklabels = [label.get_text() for label in xticklabels]
                        # Check for infinity
                        if lowerinf:
                            xticklabels[0] = "<=" + xticklabels[0]
                        if upperinf:
                            xticklabels[-1] = ">=" + xticklabels[-1]
                            
                        # show only those with showValue
                        for idx in range(0, len(xticklabels)):
                            if center_ticks == True:
                                if show_all == False:
                                    if float(xticklabels[idx])-(increment/2) not in ticklabels:
                                        xticklabels[idx] = ""
                                    else:
                                        xticklabels[idx] = (float(xticklabels[idx])-(increment/2))
                                        if float(xticklabels[idx]).is_integer():
                                                xticklabels[idx] = int(float(xticklabels[idx])) 
                                else:
                                    if float(xticklabels[idx]) not in ticklabels:
                                            xticklabels[idx] = ""    
                            else:
                                if show_all == False:
                                    try:
                                        if float(xticklabels[idx]) not in ticklabels:
                                            xticklabels[idx] = ""
                                        else:
                                            if float(xticklabels[idx]).is_integer():
                                                xticklabels[idx] = int(float(xticklabels[idx]))                                               
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
                
                if colormap.units != None:
                    fig.text(0.5, bottom-height-(0.20/lc), colormap.units, fontsize=10, horizontalalignment='center')
                    
            if colormap.title != None:
                if lc ==1:
                    title_loc = 1-t
                else:
                    title_loc = bottom+height+(0.07/lc)
                if colormap.style == "classification":
                    fig.text(0.125, title_loc, colormap.title, fontsize=10, horizontalalignment='center', weight='bold')
                else:
                    fig.text(0.5, title_loc, colormap.title, fontsize=10, horizontalalignment='center', weight='bold')
                    
        
        else: # default vertical orientation
            left = ((1.00/lc) * colormap_count) - (0.73/lc)
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
                if len(legendcolors) <= 14: 
                    col = 1
                    fontsize = 9
                if len(legendcolors) > 14:
                    if lc <= 2:
                        fig.set_figwidth(3.2)
                    col = 2
                    fontsize = 8
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
                    legend = fig.legend(patches, legendlabels, bbox_to_anchor=[0.5, 0.5], loc='center', ncol=col, fancybox=True, prop={'size':fontsize})
                    legend.get_frame().set_alpha(0.5)
         
            if has_values == True and (colormap.style != "classification" or colormap.legend == None):
                labels = bounds
                ax = fig.add_axes([left, 0.1, width, 0.8])
                cmap = mpl.colors.ListedColormap(colors)

                if show_all == True:
                    if is_large_colormap == True:
                        norm = mpl.colors.Normalize(bounds[0], bounds[len(bounds)-1])
                        v = np.linspace(bounds[0], bounds[len(bounds)-1], 9, endpoint=True)
                        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=v, orientation=orientation)
                    else:
                        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation=orientation)
                        if center_ticks == True:
                            cb.set_ticks(ticks)
                            cb.ax.set_yticklabels(ticklabels)
                else:
                    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
                    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, ticks=ticks, orientation=orientation)
                    cb.ax.set_yticklabels(ticks) 
                    
                cb.solids.set_edgecolor("face")
                        
                for tick in cb.ax.yaxis.get_ticklabels():
                    tick.set_fontsize(10)        
                    
                if colormap.legend != None:
                    if len(cb.ax.get_yticklabels()) > 0:
                        yticklabels = cb.ax.get_yticklabels()
                        yticklabels = [label.get_text() for label in yticklabels]
                        # Check for infinity
                        if lowerinf:
                            yticklabels[0] = "<=" + yticklabels[0]
                        if upperinf:
                            yticklabels[-1] = ">=" + yticklabels[-1]
                            
                        # show only those with showValue
                        for idx in range(0, len(yticklabels)):
                            if center_ticks == True:
                                if show_all == False:
                                    if float(yticklabels[idx])-(increment/2) not in ticklabels:
                                        yticklabels[idx] = ""
                                    else:
                                        yticklabels[idx] = str(float(yticklabels[idx])-(increment/2))
                                        if float(yticklabels[idx]).is_integer():
                                                yticklabels[idx] = int(float(yticklabels[idx])) 
                                else:
                                    if float(yticklabels[idx]) not in ticklabels:
                                            yticklabels[idx] = ""                                 
                            else:
                                if show_all == False:
                                    try:
                                        if float(yticklabels[idx]) not in ticklabels:
                                            yticklabels[idx] = ""
                                        else:
                                            if float(yticklabels[idx]).is_integer():
                                                yticklabels[idx] = int(float(yticklabels[idx]))                              
#                                           yticklabels[idx] = "%.2f" % float(yticklabels[idx])
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
                
                if colormap.units != None:
                    fig.text(left + (0.08/lc), 0.01, colormap.units, fontsize=10, horizontalalignment='center')

                                            
            if colormap.title != None:
                title_left = left+(0.08/lc)
                title_top = 0.94
                if colormap.style == "classification":
                    if lc == 1:
                        title_left = 0.5 #center if only one classification legend
                        title_top = 1-t
                fs = 10
                if len(colormap.title) > 10:
                    fs = 9
                if len(colormap.title) > 14:
                    fs = 8
                if len(colormap.title) > 16:
                    title_words = colormap.title.split(" ")
                    half = (len(title_words)/2)
                    if len(title_words) > 2: half += 1
                    title = ""
                    for word in title_words[0:half]:
                        title = title + word + " "
                    title = title + "\n"
                    for word in title_words[half:len(title_words)]:
                        title = title + word + " "                    
                    colormap.title = title
                fig.text(title_left, title_top, colormap.title, fontsize=fs, horizontalalignment='center', weight='bold') 
            
    fig.savefig(output, transparent=True, format=output_format)
        
    # Add tooltips to SVG    
    if output_format == 'svg' and has_values == True:
            
        ax = fig.get_axes()[0] # only supports one axis
        if orientation == "horizontal":
            ax_ticklabels = ax.get_xticklabels()
        else:
            ax_ticklabels = ax.get_yticklabels()

        for i, ticklabel in enumerate(ax_ticklabels):
            if i < len(labels):
                text = ticklabels[i]
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
            t.set_gid('tooltip_%d' % i)
        
        # Save the figure
        f = StringIO()
        plt.savefig(f, transparent=True, format="svg")     
        
        # Create XML tree from the SVG file
        tree, xmlid = ET.XMLID(f.getvalue())
        tree.set('onload', 'init(evt)')
        
        # Hide the tooltips
        for i, t in enumerate(ax.texts):
            el = xmlid['tooltip_%d' % i]
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
        print "SVG tooltips added"
    
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
                  help='Format of output file. Supported formats: eps, pdf, pgf, png, ps, raw, rgba, svg (default), svgz.')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output file')
parser.add_option('-r', '--orientation',
                  action='store', type='string', dest='orientation', default = 'vertical',
                  help='Orientation of the legend: horizontal or vertical (default)')
parser.add_option('-u', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Print out detailed log messages")

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
    
# check orientation
if options.orientation:
    if options.orientation not in ['horizontal','vertical']:
        print str(options.orientation) + " is not a valid legend orientation. Please choose horizontal or vertical."
        exit()

colormaps = []
# parse colormap file
try:
    colormap_elements = parse_colormaps(colormap_location, options.verbose)
except IOError,e:
    print str(e)
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
    except IOError,e:
        print str(e)
        exit()

# generate legend
try:
    generate_legend(colormaps, output_location, options.format, options.orientation)
except IOError,e:
    print str(e)
    exit()
    
exit()
