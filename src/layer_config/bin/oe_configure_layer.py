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
# oe_configure_layer.py
# The OnEarth Layer Configurator.
#
#
# Example XML configuration file:
#
'''
<?xml version="1.0" encoding="UTF-8"?>
<LayerConfiguration>
 <Identifier>MODIS_Aqua_Cloud_Top_Temp_Night</Identifier>
 <Title>MODIS AQUA Nighttime Cloud Top Temperature</Title>
 <FileNamePrefix>MYR6CTTLLNI</FileNamePrefix>
 <Compression>PNG</Compression>
 <Levels>6</Levels>
 <EmptyTileSize offset="0">1397</EmptyTileSize>
 <Projection>EPSG:4326</Projection> 
 <Pattern><![CDATA[request=GetMap&layers=MODIS_Aqua_Cloud_Top_Temp_Night&srs=EPSG:4326&format=image%2Fpng&styles=&time=[-0-9]*&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <Pattern><![CDATA[request=GetMap&layers=MODIS_Aqua_Cloud_Top_Temp_Night&srs=EPSG:4326&format=image%2Fpng&styles=&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <Pattern><![CDATA[LAYERS=MODIS_Aqua_Cloud_Top_Temp_Night&FORMAT=image%2Fpng&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&SRS=EPSG%3A4326&BBOX=[-,\.0-9+Ee]*&WIDTH=512&HEIGHT=512]]></Pattern>
 <Pattern><![CDATA[service=WMS&request=GetMap&version=1.1.1&srs=EPSG:4326&layers=MODIS_Aqua_Cloud_Top_Temp_Night&styles=default&transparent=TRUE&format=image%2Fpng&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <EnvironmentConfig>/layer_config/conf/environment_geographic.xml</EnvironmentConfig>
 <ArchiveLocation static="false" year="true">/data/EPSG4326/MYR6CTTLLNI</ArchiveLocation>
 <ColorMap>http://localhost/colormap/sample.xml</ColorMap>
 <Time>DETECT/2014-03-28/P1D</Time>
 <Time>2014-04-01/DETECT/P1D</Time>
</LayerConfiguration>
'''
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014

import os
import subprocess
import sys
import socket
import urllib
import urllib2
import xml.dom.minidom
import logging
import shutil
import distutils.spawn
from datetime import datetime, time, timedelta
from time import asctime
from optparse import OptionParser

versionNumber = '0.3'

class WMTSEndPoint:
    """End point data for WMTS"""
    
    def __init__(self, path, cacheConfig, getCapabilities):
        self.path = path
        self.cacheConfig = cacheConfig
        self.getCapabilities = getCapabilities
        
class TWMSEndPoint:
    """End point data for TWMS"""
    
    def __init__(self, path, cacheConfig, getCapabilities, getTileService):
        self.path = path
        self.cacheConfig = cacheConfig
        self.getCapabilities = getCapabilities
        self.getTileService = getTileService

class Environment:
    """Environment information for layer(s)"""
    
    def __init__(self, cache, getCapabilities_wmts, getCapabilities_twms, getTileService, wmtsServiceUrl, twmsServiceUrl):
        self.cache = cache
        self.getCapabilities_wmts = getCapabilities_wmts
        self.getCapabilities_twms = getCapabilities_twms
        self.getTileService = getTileService
        self.wmtsServiceUrl = wmtsServiceUrl
        self.twmsServiceUrl = twmsServiceUrl
        
class Projection:
    """Projection information for layer"""
    
    def __init__(self, projection_id, projection_dir, projection_wkt, projection_layer_template, projection_tilematrixsets):
        self.id = projection_id
        self.dir = projection_dir
        self.wkt = projection_wkt
        self.layer_template = projection_layer_template
        self.tilematrixsets = projection_tilematrixsets

def sigevent(type, mssg, sigevent_url):
    """
    Send a message to sigevent service.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
                        'http://localhost:8100/sigevent/events/create'
    """
    # Constrain mssg to 256 characters (including '...').
    if len(mssg) > 256:
        mssg=str().join([mssg[0:253], '...'])
    print str().join(['sigevent ', type, ' - ', mssg])
    # Remove any trailing slash from URL.
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any question mark from URL.  It is added later.
    if sigevent_url[-1] == '?':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any trailing slash from URL.  (Again.)
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Define sigevent parameters that get encoded into the URL.
    data={}
    data['type']=type
    data['description']=mssg
    data['computer']=socket.gethostname()
    data['source']='ONEARTH'
    data['format']='TEXT'
    data['category']='ONEARTH'
    data['provider']='GIBS'
    # Format sigevent parameters that get encoded into the URL.
    values=urllib.urlencode(data)
    # Create complete URL.
    full_url=sigevent_url+'?'+values
    data=urllib2.urlopen(full_url)

def log_info_mssg(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print mssg
    logging.info(mssg)

def log_info_mssg_with_timestamp(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print asctime()
    logging.info(asctime())
    log_info_mssg(mssg)

def log_sig_warn(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(asctime())
    logging.warning(mssg)
    # Send to sigevent.
    try:
        sent=sigevent('WARN', mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'

def log_sig_exit(type, mssg, sigevent_url):
    """
    Send a message to the log, to sigevent, and then exit.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Add "Exiting" to mssg.
    mssg=str().join([mssg, '  Exiting oe_configure_layer.'])
    # Send to sigevent.
    try:
        sent=sigevent(type, mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'
    # Send to log.
    if type == 'INFO':
        log_info_mssg_with_timestamp(mssg)
    elif type == 'WARN':
        logging.warning(asctime())
        logging.warning(mssg)
    elif type == 'ERROR':
        logging.error(asctime())
        logging.error(mssg)
    # Exit.
    sys.exit()

def log_the_command(command_list):
    """
    Send a command list to the log.
    Arguments:
        command_list -- list containing all elements of a subprocess command.
    """
    # Add a blank space between each element.
    spaced_command=''
    for ndx in range(len(command_list)):
        spaced_command=str().join([spaced_command, command_list[ndx], ' '])
    # Send to log.
    log_info_mssg_with_timestamp(spaced_command)

def get_dom_tag_value(dom, tag_name):
    """
    Return value of a tag from dom (XML file).
    Arguments:
        tag_name -- name of dom tag for which the value should be returned.
    """
    tag = dom.getElementsByTagName(tag_name)
    value = tag[0].firstChild.nodeValue.strip()
    return value

def change_dom_tag_value(dom, tag_name, value):
    """
    Return value of a tag from dom (XML file).
    Arguments:
        tag_name -- name of dom tag for which the value should be returned.
        value -- the replacement value.
    """
    tag = dom.getElementsByTagName(tag_name)
    tag[0].firstChild.nodeValue = value
    
def run_command(cmd):
    """
    Runs the provided command on the terminal.
    Arguments:
        cmd -- the command to be executed.
    """
    print '\nRunning command: ' + cmd
    process = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    process.wait()
    for output in process.stdout:
        print output.strip()
    for error in process.stderr:
        sigevent('ERROR', error.strip(), sigevent_url)
        raise Exception(error.strip())
    
def add_trailing_slash(directory_path):
    """
    Add trailing slash if one is not already present.
    Argument:
        directory_path -- path to which trailing slash should be confirmed.
    """
    # Add trailing slash.
    if directory_path[-1] != '/':
        directory_path=str().join([directory_path, '/'])
    # Return directory_path with trailing slash.
    return directory_path

def get_environment(environmentConfig):
    """
    Gets environment metadata from a environment configuration file.
    Arguments:
        environmentConfig -- the location of the projection configuration file
    """
    try:
        # Open file.
        environment_config=open(environmentConfig, 'r')
        print ('\nUsing environment config: ' + environmentConfig + '\n')
    except IOError:
        mssg=str().join(['Cannot read environment configuration file:  ', environmentConfig])
        sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
        
    dom = xml.dom.minidom.parse(environment_config)
    try:
        cacheConfig = get_dom_tag_value(dom, 'CacheLocation')
    except IndexError:
        log_sig_exit('ERROR', 'Required <CacheLocation> element is missing in ' + conf, sigevent_url)
        
    # Services
    try:
        getTileService = get_dom_tag_value(dom, 'GetTileServiceLocation')
    except IndexError:
        getTileService = None
    
    getCapabilitiesElements = dom.getElementsByTagName('GetCapabilitiesLocation')
    wmts_getCapabilities = None
    twms_getCapabilities = None
    for getCapabilities in getCapabilitiesElements:
        try:
            if str(getCapabilities.attributes['service'].value).lower() == "wmts":
                wmts_getCapabilities = getCapabilities.firstChild.nodeValue.strip()
            elif str(getCapabilities.attributes['service'].value).lower() == "twms":
                twms_getCapabilities = getCapabilities.firstChild.nodeValue.strip()
        except KeyError:
            log_sig_exit('ERROR', 'service is not defined in <GetCapabilitiesLocation>', sigevent_url)
            
    serviceUrlElements = dom.getElementsByTagName('ServiceURL')
    wmtsServiceUrl = None
    twmsServiceUrl = None
    for serviceUrl in serviceUrlElements:
        try:
            if str(serviceUrl.attributes['service'].value).lower() == "wmts":
                wmtsServiceUrl = serviceUrl.firstChild.nodeValue.strip()
            elif str(serviceUrl.attributes['service'].value).lower() == "twms":
                twmsServiceUrl = serviceUrl.firstChild.nodeValue.strip()
        except KeyError:
            log_sig_exit('ERROR', 'service is not defined in <ServiceURL>', sigevent_url)        
    
    if not os.path.exists(twms_getCapabilities):
        os.makedirs(twms_getCapabilities)
    if not os.path.exists(wmts_getCapabilities):
        os.makedirs(wmts_getCapabilities)
        
    return Environment(add_trailing_slash(cacheConfig), 
                       add_trailing_slash(wmts_getCapabilities), 
                       add_trailing_slash(twms_getCapabilities), 
                       add_trailing_slash(getTileService),
                       add_trailing_slash(wmtsServiceUrl), 
                       add_trailing_slash(twmsServiceUrl))
    
def get_projection(projectionId, projectionConfig):
    """
    Gets projection metadata from a projection configuration file based on the projection ID.
    Arguments:
        projectionId -- the name of the projection and key used
        projectionConfig -- the location of the projection configuration file
    """
    try:
        # Open file.
        projection_config=open(projectionConfig, 'r')
        print ('\nUsing projection config: ' + projectionConfig + '\n')
    except IOError:
        mssg=str().join(['Cannot read projection configuration file:  ', projectionConfig])
        sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
        
    dom = xml.dom.minidom.parse(projection_config)
    projection = None
    projectionTags = dom.getElementsByTagName('Projection')
    for projectionElement in projectionTags:
        if projectionElement.attributes['id'].value == projectionId:
            wkt = projectionElement.getElementsByTagName('WKT')[0].firstChild.data.strip()
            layer_template = projectionElement.getElementsByTagName('Layer')[0].toxml()
            tilematrixsets = {}
            tileMatrixSetElements = projectionElement.getElementsByTagName('TileMatrixSetMap')[0].getElementsByTagName('TileMatrixSet')
            for tilematrixset in tileMatrixSetElements:
                tilematrixsets[tilematrixset.attributes['level'].value] = tilematrixset.firstChild.nodeValue.strip()
            projection = Projection(projectionId, projectionElement.attributes['dir'].value, wkt, layer_template, tilematrixsets)
    
    if projection == None:
        mssg = "Projection " + projectionId + " could not be found in projection configuration file."
        sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    
    return projection

def detect_time(time, cacheLocation, fileNamePrefix, year):
    """
    Checks time element to see if start or end time must be detected on the file system.
    Arguments:
        time -- the time element (DETECT) keyword is utilized
        cacheLocation -- the location of the cache data
        fileNamePrefix -- the prefix of the MRF files
        year -- whether or not the layer uses a year-based directory structure
    """
    times = []
    print "\nAssessing time", time
    time = time.upper()
    detect = "DETECT"
    period = 'P1D' # default to period of 1 day
    cacheLocation = add_trailing_slash(cacheLocation)
    
    if time == detect or time == '':
    #detect everything including breaks in date (assumes period of 1 day)
        dates = []
        for dirname, dirnames, filenames in os.walk(cacheLocation+fileNamePrefix, followlinks=True):
            # Print subdirectories
            for subdirname in dirnames:
                print "Searching:", os.path.join(dirname, subdirname)

            for filename in filenames:
                filetime = filename[-12:-5]
                try:
                    filedate = datetime.strptime(filetime,"%Y%j")
                    dates.append(filedate)
                except ValueError:
                    print "Skipping", filename
        dates = sorted(list(set(dates)))
        # Search for date ranges
        if len(dates) == 0:
            message = "No files with dates found for '" + fileNamePrefix + "' in '" + cacheLocation + "' - please check if data exists."
            log_sig_warn(message, sigevent_url)
            startdate = datetime.now() # default to now
        else:
            startdate = min(dates)
        enddate = startdate # set end date to start date for lone dates
        for i, d in enumerate(dates):
            # print d
            next_day = d + timedelta(days=1)
            try:
                if dates[i+1] == next_day:
                    enddate = next_day # set end date to next existing day
                else: # end of range
                    start = datetime.strftime(startdate,"%Y-%m-%d")
                    end = datetime.strftime(enddate,"%Y-%m-%d")
                    times.append(start+'/'+end+'/'+period)
                    startdate = dates[i+1] # start new range loop
                    enddate = startdate
            except IndexError:
                # breaks when loop completes
                start = datetime.strftime(startdate,"%Y-%m-%d")
                end = datetime.strftime(enddate,"%Y-%m-%d")
                times.append(start+'/'+end+'/'+period)
                print "Time ranges: " + ", ".join(times)
                return times
    
    else:
        intervals = time.split('/')
        if intervals[0][0] == 'P': #starts with period, so no start date
            start = detect
        else:
            start = ''
        for interval in list(intervals):
            if interval[0] == 'P':
                period = interval
                intervals.remove(interval)
        if len(intervals) == 2:
            start = intervals[0]
            end = intervals[1]
        else:
            if start == detect:
                end = intervals[0]
            else:
                start = intervals[0]
                end = detect
        
        if start==detect or end==detect:
            if year == True: # get newest and oldest years
                years = []
                for subdirname in os.walk(cacheLocation+fileNamePrefix, followlinks=True).next()[1]:
                    if subdirname != 'YYYY':
                        years.append(subdirname)
                years = sorted(years)
                newest_year = years[-1]
                oldest_year = years[0]
                print "Year directories available: " + ",".join(years)
                            
        if start==detect:
            for dirname, dirnames, filenames in os.walk(cacheLocation+fileNamePrefix+'/'+oldest_year, followlinks=True):
                dates = []
                for filename in filenames:
                    filetime = filename[-12:-5]
                    filedate = datetime.strptime(filetime,"%Y%j")
                    dates.append(filedate)
                startdate = min(dates)
                start = datetime.strftime(startdate,"%Y-%m-%d")
        
        if end==detect:
            for dirname, dirnames, filenames in os.walk(cacheLocation+fileNamePrefix+'/'+newest_year, followlinks=True):
                dates = []
                for filename in filenames:
                    filetime = filename[-12:-5]
                    filedate = datetime.strptime(filetime,"%Y%j")
                    dates.append(filedate)            
                enddate = max(dates)
                end = datetime.strftime(enddate,"%Y-%m-%d")   
        
        print "Time: start="+start+" end="+end+" period="+period
        time = start+'/'+end+'/'+period
        times.append(time)
        
    return times
    
#-------------------------------------------------------------------------------   

print 'OnEarth Layer Configurator v' + versionNumber

if os.environ.has_key('LCDIR') == False:
    print 'LCDIR environment variable not set.\nLCDIR should point to your OnEarth layer_config directory.\n'
    lcdir = os.path.abspath(os.path.dirname(__file__) + '/..')
else:
    lcdir = os.environ['LCDIR']

usageText = 'oe_configure_layer.py --conf_file [layer_configuration_file.xml] --layer_dir [$LCDIR/conf/] --projection_config [projection.xml] --sigevent_url [url] --time [ISO 8601] --restart_apache --no_xml --no_cache --no_twms --no_wmts'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--conf_file',
                  action='store', type='string', dest='configuration_filename',
                  help='Full path of layer configuration filename.')
parser.add_option('-d', '--layer_dir',
                  action='store', type='string', dest='configuration_directory',
                  default=lcdir+'/layers/',
                  help='Full path of directory containing configuration files.  Default: $LCDIR/layers/')
parser.add_option("-n", "--no_twms",
                  action="store_true", dest="no_twms", 
                  default=False, help="Do not use configurations for Tiled-WMS")
parser.add_option('-p', '--projection_config',
                  action='store', type='string', dest='projection_configuration',
                  default=lcdir+'/conf/projection.xml',
                  help='Full path of projection configuration file.  Default: $LCDIR/conf/projection.xml')
parser.add_option("-r", "--restart_apache",
                  action="store_true", dest="restart", 
                  default=False, help="Restart the Apache server on completion (requires sudo).")
parser.add_option('-s', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')
parser.add_option('-t', '--time',
                  action='store', type='string', dest='time',
                  help='ISO 8601 time(s) for single configuration file (conf_file must be specified).')
parser.add_option("-w", "--no_wmts",
                  action="store_true", dest="no_wmts", 
                  default=False, help="Do not use configurations for WMTS")
parser.add_option("-x", "--no_xml",
                  action="store_true", dest="no_xml", 
                  default=False, help="Do not generate getCapabilities and getTileService XML.")
parser.add_option("-z", "--no_cache",
                  action="store_true", dest="no_cache", 
                  default=False, help="Do not copy cache configuration files to cache location.")

# Read command line args.
(options, args) = parser.parse_args()
# Configuration filename.
configuration_filename = options.configuration_filename
# Configuration directory.
configuration_directory = options.configuration_directory
# No XML configurations (getCapabilities, getTileService)
no_xml = options.no_xml
# No cache configuration.
no_cache = options.no_cache
# No Tiled-WMS configuration.
no_twms = options.no_twms
# No WMTS configuration.
no_wmts = options.no_wmts
# Do restart Apache.
restart = options.restart
# Time for conf file.
configuration_time = options.time
# Projection configuration
projection_configuration = options.projection_configuration

# Sigevent URL.
sigevent_url = options.sigevent_url
  
print 'Using ' + lcdir + ' as $LCDIR.'

if no_xml:
    print "no_xml specified, getCapabilities and getTileService files will not be generated"
if no_cache:
    print "no_cache specified, cache configuration files will not be generated"
    restart = False
if no_xml and no_cache:
    print "no_xml and no_cache specified, nothing to do...exiting"
    exit()
    
if configuration_time:
    if configuration_filename == None:
        print "A configuration file must be specified with --time"
        exit()
    else:
        print "Using time='" + configuration_time + "' for " + configuration_filename

# Read XML configuration files.

conf_files = []
wmts_endpoints = {}
twms_endpoints = {}

if not options.configuration_filename:
    conf = subprocess.Popen('ls ' + configuration_directory + '/*.xml',shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    for line in conf:
        conf_files.append(line.strip())
else:
    # use only the solo MRF when specified
    conf_files.append(configuration_filename)
    
print 'Configuration file(s):'
print conf_files
if conf_files==[]:
    mssg = 'No configuration files found.'
    sigevent('ERROR', mssg, sigevent_url)
    sys.exit(mssg)
    
for conf in conf_files:
    
    try:
        # Open file.
        config_file=open(conf, 'r')
        print ('\nUsing config: ' + conf)
    except IOError:
        mssg=str().join(['Cannot read configuration file:  ', 
                         conf])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        dom = xml.dom.minidom.parse(config_file)
        
        #Required parameters
        try:
            identifier = get_dom_tag_value(dom, 'Identifier')
        except IndexError:
            log_sig_exit('ERROR', 'Required <Identifier> element is missing in ' + conf, sigevent_url)
        try:
            title = get_dom_tag_value(dom, 'Title')
        except IndexError:
            log_sig_exit('ERROR', 'Required <Title> element is missing in ' + conf, sigevent_url)
        try:
            compression = get_dom_tag_value(dom, 'Compression')
            compression = compression.upper()
            if compression == "JPG":
                compression = "JPEG"
            if compression == "PPNG":
                compression = "PNG"
            if compression not in ["JPEG", "PNG"]:
                log_sig_exit('ERROR', '<Compression> must be either JPEG or PNG in ' + conf, sigevent_url)
        except IndexError:
            log_sig_exit('ERROR', 'Required <Compression> element is missing in ' + conf, sigevent_url)
        try:
            levels = get_dom_tag_value(dom, 'Levels')
        except IndexError:
            log_sig_exit('ERROR', 'Required <Levels> element is missing in ' + conf, sigevent_url)
        try:
            emptyTileSize = int(get_dom_tag_value(dom, 'EmptyTileSize'))
        except IndexError:
            log_sig_exit('ERROR', 'Required <EmptyTileSize> element is missing in ' + conf, sigevent_url)
        try:
            fileNamePrefix = get_dom_tag_value(dom, 'FileNamePrefix')
        except IndexError:
            log_sig_exit('ERROR', 'Required <FileNamePrefix> element is missing in ' + conf, sigevent_url)
        try:
            environmentConfig = get_dom_tag_value(dom, 'EnvironmentConfig')
            environment = get_environment(environmentConfig)
        except IndexError:
            log_sig_exit('ERROR', 'Required <EnvironmentConfig> element is missing in ' + conf, sigevent_url)
            
        cacheConfig = environment.cache
        wmts_getCapabilities = environment.getCapabilities_wmts
        twms_getCapabilities = environment.getCapabilities_twms
        getTileService = environment.getTileService
        wmtsServiceUrl = environment.wmtsServiceUrl
        twmsServiceUrl = environment.twmsServiceUrl

        # Optional parameters
        try:
            archiveLocation = get_dom_tag_value(dom, 'ArchiveLocation')
        except IndexError:
            archiveLocation = None
        try:
            static = dom.getElementsByTagName('ArchiveLocation')[0].attributes['static'].value.lower() in ['true']
        except:
            static = True
        try:
            year = dom.getElementsByTagName('ArchiveLocation')[0].attributes['year'].value.lower() in ['true']
        except:
            year = False
        try:
            headerFileName = get_dom_tag_value(dom, 'HeaderFileName')
        except IndexError:
            headerFileName = None
        try:
            dataFileLocation = get_dom_tag_value(dom, 'DataFileLocation')
        except IndexError:
            dataFileLocation = None
        try:
            indexFileLocation = get_dom_tag_value(dom, 'IndexFileLocation')
        except IndexError:
            indexFileLocation = None
        try:
            projection = get_projection(get_dom_tag_value(dom, 'Projection'), projection_configuration)
        except IndexError:
            projection = None 
        try:
            emptyTileOffset = dom.getElementsByTagName('EmptyTileSize')[0].attributes['offset'].value
        except:
            emptyTileOffset = 0

        try:
            colormap = get_dom_tag_value(dom, 'ColorMap')
        except IndexError:
            colormap = None
            
        # Patterns
        patterns = []
        patternTags = dom.getElementsByTagName('Pattern')
        for pattern in patternTags:
            patterns.append(pattern.firstChild.data.strip())
            
        # Time
        if configuration_time:
            times = configuration_time.split(',')
        else:  
            times = []  
            timeTags = dom.getElementsByTagName('Time')
            for time in timeTags:
                try:
                    times.append(time.firstChild.data.strip())
                except AttributeError:
                    times.append('')
        
        # Set end points
        try:
            wmtsEndPoint = get_dom_tag_value(dom, 'WMTSEndPoint')
        except IndexError:
            if projection != None:
                wmtsEndPoint = 'wmts/' + projection.dir
            else:
                log_sig_exit('ERROR', 'Projection directory is not defined', sigevent_url)
        try:
            twmsEndPoint = get_dom_tag_value(dom, 'TWMSEndPoint')
        except IndexError:
            if projection != None:
                twmsEndPoint = 'twms/' + projection.dir
            else:
                log_sig_exit('ERROR', 'Projection directory is not defined', sigevent_url)
                
        wmts_endpoints[wmtsEndPoint] = WMTSEndPoint(wmtsEndPoint, cacheConfig, wmts_getCapabilities)
        twms_endpoints[twmsEndPoint] = TWMSEndPoint(twmsEndPoint, cacheConfig, twms_getCapabilities, getTileService)
        
        # Close file.
        config_file.close()
     
    log_info_mssg('config: Identifier: ' + identifier)
    log_info_mssg('config: Title: ' + title)
    log_info_mssg('config: FileNamePrefix: ' + fileNamePrefix)
    log_info_mssg('config: Compression: ' + compression)
    log_info_mssg('config: Levels: ' + levels)
    log_info_mssg('config: EmptyTileSize: ' + str(emptyTileSize))
    log_info_mssg('config: EmptyTileOffset: ' + str(emptyTileOffset))
    if headerFileName:
        log_info_mssg('config: HeaderFileName: ' + headerFileName)
    if archiveLocation:
        log_info_mssg('config: ArchiveLocation static=' + str(static) + ' year=' + str(year) + ': ' + archiveLocation)
    if dataFileLocation:
        log_info_mssg('config: DataFileLocation: ' + dataFileLocation)
    if indexFileLocation:
        log_info_mssg('config: IndexFileLocation: ' + indexFileLocation)
    if projection:
        log_info_mssg('config: Projection: ' + str(projection.id))
    if getTileService:
        log_info_mssg('config: GetTileServiceLocation: ' + str(getTileService))
    if wmts_getCapabilities:
        log_info_mssg('config: WMTS GetCapabilitiesLocation: ' + str(wmts_getCapabilities))
    if twms_getCapabilities:
        log_info_mssg('config: TWMS GetCapabilitiesLocation: ' + str(twms_getCapabilities))
    if cacheConfig:
        log_info_mssg('config: CacheLocation: ' + str(cacheConfig))
    if wmtsEndPoint:
        log_info_mssg('config: WMTSEndPoint: ' + str(wmtsEndPoint))
    if twmsEndPoint:
        log_info_mssg('config: TWMSEndPoint: ' + str(twmsEndPoint))
    if colormap:
        log_info_mssg('config: ColorMap: ' + str(colormap))
    log_info_mssg('config: Patterns: ' + str(patterns))
    if len(times) > 0:
        log_info_mssg('config: Time: ' + str(times))
    
    # get MRF archetype

    if archiveLocation != None:
        archiveLocation = add_trailing_slash(archiveLocation)
        # check if absolute path or else use relative to cache location
        if archiveLocation[0] == '/':
            mrfLocation = archiveLocation
        else:
            mrfLocation = cacheConfig + archiveLocation
    else: # use archive location relative to cache if not defined
        mrfLocation = add_trailing_slash(cacheConfig)
    if year == True:
        if archiveLocation != None:
            mrfLocation =  mrfLocation +'YYYY/'
        else:
            mrfLocation =  mrfLocation + fileNamePrefix +'/YYYY/'
    
    if static == True:
        mrf = mrfLocation + fileNamePrefix + '.mrf'
        mrf_base = fileNamePrefix + '.mrf'
        if headerFileName == None:
            headerFileName = mrf
    else:
        mrf = mrfLocation + fileNamePrefix + 'TTTTTTT_.mrf'
        mrf_base = fileNamePrefix + 'TTTTTTT_.mrf'
        if headerFileName == None:
            headerFileName = mrf
    
    if indexFileLocation == None:
        if archiveLocation != None and archiveLocation[0] == '/':
            # use absolute path of archive
            indexFileLocation = mrf.replace('.mrf','.idx')
        else:
            # use relative path to cache
            indexFileLocation = mrf.replace(cacheConfig,'').replace('.mrf','.idx')
        
    if dataFileLocation == None:
        if archiveLocation != None and archiveLocation[0] == '/':
            # use absolute path of archive
            dataFileLocation = mrf
        else:
            # use relative path to cache
            dataFileLocation = mrf.replace(cacheConfig,'')
        if compression.lower() in ['jpg', 'jpeg']:
            dataFileLocation = dataFileLocation.replace('.mrf','.pjg')
            mrf_format = 'image/jpeg'
        else:
            dataFileLocation = dataFileLocation.replace('.mrf','.ppg')
            mrf_format = 'image/png'
        
    log_info_mssg('MRF: ' + mrf)
    
    # Modify MRF Archetype
    try:
        # Open file.
        mrf_file=open(headerFileName, 'r')
    except IOError:
        mssg=str().join(['Cannot read MRF header file:  ', 
                         headerFileName])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        mrf_dom = xml.dom.minidom.parse(mrf_file)
    
    mrf_meta = mrf_dom.getElementsByTagName('MRF_META')[0]
    try:
        change_dom_tag_value(mrf_dom, 'Compression', compression)
    except IndexError: #Add Compression tag if it is missing
        rasterElement = mrf_dom.getElementsByTagName('Raster')[0]
        compressionElement = mrf_dom.createElement('Compression')
        compressionElement.appendChild(mrf_dom.createTextNode(compression))
        rasterElement.appendChild(compressionElement)
    
    rsets = mrf_dom.getElementsByTagName('Rsets')[0]
    dataFileNameElement = mrf_dom.createElement('DataFileName')
    dataFileNameElement.appendChild(mrf_dom.createTextNode(dataFileLocation))
    indexFileNameElement = mrf_dom.createElement('IndexFileName')
    indexFileNameElement.appendChild(mrf_dom.createTextNode(indexFileLocation))
    rsets.appendChild(dataFileNameElement)
    rsets.appendChild(indexFileNameElement)
    
    twms = mrf_dom.createElement('TWMS')
    levelsElement = mrf_dom.createElement('Levels')
    levelsElement.appendChild(mrf_dom.createTextNode(levels))
    emptyInfoElement = mrf_dom.createElement('EmptyInfo')
    emptyInfoElement.setAttribute('size', str(emptyTileSize))
    emptyInfoElement.setAttribute('offset', str(emptyTileOffset))
    twms.appendChild(levelsElement)
    twms.appendChild(emptyInfoElement)

    if colormap:
        metadataElement = mrf_dom.createElement('Metadata')
        metadataElement.appendChild(mrf_dom.createTextNode(colormap))
        twms.appendChild(twms.appendChild(metadataElement))
    
    patternElements = []
    for pattern in patterns:
        patternElements.append(mrf_dom.createElement('Pattern'))
        patternElements[-1].appendChild(mrf_dom.createCDATASection(pattern))
    
    for patternElement in patternElements:
        twms.appendChild(patternElement)
    
    # Time elements
    if static == False:
        timeElements = []
        for time in times:
            detected_times = detect_time(time, cacheConfig, fileNamePrefix, year)
            for detected_time in detected_times:
                timeElements.append(mrf_dom.createElement('Time'))
                timeElements[-1].appendChild(mrf_dom.createTextNode(detected_time))
        
        for timeElement in timeElements:
            twms.appendChild(timeElement)
                
    mrf_meta.appendChild(twms)
        
    if projection:
        projectionElement = mrf_dom.createElement('Projection')
        projectionElement.appendChild(mrf_dom.createCDATASection(projection.wkt))
        mrf_meta.appendChild(projectionElement)
    
    if not os.path.exists(lcdir+'/'+twmsEndPoint):
        os.makedirs(lcdir+'/'+twmsEndPoint)
    if not os.path.exists(lcdir+'/'+wmtsEndPoint):
        os.makedirs(lcdir+'/'+wmtsEndPoint)
        
    twms_mrf_filename = lcdir+'/'+twmsEndPoint+'/'+mrf_base
    twms_mrf_file = open(twms_mrf_filename,'w+')
    mrf_dom.writexml(twms_mrf_file)
    
    wmts_mrf_filename = lcdir+'/'+wmtsEndPoint+'/'+mrf_base
    wmts_mrf_file = open(wmts_mrf_filename,'w+')
    
    twms_mrf_file.seek(0)
    lines = twms_mrf_file.readlines()
    lines[0] = '<MRF_META>\n'
    lines[-1] = lines[-1].replace('<TWMS>','<TWMS>\n\t').replace('</Levels>','</Levels>\n\t').replace('<Pattern>','\n\t<Pattern>'). \
        replace('<Time>','\n\t<Time>').replace('<Metadata>','\n\t<Metadata>').replace('</TWMS>','\n</TWMS>\n'). \
        replace('</MRF_META>','\n</MRF_META>\n') 
    #get_mrfs is picky about line breaks
    
    twms_mrf_file.seek(0)
    twms_mrf_file.truncate()
    twms_mrf_file.writelines(lines)
    
    # change patterns for WMTS
    pattern_replaced = False
    wmts_pattern = "<![CDATA[SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=%s&STYLE=(default)?&TILEMATRIXSET=%s&TILEMATRIX=[0-9]*&TILEROW=[0-9]*&TILECOL=[0-9]*&FORMAT=%s]]>" % (identifier, projection.tilematrixsets[levels], mrf_format.replace("/","%2F"))
    for line in lines:
        if '<Pattern>' in line:
            if pattern_replaced == False:
                patternline = line.split('Pattern')
                line = patternline[0] + "Pattern>" + wmts_pattern + "</Pattern" + patternline[-1]
                pattern_replaced = True
            else:
                line = ''
        wmts_mrf_file.write(line)
    
    twms_mrf_file.close()
    wmts_mrf_file.close()
    mrf_file.close()
    
    print '\n'+ twms_mrf_filename + ' configured successfully\n'
    print '\n'+ wmts_mrf_filename + ' configured successfully\n'


# Modify service files
    
    #getCapabilities
    try:
        # Open file.
        getCapabilities_base=open(lcdir+'/'+twmsEndPoint+'/getCapabilities.base', 'r+')
    except IOError:
        mssg=str().join(['Cannot read getCapabilities.base file:  ', 
                         lcdir+'/'+twmsEndPoint+'/getCapabilities.base'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        execbeef = 'EXECBEEF: Layer='+fileNamePrefix+' eval $LT'
        lines = getCapabilities_base.readlines()
        for idx in range(0, len(lines)):
            if execbeef in lines[idx]:
                # don't add another execbeef if it's already there
                print fileNamePrefix + ' already exists in getCapabilities'
                break
            if '  </Layer>' in lines[idx]: #careful with spaces here
                lines[idx-1] = '' # remove empty line
                lines[idx] = lines[idx].replace('  </Layer>',execbeef+'\n\n  </Layer>')
                print 'Injecting to getCapabilities ' + execbeef
            if 'OnlineResource' in lines[idx]:
                spaces = lines[idx].index('<')
                onlineResource = xml.dom.minidom.parseString(lines[idx]).getElementsByTagName('OnlineResource')[0]
                onlineResource.attributes['xlink:href'] = twmsServiceUrl
                lines[idx] = (' '*spaces) + onlineResource.toprettyxml(indent=" ")
        getCapabilities_base.seek(0)
        getCapabilities_base.truncate()
        getCapabilities_base.writelines(lines)
        getCapabilities_base.close()
    
    #getCapabilities WMTS modify Service URL
    try:
        # Open start base.
        getCapabilities_startbase=open(lcdir+'/'+wmtsEndPoint+'/getCapabilities_start.base', 'r+')
    except IOError:
        mssg=str().join(['Cannot read getCapabilities_start.base file:  ', 
                         lcdir+'/'+wmtsEndPoint+'/getCapabilities_start.base'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        lines = getCapabilities_startbase.readlines()
        for idx in range(0, len(lines)):
            if '<ows:Get' in lines[idx]:
                spaces = lines[idx].index('<')
                getUrlLine = lines[idx].replace('ows:Get','Get xmlns:xlink="http://www.w3.org/1999/xlink"').replace('>','/>')
                getUrl = xml.dom.minidom.parseString(getUrlLine).getElementsByTagName('Get')[0]
                if '1.0.0/WMTSCapabilities.xml' in lines[idx]:
                    getUrl.attributes['xlink:href'] = wmtsServiceUrl + '1.0.0/WMTSCapabilities.xml'
                elif 'wmts.cgi?' in lines[idx]:
                    getUrl.attributes['xlink:href'] = wmtsServiceUrl + 'wmts.cgi?'
                else:
                    getUrl.attributes['xlink:href'] = wmtsServiceUrl
                lines[idx] = (' '*spaces) + getUrl.toprettyxml(indent=" ").replace('Get','ows:Get').replace(' xmlns:xlink="http://www.w3.org/1999/xlink"','').replace('/>','>')
        getCapabilities_startbase.seek(0)
        getCapabilities_startbase.truncate()
        getCapabilities_startbase.writelines(lines)
        getCapabilities_startbase.close()
    try:
        # Open end base.
        getCapabilities_endbase=open(lcdir+'/'+wmtsEndPoint+'/getCapabilities_end.base', 'r+')
    except IOError:
        mssg=str().join(['Cannot read getCapabilities_end.base file:  ', 
                         lcdir+'/'+wmtsEndPoint+'/getCapabilities_end.base'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        lines = getCapabilities_endbase.readlines()
        for idx in range(0, len(lines)):
            if 'ServiceMetadataURL' in lines[idx]:
                spaces = lines[idx].index('<')
                serviceMetadataUrlLine = lines[idx].replace('ServiceMetadataURL','ServiceMetadataURL xmlns:xlink="http://www.w3.org/1999/xlink"')
                serviceMetadataUrl = xml.dom.minidom.parseString(serviceMetadataUrlLine).getElementsByTagName('ServiceMetadataURL')[0]
                serviceMetadataUrl.attributes['xlink:href'] = wmtsServiceUrl + '1.0.0/WMTSCapabilities.xml'
                lines[idx] = (' '*spaces) + serviceMetadataUrl.toprettyxml(indent=" ").replace(' xmlns:xlink="http://www.w3.org/1999/xlink"','')
        getCapabilities_endbase.seek(0)
        getCapabilities_endbase.truncate()
        getCapabilities_endbase.writelines(lines)
        getCapabilities_endbase.close()    

    #getTileService
    try:
        # Open file.
        getTileService_base=open(lcdir+'/'+twmsEndPoint+'/getTileService.base', 'r+')
    except IOError:
        mssg=str().join(['Cannot read getTileService.base file:  ', 
                         lcdir+'/'+twmsEndPoint+'/getTileService.base'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        execbeef = 'EXECBEEF: N="'+title+'" Name="$N tileset" Title="$N" LN='+mrf_base+' eval $TILED_GROUP'
        lines = getTileService_base.readlines()
        for idx in range(0, len(lines)):
            if execbeef in lines[idx]:
                # don't add another execbeef if it's already there
                print mrf_base + ' already exists in getTileService'
                break
            if '</TiledPatterns>' in lines[idx]:
                lines[idx-1] = '' # remove empty line
                lines[idx] = lines[idx].replace('</TiledPatterns>',execbeef+'\n\n</TiledPatterns>')
                print 'Injecting to getTileService ' + execbeef
            if 'OnlineResource' in lines[idx]:
                spaces = lines[idx].index('<')
                onlineResource = xml.dom.minidom.parseString(lines[idx]).getElementsByTagName('OnlineResource')[0]
                onlineResource.attributes['xlink:href'] = twmsServiceUrl
                lines[idx] = (' '*spaces) + onlineResource.toprettyxml(indent=" ")
        getTileService_base.seek(0)
        getTileService_base.truncate()
        getTileService_base.writelines(lines)
        getTileService_base.close()

    #wms_config
    try:
        # Open file.
        wms_config_base=open(lcdir+'/'+twmsEndPoint+'/wms_config.base', 'r+')
    except IOError:
        mssg=str().join(['Cannot read wms_config.base file:  ', 
                         lcdir+'/'+twmsEndPoint+'/wms_config.base'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        execbeef = 'EXECBEEF: N="'+title+'" Name="$N tileset" Title="$N" LN='+mrf_base+' eval $TILED_GROUP'
        lines = wms_config_base.readlines()
        for idx in range(0, len(lines)):
            if execbeef in lines[idx]:
                # don't add another execbeef if it's already there
                print mrf_base + ' already exists in wms_config'
                break
            if '  </LayerList>' in lines[idx]: #careful with spaces here
                lines[idx-1] = '' # remove empty line
                lines[idx] = lines[idx].replace('  </LayerList>',execbeef+'\n\n  </LayerList>')
                print 'Injecting to wms_config ' + execbeef
        wms_config_base.seek(0)
        wms_config_base.truncate()
        wms_config_base.writelines(lines)
        wms_config_base.close()
        
# configure Makefiles
    
    # set location of tools
    if os.path.isfile(os.path.abspath(lcdir)+'/bin/oe_create_cache_config'):
        depth = os.path.abspath(lcdir)+'/bin'
    elif distutils.spawn.find_executable('oe_create_cache_config') != None:
        depth = distutils.spawn.find_executable('oe_create_cache_config').split('/oe_create_cache_config')[0]
    else:
        depth = '/usr/bin' # default
    
    #twms
    try:
        # Open file.
        twms_make=open(lcdir+'/'+twmsEndPoint+'/Makefile', 'r+')
    except IOError:
        mssg=str().join(['Cannot read twms Makefile file:  ', 
                         lcdir+'/'+twmsEndPoint+'/Makefile'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        lines = twms_make.readlines()
        for idx in range(0, len(lines)):
            # replace lines in Makefiles
            if 'DEPTH=' in lines[idx]:
                lines[idx] = 'DEPTH=' + depth + '\n'
            if 'TGT_PATH=' in lines[idx]:
                lines[idx] = 'TGT_PATH=' + twms_endpoints[twmsEndPoint].getTileService + '\n'
            if fileNamePrefix in lines[idx]:
                # don't add the layer if it's already there
                print fileNamePrefix + ' already exists in twms Makefile'
                break
            if 'MRFS:=$' in lines[idx] and static == False:
                lines[idx-2] = '\nTYPES:=' + fileNamePrefix + ' $(TYPES)\n\n'
                print 'Adding to twms Makefile: ' + fileNamePrefix
            if 'TARGETS:=' in lines[idx] and static == True:
                lines[idx-2] = '\nMRFS:=' + fileNamePrefix + '.mrf $(MRFS)\n\n'
                print 'Adding to twms Makefile: ' + fileNamePrefix
        twms_make.seek(0)
        twms_make.truncate()
        twms_make.writelines(lines)
        twms_make.close()

    #wmts
    try:
        # Open file.
        wmts_make=open(lcdir+'/'+wmtsEndPoint+'/Makefile', 'r+')
    except IOError:
        mssg=str().join(['Cannot read wmts Makefile file:  ', 
                         lcdir+'/'+wmtsEndPoint+'/Makefile'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        lines = wmts_make.readlines()
        for idx in range(0, len(lines)):
            # replace lines in Makefiles
            if 'DEPTH=' in lines[idx]:
                lines[idx] = 'DEPTH=' + depth + '\n'
            if 'srcdir=' in lines[idx]:
                lines[idx] = 'srcdir=' + os.path.abspath(lcdir+'/'+twmsEndPoint) + '\n'
            if fileNamePrefix in lines[idx]:
                # don't add the layer if it's already there
                print fileNamePrefix + ' already exists in wmts Makefile'
                break
            if 'MRFS:=$' in lines[idx] and static == False:
                lines[idx-2] = '\nTYPES:=' + fileNamePrefix + ' $(TYPES)\n\n'
                print 'Adding to wmts Makefile: ' + fileNamePrefix
            if 'TARGETS:=' in lines[idx] and static == True:
                lines[idx-2] = '\nMRFS:=' + fileNamePrefix + '.mrf $(MRFS)\n\n'
                print 'Adding to wmts Makefile: ' + fileNamePrefix
        wmts_make.seek(0)
        wmts_make.truncate()
        wmts_make.writelines(lines)
        wmts_make.close()
        
# create WMTS layer metadata for GetCapabilities

    wmts_layer_output_name = lcdir+'/'+wmtsEndPoint+'/'+os.path.basename(mrf).replace('.mrf','.xml')
    wmts_layer_output = open(wmts_layer_output_name, 'w')
    print "\nCreating layer metadata file for GetCapabilities:", wmts_layer_output_name
    try:
        # Open files.
#         wmts_layer_template = open(lcdir+'/conf/wmts_layer.template', 'r')
        wmts_layer_template = projection.layer_template
    except IOError:
        mssg=str().join(['Cannot read wmts layer template file:  ', 
                         lcdir+'/conf/wmts_layer.template'])
        sent=sigevent('ERROR', mssg, sigevent_url)
        sys.exit(mssg)
    else:
        lines = wmts_layer_template.splitlines(True)
        for line in lines:
            # replace lines in template
            if '<Layer>' in line:
                line = '         '+line
            if '</Layer>' in line:
                line = ' '+line+'\n'                
            if '$Title' in line:
                line = line.replace("$Title",title)
            if '$Identifier' in line:
                line = line.replace("$Identifier",identifier)
            if '$ColorMap' in line:
                if colormap == None:
                    line = ''
                else:
                    line = line.replace("$ColorMap",str(colormap))
            if '$Format' in line:
                line = line.replace("$Format",mrf_format)
            if '$TileMatrixSet' in line:
                line = line.replace("$TileMatrixSet",projection.tilematrixsets[levels])
            if static == True or len(timeElements)==0:
                if any(x in line for x in ['Dimension', '<ows:Identifier>time</ows:Identifier>', '<UOM>ISO8601</UOM>', '$DefaultDate', '<Current>false</Current>', '$DateRange']):
                    line = ''
            else:
                if '$DefaultDate' in line:
                    defaultDate = ''
                    for timeElement in timeElements:
                        defaultDate = timeElement.firstChild.data.strip().split('/')[1]
                    line = line.replace("$DefaultDate",defaultDate)
                if '$DateRange' in line:
                    line = line.replace("$DateRange",timeElements[0].firstChild.data.strip())
                    iterTime = iter(timeElements)
                    next(iterTime)
                    for timeElement in iterTime:
                        line = line + "             " + timeElement.toxml().replace('Time','Value')+"\n"
            # remove extra white space from lines
            line = line[3:]
            wmts_layer_output.write(line)
        wmts_layer_output.close()
        
# run scripts

if no_twms == False:
    for key, twms_endpoint in twms_endpoints.iteritems():
        #twms
        print "\nRunning commands for endpoint: " + twms_endpoint.path
        cmd = 'make -C '+lcdir+'/'+twms_endpoint.path+'/ clean'
        run_command(cmd)
        cmd = 'make -C '+lcdir+'/'+twms_endpoint.path+'/ all'
        run_command(cmd)
        if no_cache == False:
            if twms_endpoint.cacheConfig:
                shutil.copy(lcdir+'/'+twms_endpoint.path+'/cache.config', twms_endpoint.cacheConfig)
                print '\nCopying: ' + lcdir+'/'+twms_endpoint.path+'/cache.config' + ' -> ' + twms_endpoint.cacheConfig
        if no_xml == False:
            if twms_endpoint.getCapabilities:
                shutil.copy(lcdir+'/'+twms_endpoint.path+'/getCapabilities.xml', twms_endpoint.getCapabilities)
                print '\nCopying: ' + lcdir+'/'+twms_endpoint.path+'/getCapabilities.xml' + ' -> ' + twms_endpoint.getCapabilities
            if twms_endpoint.getTileService:
                shutil.copy(lcdir+'/'+twms_endpoint.path+'/getTileService.xml', twms_endpoint.getTileService)
                print '\nCopying: ' + lcdir+'/'+twms_endpoint.path+'/getTileService.xml' + ' -> ' + twms_endpoint.getTileService

if no_wmts == False:
    for key, wmts_endpoint in wmts_endpoints.iteritems():
        #wmts
        print "\nRunning commands for endpoint: " + wmts_endpoint.path
        cmd = 'make -C '+lcdir+'/'+wmts_endpoint.path+'/ clean'
        run_command(cmd)
        cmd = 'make -C '+lcdir+'/'+wmts_endpoint.path+'/ all'
        run_command(cmd)
        if no_cache == False:
            if wmts_endpoint.cacheConfig:
                shutil.copy(lcdir+'/'+wmts_endpoint.path+'/cache_wmts.config', wmts_endpoint.cacheConfig)
                print '\nCopying: ' + lcdir+'/'+wmts_endpoint.path+'/cache_wmts.config' + ' -> ' + wmts_endpoint.cacheConfig
        if no_xml == False:
            cmd = 'cat '+lcdir+'/'+wmts_endpoint.path+'/getCapabilities_start.base '+lcdir+'/'+wmts_endpoint.path+'/*.xml '+lcdir+'/'+wmts_endpoint.path+'/getCapabilities_end.base > '+lcdir+'/'+wmts_endpoint.path+'/getCapabilities.xml'
            run_command(cmd)
            if wmts_endpoint.getCapabilities:
                shutil.copy(lcdir+'/'+wmts_endpoint.path+'/getCapabilities.xml', wmts_endpoint.getCapabilities)
                print '\nCopying: ' + lcdir+'/'+wmts_endpoint.path+'/getCapabilities.xml' + ' -> ' + wmts_endpoint.getCapabilities
                if not os.path.exists(wmts_endpoint.getCapabilities +'1.0.0/'):
                    os.makedirs(wmts_endpoint.getCapabilities +'1.0.0')
                shutil.copy(lcdir+'/'+wmts_endpoint.path+'/getCapabilities.xml', wmts_endpoint.getCapabilities + '/1.0.0/WMTSCapabilities.xml')
                print '\nCopying: ' + lcdir+'/'+wmts_endpoint.path+'/getCapabilities.xml' + ' -> ' + wmts_endpoint.getCapabilities + '/1.0.0/WMTSCapabilities.xml'

print '\n*** Layers have been configured successfully ***'
if no_cache == False:
    print '\nThe Apache server must be restarted to reload the cache configurations\n'

if restart==True:
    cmd = 'sudo apachectl stop'
    run_command(cmd)
    cmd = 'sleep 3'
    run_command(cmd)
    cmd = 'sudo apachectl start'
    run_command(cmd)
    print '\nThe Apache server was restarted successfully'
    
message = "The OnEarth Layer Configurator completed successully. " + ("Cache created.", "No cache.")[no_cache] + " " + ("XML created","No XML")[no_xml] + "."
log_sig_exit('INFO', message, sigevent_url)
    