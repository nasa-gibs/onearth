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
# onearth_logs.py
# The OnEarth Custom Log Generator.
#
#
# Example XML configuration file:
#
'''
<?xml version="1.0" encoding="UTF-8"?>
<LogConfiguration>
    
    <!-- Apache Custom Log Format (http://httpd.apache.org/docs/2.2/mod/mod_log_config.html) -->
    <!-- Ex. "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" -->
    <ApacheLogFormat>"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""</ApacheLogFormat>
    
    <!-- Available Apache fields: requestor, timestamp, uri, bytes, statuscode, useragent -->
    <!-- Available OnEarth fields: service, request, version, layer, time, tilematrixset, tilematrix, tilerow, tilecol, format, layers, srs, styles, width, height, bbox, transparent, bgcolor, exceptions, elevation -->
    <!-- Ex. %(requestor)s|&amp;|%(timestamp)s|&amp;|%(uri)s|&amp;|%(bytes)s|&amp;|%(statuscode)s|&amp;|%(useragent)s|&amp;|%(service)s|&amp;|%(layer)s|&amp;|%(time)s|&amp;|%(tilematrixset)s|&amp;|%(tilematrix)s|&amp;|%(tilerow)s|&amp;|%(tilecol)s|&amp;|%(format)s -->
    <OutputLog>%(requestor)s|&amp;|%(timestamp)s|&amp;|%(uri)s|&amp;|%(bytes)s|&amp;|%(statuscode)s|&amp;|%(useragent)s|&amp;|%(service)s|&amp;|%(layer)s|&amp;|%(time)s|&amp;|%(tilematrixset)s|&amp;|%(tilematrix)s|&amp;|%(tilerow)s|&amp;|%(tilecol)s|&amp;|%(format)s</OutputLog>
    
</LogConfiguration>
'''
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014

from optparse import OptionParser
import sys
import time
import subprocess
import select
import re
import urlparse
import urllib
import xml.dom.minidom

toolName = "onearth_logs.py"
versionNumber = "1.3.0"

pixelsize = 0.00028 # meters


class TileMatrixSetMap:
    """Mappings for Tiled-WMS bounding box levels to WMTS TileMatrixSets"""
    
    def __init__(self, projection_id, bboxes, minx, maxy, tilematrixsetmap):
        """
        Arguments:
            projection_id -- EPSG code identifier
            bboxes -- dictionary of bounding box patterns by layer
            minx -- the top-left corner x value
            maxy -- the top-left corner y value
            tilematrixsetmap -- map of levels to their TileMatrixSet names
        """
        self.projection_id = projection_id
        self.bboxes = bboxes
        self.minx = float(minx)
        self.maxy = float(maxy)
        self.tilematrixsetmap = tilematrixsetmap

def read_getTileService(gettileservice_file):
    """
    Reads the TileMatrixSet map configuration file and returns a dictionary with mappings between WMTS TileMatrixSets and Tiled-WMS TilePatterns.
    Arguments:
        tilematrixsetmap_file -- the location of the tilematrixsetmap configuration file
    """
    
    try:
        # Open file.
        gettileservice=open(gettileservice_file, 'r')
        dom = xml.dom.minidom.parse(gettileservice)
        gettileservice.close()
    except IOError: # try http URL
        dom = xml.dom.minidom.parse(urllib.urlopen(gettileservice_file))
    print ('Using getTileService: ' + gettileservice_file)
        
    bboxes = {}
    tilePatternElements = dom.getElementsByTagName('TilePattern')
    for tilePatternElement in tilePatternElements:
        tilepattern = tilePatternElement.firstChild.wholeText
        layer = tilepattern.split("layers=")[1].split("&")[0].strip()
        bbox_string = tilepattern.split("bbox=")[1].split(" ")[0].strip()
        bbox = [float(x) for x in bbox_string.split(',')]
        try:
            bboxes[layer].append(bbox)
        except KeyError:
            bboxes[layer] = []
            bboxes[layer].append(bbox)
        
    return bboxes

def read_tilematrixsetmap(tilematrixsetmap_file):
    """
    Reads the TileMatrixSet map configuration file and returns a dictionary with mappings between WMTS TileMatrixSets and Tiled-WMS TilePatterns.
    Arguments:
        tilematrixsetmap_file -- the location of the tilematrixsetmap configuration file
    """
    
    try:
        # Open file.
        config=open(tilematrixsetmap_file, 'r')
        print ('Using tilematrixsetmap: ' + tilematrixsetmap_file)
    except IOError:
        mssg=str().join(['Cannot read tilematrixsetmap file:  ', tilematrixsetmap_file])
        sys.exit(mssg)
        
    tilematrixset_data = {}
    dom = xml.dom.minidom.parse(config)
    projectionElements = dom.getElementsByTagName('Projection')
    for projectionElement in projectionElements:
        projection_id = projectionElement.attributes['id'].value 
        getTileService = projectionElement.attributes['getTileService'].value
        topleftcorner = projectionElement.attributes['topLeftCorner'].value
        tilematrixsetmap = {}
        tileMatrixSetElements = projectionElement.getElementsByTagName("TileMatrixSet")
        for tileMatrixSetElement in tileMatrixSetElements:
            tilematrixsetmap[tileMatrixSetElement.attributes['level'].value] = tileMatrixSetElement.firstChild.nodeValue.strip()

        bboxes = read_getTileService(getTileService)
        tilematrixset_data[projection_id] = TileMatrixSetMap(projection_id, bboxes, topleftcorner.split(' ')[0], topleftcorner.split(' ')[1], tilematrixsetmap)
    
    return tilematrixset_data

def read_config(config_file):
    """
    Reads the log configuration file and returns the Apache log and custom output log formats.
    Arguments:
        config_file -- the location of the log configuration file
    """
    
    try:
        # Open file.
        config=open(config_file, 'r')
        print ('Using config: ' + config_file)
    except IOError:
        mssg=str().join(['Cannot read configuration file:  ', config_file])
        sys.exit(mssg)
        
    dom = xml.dom.minidom.parse(config)
    log_format = get_dom_tag_value(dom, 'ApacheLogFormat')
    log_output = get_dom_tag_value(dom, 'OutputLog')

    print "Using Apache Log Format: " + log_format
    print "Using Custom Log Output Format: " + log_output
    
    return (log_format, log_output)
            

def parse_request(request_string):
    """
    Parse OnEarth request parameters into a dictionary
    Arguments:
        request_string -- The URL request string
    """
    
    try:
        request_dict = lower_keys(urlparse.parse_qs(str(request_string).split('?')[1], keep_blank_values=True))
    except IndexError: # return blank values on error
        request_dict = {'service': [''], 'request':[''], 'version':[''], 'layer': [''], 'time': [''], 'tilematrixset': [''], 'tilematrix': [''], 'tilerow': [''], 'tilecol': [''], 'format': [''],
                        'layers': [''], 'srs':[''], 'styles': [''], 'width':[''], 'height':[''], 'bbox':[''], 'transparent':[''], 'bgcolor':[''], 'exceptions':[''], 'elevation':['']} #Tiled-WMS specific
    
    # add blank values if they don't exist in the request
    for key in ['service','request','version','layer','time','tilematrixset','tilematrix','tilerow','tilecol','format',
                'layers','srs','styles','width','height','bbox','transparent','bgcolor','exceptions','elevation']: #Tiled-WMS specific
        if key not in request_dict:
            request_dict[key] = ['']
            
    return request_dict


def translate_log(log_in, log_re, log_output, tilematrixset_data, wmts_translate_off):
    """
    Translates log message in Apache log format to a custom format 
    Arguments:
        log_in -- The input log message
        log_re -- Regex for the Apache log format
        log_output -- The custom output log format
    """
    
    log_out = ""
    message = re.match(log_re, log_in)
    if message:
        log_dict = message.groupdict()
        request = parse_request(str(log_dict['uri']))
        for key, value in request.iteritems():
            log_dict[key] = value[0]
        
        if (wmts_translate_off == False) and (log_dict['bbox'] != ''):
            try:
                log_dict = translate_wmts(log_dict, tilematrixset_data)
            except:
                log_dict = log_dict     
        try:
            log_out = log_output % log_dict
        except KeyError,e:
            print "Error: " + str(e) + " is not an available custom log field."
            sys.exit()
        
    return log_out


def translate_wmts(request_dict, tilematrixset_data):
    """
    Translates Tiled-WMS request to WMTS
    Arguments:
        request_dict -- Dictionary of request parameters and values
    """
    
#     print str(request_dict)
    
    projection = str(request_dict['srs'])
    request_bbox = str(request_dict['bbox']).split(",")
    tilesize = float(str(request_dict['width']))
    
    if projection == "EPSG:4326":
        units = 111319.490793274 # meters/degree
    else: # default to EPSG:4326
        units = 111319.490793274 # meters/degree
    
    # parse request_bbox to individual values
    request_minx = float(request_bbox[0])
    request_miny = float(request_bbox[1])
    request_maxx = float(request_bbox[2])
    request_maxy = float(request_bbox[3])
    
    x_size = request_maxx - request_minx
    y_size = request_maxy - request_miny
    
    # set top_left values
    top_left_minx = tilematrixset_data[projection].minx
    top_left_maxy = tilematrixset_data[projection].maxy
    
    # calculate additional top_left values for reference
    top_left_maxx = top_left_minx + x_size
    top_left_miny = top_left_maxy - y_size
    
    topleftbbox = str(top_left_minx)+","+str(top_left_miny)+","+str(top_left_maxx)+","+str(top_left_maxy)
#     print "Top Left BBOX:", topleftbbox
#     print "Request BBOX:",str(request_minx)+","+str(request_miny)+","+str(request_maxx)+","+str(request_maxy)
    
    # calculate col and row
    col = ((request_minx-top_left_minx)/x_size)
    row = ((request_miny-top_left_miny)/y_size)
    
    # calculate scale denominator for reference
    scale_denominator = (((x_size*2)/pixelsize)*units)/(tilesize*2)
#     print "Scale Denominator:", str(round(scale_denominator,10))

    try:
        tilematrixsetlevels = len(tilematrixset_data[projection].bboxes[request_dict['layers']])
    except:
        return request_dict # return if layer does not exist in getTileService
    tilematrixset = tilematrixset_data[projection].tilematrixsetmap[str(tilematrixsetlevels)]
    tilematrix = ''
    
    topleftbbox = [float(x) for x in topleftbbox.split(',')]
    for i, bbox in enumerate(tilematrixset_data[projection].bboxes[request_dict['layers']]):
        if topleftbbox == bbox:
            tilematrix = (tilematrixsetlevels-1)-i
            
    request_dict['scaledenominator'] = scale_denominator
    request_dict['tilematrixset'] = tilematrixset
    request_dict['tilematrix'] = tilematrix
    request_dict['tilecol'] = str(abs(int(col)))
    request_dict['tilerow'] = str(abs(int(row)))
    
    return request_dict


def lower_keys(x):
    """
    Lowers key in a dictionary to normalize case
    Arguments:
        x -- The dictionary key
    """    
    if isinstance(x, list):
        return [lower_keys(v) for v in x]
    if isinstance(x, dict):
        return dict((k.lower(), lower_keys(v)) for k, v in x.iteritems())
    return x


def get_dom_tag_value(dom, tag_name):
    """
    Return value of a tag from dom (XML file).
    Arguments:
        tag_name -- name of dom tag for which the value should be returned.
    """
    tag = dom.getElementsByTagName(tag_name)
    value = tag[0].firstChild.nodeValue.strip()
    return value


#-------------------------------------------------------------------------------

print toolName + ' ' + versionNumber

usageText = toolName + " --input [file] --output [file] --config [logs.xml] --tilematrixsetmap [tilematrixsetmap.xml] --date [YYYY-MM-DD] --quiet --tail --wmts_translate_off"

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--config',
                  action='store', type='string', dest='config', default='logs.xml',
                  help='Full path of log configuration file.  Default: logs.xml')
parser.add_option('-d', '--date',
                  action='store', type='string', dest='logdate', default=None,
                  help='Filter log for specified date [YYYY-MM-DD]')
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input',
                  help='The full path of the input log file')
parser.add_option('-m', '--tilematrixsetmap',
                  action='store', type='string', dest='tilematrixsetmap', default='tilematrixsetmap.xml',
                  help='Full path of configuration file containing TileMatrixSet mappings.  Default: tilematrixsetmap.xml')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output log file')
parser.add_option("-q", "--quiet", action="store_true", dest="quiet", 
                  default=False, help="Suppress log output to terminal")
parser.add_option("-t", "--tail", action="store_true", dest="tail", 
                  default=False, help="Tail the log file")
parser.add_option("-w", "--wmts_translate_off", action="store_true", dest="wmts_translate_off", 
                  default=False, help="Do not translate Tiled-WMS tile requests to WMTS")

# Read command line args.
(options, args) = parser.parse_args()

quiet = options.quiet
tail = options.tail

if options.input:
    input_log = options.input
else:
    print "input log file must be specified...exiting"
    exit()
if options.output:
    output_log = options.output
else:
    print "output log file must be specified...exiting"
    exit()
if options.logdate != None:
    if tail:
        print "date cannot be specified with tail option...exiting"
        exit()
    try:
        logdate = time.strptime(options.logdate,"%Y-%m-%d")
        apachedate = time.strftime('%d/%b/%Y', logdate)
        print "Filtering for date", apachedate
    except ValueError,e:
        print str(e)
        exit()

try:    
    output_file = open(output_log,'w')
except IOError,e:
    print str(e)
    exit()
print "opening " + input_log

if options.wmts_translate_off == False:
    tilematrixset_data = read_tilematrixsetmap(options.tilematrixsetmap)
else:
    tilematrixset_data = None

log_format, log_output = read_config(options.config)

# only one Apache log format supported for now
combined = '"%h %l %u %t \\"%r\\" %>s %b \\"%{Referer}i\\" \\"%{User-Agent}i\\""'
if log_format == combined:
    log_re = '(?P<requestor>[.:0-9a-fA-F]+) - - \[(?P<timestamp>.*?)\] "(?P<uri>.*?) HTTP/1.\d" (?P<statuscode>\d+) (?P<bytes>\d+|-) "(?P<referrer>.*?)" "(?P<useragent>.*?)"'
else:
    print "The specified Apache log format is not supported by this tool: " + log_format
    print "Please use: " + combined
    exit()
        
if tail:
    try:
        testopen = open(input_log, 'r')
    except IOError,e:
        print str(e)
        if "Permission denied" in str(e):
            print "Please rerun with appropriate permissions or sudo"
        exit()
    
    logfile = subprocess.Popen(['tail','-F',input_log], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    
    p = select.poll()
    p.register(logfile.stdout)
     
    while True:
        if p.poll(1):
            output_file.write(logfile.stdout.readline())
            if quiet == False:
                print translate_log(logfile.stdout.readline().strip(), log_re, log_output, tilematrixset_data, options.wmts_translate_off)
        time.sleep(.001)
        
else:
    try:
        input_file = open(input_log, 'r')
    except IOError,e:
        print str(e)
        if "Permission denied" in str(e):
            print "Please rerun with appropriate permissions or sudo"
        exit()
        
    for line in input_file:
        if options.logdate == None:
            log_out = translate_log(line, log_re, log_output, tilematrixset_data, options.wmts_translate_off)
            if quiet == False:
                print log_out
            output_file.write(log_out+"\n")
        else:
            if apachedate in line:
                log_out = translate_log(line, log_re, log_output, tilematrixset_data, options.wmts_translate_off)
                if quiet == False:
                    print log_out
                output_file.write(log_out+"\n")            
        
exit()