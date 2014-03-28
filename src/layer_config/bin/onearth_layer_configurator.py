#!/bin/env python

# Copyright (c) 2002-2013, California Institute of Technology.
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
# onearth_layer_configurator.py
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
 <HeaderFileName>MYR6CTTLLNITTTTTTT_.mrf</HeaderFileName>
 <DataFileLocation>MYR6CTTLLNI/YYYY/MYR6CTTLLNITTTTTTT_.ppg</DataFileLocation>
 <IndexFileLocation>MYR6CTTLLNI/YYYY/MYR6CTTLLNITTTTTTT_.idx</IndexFileLocation>
 <Compression>PNG</Compression>
 <Levels>6</Levels>
 <EmptyTileSize offset="0">1397</EmptyTileSize>
 <Projection><![CDATA[GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]]]></Projection> 
 <Pattern><![CDATA[request=GetMap&layers=MODIS_Aqua_Cloud_Top_Temp_Night&srs=EPSG:4326&format=image/png&styles=&time=[-0-9]*&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <Pattern><![CDATA[request=GetMap&layers=MODIS_Aqua_Cloud_Top_Temp_Night&srs=EPSG:4326&format=image/png&styles=&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <Pattern><![CDATA[LAYERS=MODIS_Aqua_Cloud_Top_Temp_Night&FORMAT=image%2Fpng&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&SRS=EPSG%3A4326&BBOX=[-,\.0-9+Ee]*&WIDTH=512&HEIGHT=512]]></Pattern>
 <Pattern><![CDATA[service=WMS&request=GetMap&version=1.1.1&srs=EPSG:4326&layers=MODIS_Aqua_Cloud_Top_Temp_Night&styles=default&transparent=TRUE&format=image/png&width=512&height=512&bbox=[-,\.0-9+Ee]*]]></Pattern>
 <StartDate>2013-11-04</StartDate>
 <EndDate>2013-11-04</EndDate>
 <WMTSEndPoint>wmts-geo</WMTSEndPoint>
 <TWMSEndPoint>twms-geo</TWMSEndPoint>
 <ColorMap>http://map1.vis.earthdata.nasa.gov/colormap/sample.xml</ColorMap>
</LayerConfiguration>
'''
#
# Global Imagery Browse Services
# NASA Jet Propulsion Laboratory
# 2014
# Joe.T.Roberts@jpl.nasa.gov

import os
import subprocess
import sys
import time
import datetime
import socket
import urllib
import urllib2
import xml.dom.minidom
import string
import shutil
import glob
import logging
from optparse import OptionParser

versionNumber = '0.3'

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
    print str().join(['sigevent', type, mssg])
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
    data['source']='OnEarth'
    data['format']='TEXT'
    data['category']='UNCATEGORIZED'
    data['provider']='Global Imagery Browse Services'
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
    print time.asctime()
    logging.info(time.asctime())
    log_info_mssg(mssg)

def log_sig_warn(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(time.asctime())
    logging.warning(mssg)
    # Send to sigevent.
    sent=sigevent('WARN', mssg, sigevent_url)

def log_sig_exit(type, mssg, sigevent_url):
    """
    Send a message to the log, to sigevent, and then exit.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Add "Exiting" to mssg.
    mssg=str().join([mssg, '  Exiting.'])
    # Send to log.
    if type == 'INFO':
        log_info_mssg_with_timestamp(mssg)
    elif type == 'WARN':
        logging.warning(time.asctime())
        logging.warning(mssg)
    elif type == 'ERROR':
        logging.error(time.asctime())
        logging.error(mssg)
    # Send to sigevent.
    sent=sigevent(type, mssg, sigevent_url)
    # Exit.
    sys.exit(mssg)

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
        raise Exception(error.strip())
    
 #-------------------------------------------------------------------------------   

print 'OnEarth Layer Configurator v' + versionNumber

if os.environ.has_key('LCDIR') == False:
    print 'LCDIR environment variable not set.\nLCDIR should point to your OnEarth layer_config directory.\n'
    lcdir = os.path.dirname(__file__) + '/..'
else:
    lcdir = os.environ['LCDIR']

usageText = 'onearth_layer_config.py --conf_file [layer_configuration_file.xml] --conf_dir [$LCDIR/conf/] --headers [$LCDIR/headers/] --mrf [MRF archetype] --onearth [OnEarth DocRoot] --sigevent_url [url]'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-c', '--conf_file',
                  action='store', type='string', dest='configuration_filename',
                  help='Full path of configuration filename.')
parser.add_option('-d', '--conf_dir',
                  action='store', type='string', dest='configuration_directory',
                  default=lcdir+'/conf/',
                  help='Full path of directory containing configuration files.  Default: $LCDIR/conf/')
parser.add_option('-e', '--headers',
                  action='store', type='string', dest='headers',
                  default=lcdir+'/headers/',
                  help='Full path of directory containing MRF headers.  Default: $LCDIR/headers/')
parser.add_option('-m', '--mrf',
                  action='store', type='string', dest='mrf',
                  help='Full path of archetype MRF file.')
parser.add_option("-n", "--no_restart",
                  action="store_true", dest="no_restart", 
                  default=False, help="Do not restart the Apache server on completion.")
parser.add_option('-o', '--onearth',
                  action='store', type='string', dest='onearth',
                  help='Full path of the Apache document root for OnEarth if getCapabilities and cache config locations not specified.  Default: $ONEARTH')
parser.add_option('-s', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')

# Read command line args.
(options, args) = parser.parse_args()
# Configuration filename.
configuration_filename = options.configuration_filename
# Configuration directory.
configuration_directory = options.configuration_directory
# Archetype headers
headers = options.headers
# Sigevent URL.
sigevent_url = options.sigevent_url

if options.onearth:
    onearth = options.onearth
if os.environ.has_key('ONEARTH'):
    onearth = os.environ['ONEARTH']
else:
    onearth = None
#     print 'ONEARTH environment variable not set.\nONEARTH should point to your Apache document root for OnEarth.\n'
#     if not options.onearth:
#         parser.error('--onearth must be specified if the $ONEARTH environment variable is not set.')

if not options.mrf and not options.headers:   # if filename is not given
    parser.error('MRF file or directory not given. --mrf or --headers must be specified.')

if onearth:
    print 'Using ' + onearth + ' as $ONEARTH.'    
print 'Using ' + lcdir + ' as $LCDIR.'

# Read XML configuration files.

conf_files = []
wmts_endpoints = []
twms_endpoints = []

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
    sys.exit('No configuration files found.')
    
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
        identifier = get_dom_tag_value(dom, 'Identifier')
        title = get_dom_tag_value(dom, 'Title')
        fileNamePrefix = get_dom_tag_value(dom, 'FileNamePrefix')
        headerFileName = get_dom_tag_value(dom, 'HeaderFileName')
        dataFileLocation = get_dom_tag_value(dom, 'DataFileLocation')
        indexFileLocation = get_dom_tag_value(dom, 'IndexFileLocation')
        compression = get_dom_tag_value(dom, 'Compression')
        levels = get_dom_tag_value(dom, 'Levels')
        emptyTileSize = int(get_dom_tag_value(dom, 'EmptyTileSize'))

        # Optional parameters
        try:
            projection = get_dom_tag_value(dom, 'Projection')
        except IndexError:
            projection = None 
        try:
            epsg = dom.getElementsByTagName('Projection')[0].attributes['epsg'].value
        except:
            epsg = None
        try:
            emptyTileOffset = dom.getElementsByTagName('EmptyTileSize')[0].attributes['offset'].value
        except:
            emptyTileOffset = 0
        try:
            startDate = get_dom_tag_value(dom, 'StartDate')
            endDate = get_dom_tag_value(dom, 'EndDate')
        except IndexError:
            startDate = None
            endDate = None
        try:
            colormap = get_dom_tag_value(dom, 'ColorMap')
        except IndexError:
            colormap = None
            
        # Patterns
        patterns = []
        patternTags = dom.getElementsByTagName('Pattern')
        for pattern in patternTags:
            patterns.append(pattern.firstChild.data.strip())
            
        # Services
        try:
            getTileService = get_dom_tag_value(dom, 'GetTileServiceLocation')
        except IndexError:
            getTileService = None
        
        getCapabilitiesElements = dom.getElementsByTagName('GetCapabilitiesLocation')
        wmts_getCapabilities = None
        twms_getCapabilities = None
        for getCapabilities in getCapabilitiesElements:
            if str(getCapabilities.attributes['service'].value).lower() == "wmts":
                wmts_getCapabilities = getCapabilities.firstChild.nodeValue.strip()
            elif str(getCapabilities.attributes['service'].value).lower() == "twms":
                twms_getCapabilities = getCapabilities.firstChild.nodeValue.strip()
                
        cacheConfigElements = dom.getElementsByTagName('CacheConfigLocation')
        wmts_cacheConfig = None
        twms_cacheConfig = None
        for cacheConfig in cacheConfigElements:
            if str(cacheConfig.attributes['service'].value).lower() == "wmts":
                wmts_cacheConfig = cacheConfig.firstChild.nodeValue.strip()
            elif str(cacheConfig.attributes['service'].value).lower() == "twms":
                twms_cacheConfig = cacheConfig.firstChild.nodeValue.strip()
        
        # Set end points
        try:
            wmtsEndPoint = get_dom_tag_value(dom, 'WMTSEndPoint')
        except IndexError:
            wmtsEndPoint = 'wmts/EPSG' + epsg
        try:
            twmsEndPoint = get_dom_tag_value(dom, 'TWMSEndPoint')
        except IndexError:
            twmsEndPoint = 'twms/EPSG' + epsg
        
        wmts_endpoints.append(wmtsEndPoint)
        twms_endpoints.append(twmsEndPoint)
        
        # Close file.
        config_file.close()
        
    if options.mrf:
        mrf = options.mrf
    else:
        mrf = headers + headerFileName
    
    log_info_mssg('MRF: ' + mrf)    
    log_info_mssg('config: Identifier: ' + identifier)
    log_info_mssg('config: Title: ' + title)
    log_info_mssg('config: FileNamePrefix: ' + fileNamePrefix)
    log_info_mssg('config: HeaderFileName: ' + headerFileName)
    log_info_mssg('config: DataFileLocation: ' + dataFileLocation)
    log_info_mssg('config: IndexFileLocation: ' + indexFileLocation)
    log_info_mssg('config: Compression: ' + compression)
    log_info_mssg('config: Levels: ' + levels)
    log_info_mssg('config: EmptyTileSize: ' + str(emptyTileSize))
    log_info_mssg('config: EmptyTileOffset: ' + str(emptyTileOffset))
    if projection:
        log_info_mssg('config: Projection: ' + str(projection))
    if startDate:
        log_info_mssg('config: StartDate: ' + str(startDate))
    if endDate:
        log_info_mssg('config: EndDate: ' + str(endDate))
    if getTileService:
        log_info_mssg('config: GetTileServiceLocation: ' + str(getTileService))
    if wmts_getCapabilities:
        log_info_mssg('config: WMTS GetCapabilitiesLocation: ' + str(wmts_getCapabilities))
    if twms_getCapabilities:
        log_info_mssg('config: TWMS GetCapabilitiesLocation: ' + str(twms_getCapabilities))
    if wmts_cacheConfig:
        log_info_mssg('config: WMTS CacheConfigLocation: ' + str(wmts_cacheConfig))
    if twms_cacheConfig:
        log_info_mssg('config: TWMS CacheConfigLocation: ' + str(twms_cacheConfig))
    if wmtsEndPoint:
        log_info_mssg('config: WMTSEndPoint: ' + str(wmtsEndPoint))
    if twmsEndPoint:
        log_info_mssg('config: TWMSEndPoint: ' + str(twmsEndPoint))
    if colormap:
        log_info_mssg('config: ColorMap: ' + str(colormap))
    log_info_mssg('config: Patterns: ' + str(patterns))
    
    # Modify MRF Archetype
    try:
        # Open file.
        mrf_file=open(mrf, 'r')
    except IOError:
        mssg=str().join(['Cannot read MRF header file:  ', 
                         mrf])
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
    
    if startDate:
        startDateElement = mrf_dom.createElement('StartDate')
        startDateElement.appendChild(mrf_dom.createTextNode(startDate))
        twms.appendChild(twms.appendChild(startDateElement))

    if endDate:
        endDateElement = mrf_dom.createElement('EndDate')
        endDateElement.appendChild(mrf_dom.createTextNode(endDate))
        twms.appendChild(twms.appendChild(endDateElement))

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
    
    mrf_meta.appendChild(twms)
        
    if projection:
        projectionElement = mrf_dom.createElement('Projection')
        projectionElement.appendChild(mrf_dom.createCDATASection(projection))
        mrf_meta.appendChild(projectionElement)
    
    new_mrf_file = open(lcdir+'/'+twmsEndPoint+'/'+headerFileName,'w+')
    mrf_dom.writexml(new_mrf_file)
    
    new_mrf_file.seek(0)
    lines = new_mrf_file.readlines()
    lines[0] = '<MRF_META>\n'
    lines[-1] = lines[-1].replace('<TWMS>','<TWMS>\n\t').replace('</Levels>','</Levels>\n\t').replace('<Pattern>','\n\t<Pattern>'). \
        replace('<StartDate>','\n\t<StartDate>').replace('<EndDate>','\n\t<EndDate>').replace('<Metadata>','\n\t<Metadata>').replace('</TWMS>','\n</TWMS>\n'). \
        replace('</MRF_META>','\n</MRF_META>\n') #get_mrfs is picky about line breaks
    
    new_mrf_file.seek(0)
    new_mrf_file.truncate()
    new_mrf_file.writelines(lines)
    
    new_mrf_file.close()
    mrf_file.close()
    
    print '\n'+lcdir+'/'+twmsEndPoint+'/'+headerFileName + ' configured successfully\n'


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
        getCapabilities_base.seek(0)
        getCapabilities_base.truncate()
        getCapabilities_base.writelines(lines)
        getCapabilities_base.close()

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
        execbeef = 'EXECBEEF: N="'+title+'" Name="$N tileset" Title="$N" LN='+headerFileName+' eval $TILED_GROUP'
        lines = getTileService_base.readlines()
        for idx in range(0, len(lines)):
            if execbeef in lines[idx]:
                # don't add another execbeef if it's already there
                print headerFileName + ' already exists in getTileService'
                break
            if '</TiledPatterns>' in lines[idx]:
                lines[idx-1] = '' # remove empty line
                lines[idx] = lines[idx].replace('</TiledPatterns>',execbeef+'\n\n</TiledPatterns>')
                print 'Injecting to getTileService ' + execbeef
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
        execbeef = 'EXECBEEF: N="'+title+'" Name="$N tileset" Title="$N" LN='+headerFileName+' eval $TILED_GROUP'
        lines = wms_config_base.readlines()
        for idx in range(0, len(lines)):
            if execbeef in lines[idx]:
                # don't add another execbeef if it's already there
                print headerFileName + ' already exists in wms_config'
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
            if fileNamePrefix in lines[idx]:
                # don't add the layer if it's already there
                print fileNamePrefix + ' already exists in twms Makefile'
                break
            if 'MRFS:=' in lines[idx]:
                lines[idx-2] = '\nTYPES:=' + fileNamePrefix + ' $(TYPES)\n\n'
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
            if fileNamePrefix in lines[idx]:
                # don't add the layer if it's already there
                print fileNamePrefix + ' already exists in wmts Makefile'
                break
            if 'MRFS:=' in lines[idx]:
                lines[idx-2] = '\nTYPES:=' + fileNamePrefix + ' $(TYPES)\n\n'
                print 'Adding to wmts Makefile: ' + fileNamePrefix
        wmts_make.seek(0)
        wmts_make.truncate()
        wmts_make.writelines(lines)
        wmts_make.close()
        
# run scripts

for twms_endpoint in set(twms_endpoints):
    #twms
    print "\nRunning commands for endpoint: " + twms_endpoint
    cmd = 'make -C '+lcdir+'/'+twms_endpoint+'/ clean'
    run_command(cmd)
    cmd = 'make -C '+lcdir+'/'+twms_endpoint+'/ all'
    run_command(cmd)
    if twms_cacheConfig:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/cache.config ' + twms_cacheConfig
    elif onearth:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/cache.config '+onearth+'/'+twms_endpoint+'/'
    run_command(cmd)
    if twms_getCapabilities:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/getCapabilities.xml ' + twms_getCapabilities
    elif onearth:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/getCapabilities.xml '+onearth+'/'+twms_endpoint+'/.lib/'
    run_command(cmd)
    if getTileService:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/getTileService.xml ' + getTileService
    elif onearth:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/getTileService.xml '+onearth+'/'+twms_endpoint+'/.lib/'
    run_command(cmd)
    if onearth:
        cmd = 'cp -p -v '+lcdir+'/'+twms_endpoint+'/wms_config.xml '+onearth+'/'+twms_endpoint+'/.lib/'
        run_command(cmd)

for wmts_endpoint in set(wmts_endpoints):
    #wmts
    print "\nRunning commands for endpoint: " + wmts_endpoint
    cmd = 'make -C '+lcdir+'/'+wmts_endpoint+'/ clean'
    run_command(cmd)
    cmd = 'make -C '+lcdir+'/'+wmts_endpoint+'/ all'
    run_command(cmd)
    if wmts_cacheConfig:
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/cache_wmts.config ' + wmts_cacheConfig
    elif onearth:
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/cache_wmts.config '+onearth+'/'+wmts_endpoint+'/'
    run_command(cmd)
    cmd = lcdir+'/bin/get_GC_xml.sh '+lcdir+'/'+wmts_endpoint+'/'
    run_command(cmd)
    cmd = 'mv -v *_.xml '+lcdir+'/'+wmts_endpoint+'/'
    run_command(cmd)
    cmd = 'cat '+lcdir+'/'+wmts_endpoint+'/getCapabilities_start.base '+lcdir+'/'+wmts_endpoint+'/*.xml '+lcdir+'/'+wmts_endpoint+'/getCapabilities_end.base > '+lcdir+'/'+wmts_endpoint+'/getCapabilities.xml'
    run_command(cmd)
    if wmts_getCapabilities:
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/getCapabilities.xml ' + wmts_getCapabilities
        run_command(cmd)
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/getCapabilities.xml '+ wmts_getCapabilities +'/1.0.0/WMTSCapabilities.xml'
        run_command(cmd)
    elif onearth:
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/getCapabilities.xml '+onearth+'/'+wmts_endpoint+'/'
        run_command(cmd)
        cmd = 'cp -p -v '+lcdir+'/'+wmts_endpoint+'/getCapabilities.xml '+onearth+'/'+wmts_endpoint+'/1.0.0/WMTSCapabilities.xml'
        run_command(cmd)

print '\n*** Layers have been configured successfully ***'
print '\nThe Apache server must be restarted'

if options.no_restart==False:
    cmd = 'sudo apachectl stop'
    run_command(cmd)
    cmd = 'sleep 3'
    run_command(cmd)
    cmd = 'sudo apachectl start'
    run_command(cmd)
    print '\nThe Apache server was restarted successfully'
    