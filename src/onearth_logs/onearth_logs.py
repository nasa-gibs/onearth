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
import xml.dom.minidom

toolName = "onearth_logs.py"
versionNumber = "v0.3"

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


def translate_log(log_in, log_re, log_output):
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
        try:
            log_out = log_output % log_dict
        except KeyError,e:
            print "Error: " + str(e) + " is not an available custom log field."
            sys.exit()
        
    return log_out

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

usageText = toolName + " --input [file] --output [file] --config [logs.xml] --date [YYYY-MM-DD] --quiet --rotate_daily --tail"

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--config',
                  action='store', type='string', dest='config', default='logs.xml',
                  help='Full path of log configuration file.  Default: logs.xml')
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input',
                  help='The full path of the input log file')
parser.add_option('-o', '--output',
                  action='store', type='string', dest='output',
                  help='The full path of the output log file')
parser.add_option("-q", "--quiet", action="store_true", dest="quiet", 
                  default=False, help="Suppress log output to terminal")
parser.add_option("-t", "--tail", action="store_true", dest="tail", 
                  default=False, help="Tail the log file")

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

try:    
    output_file = open(output_log,'w')
except IOError,e:
    print str(e)
    exit()
print "opening " + input_log

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
                print translate_log(logfile.stdout.readline().strip(), log_re, log_output)
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
        log_out = translate_log(line, log_re, log_output)
        if quiet == False:
            print log_out
        output_file.write(log_out+"\n")
        
exit()