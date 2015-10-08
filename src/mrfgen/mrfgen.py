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
# Pipeline for converting georeferenced tiles to MRF for Tiled-WMS.
#
# Example:
#
#  mrfgen.py 
#   -c mrfgen_configuration_file.xml 
#   -s http://localhost:8100/sigevent/events/create
#
# Example XML configuration file:
#
# <?xml version="1.0" encoding="UTF-8"?>
# <mrfgen_configuration>
#  <date_of_data>20140606</date_of_data>
#  <parameter_name>MORCR143LLDY</parameter_name>
#  <input_dir>/mrfgen/input_dir</input_dir> 
#  <output_dir>/mrfgen/output_dir</output_dir>
#  <cache_dir>/mrfgen/cache_dir</cache_dir>
#  <working_dir>/mrfgen/working_dir</working_dir>
#  <logfile_dir>/mrfgen/working_dir</logfile_dir>
#  <empty_tile>black</empty_tile>
#  <mrf_blocksize>512</mrf_blocksize>
#  <mrf_compression_type>JPEG</mrf_compression_type>
#  <outsize>327680 163840</outsize>
#  <overview_levels>2 4 8 16 32 64 128 256 512 1024</overview_levels>
#  <overview_resampling>nearest</overview_resampling>
#  <epsg>4326</epsg>
#  <extents>-180,-90,180,90</extents>
#  <mrf_name>{$parameter_name}%Y%j_.mrf</mrf_name>
#  <colormap></colormap>
# </mrfgen_configuration>
#
# Global Imagery Browse Services / Physical Oceanography Distributed Active Archive Center (PO.DAAC)
# NASA Jet Propulsion Laboratory
# 2015
# Jeffrey.R.Hall@jpl.nasa.gov
# Joe.T.Roberts@jpl.nasa.gov


#COMMENTS IN ALL CAPS INDICATES UNFINISHED OR NEEDS MORE CONSIDERATOIN.

from optparse import OptionParser
import glob
import logging
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
import imghdr
import sqlite3

versionNumber = '0.8.0'

#-------------------------------------------------------------------------------
# Begin defining subroutines.
# CONSIDER BREAKING OUT SUBROUTINES TO SEPARATE FILES.
#-------------------------------------------------------------------------------

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
    data['category']='MRFGEN'
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
    exit_code = 0
    # Add "Exiting" to mssg.
    mssg=str().join([mssg, '  Exiting mrfgen.'])
    # Send to sigevent.
    try:
        sent=sigevent(type, mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'
    # Send to log.
    if type == 'INFO':
        log_info_mssg_with_timestamp(mssg)
    elif type == 'WARN':
        logging.warning(time.asctime())
        logging.warning(mssg)
    elif type == 'ERROR':
        logging.error(time.asctime())
        logging.error(mssg)
        exit_code = 1
    # Exit.
    sys.exit(exit_code)

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

def get_modification_time(filename):
    """
    Return (fake) floating point value of posix modification time for a file.
    The (fake) floating point value is yyyymmdd.hhmmss which may be treated 
    as a floating point number for the sake of time ordering.
    Arguments:
        filename -- name of file for which to return the modificaton time
    """
    # Get posix system time for mrf file to check the modification time.
    stats=os.stat(filename)
    # Convert st_mtime to time string "yyyymmdd.hhmmss".
    addt=time.strftime('%Y%m%d.%H%M%S', time.localtime(stats.st_mtime))
    mssg=str().join(['modification time ', addt, ' ', filename])
    # Send to log.
    log_info_mssg(mssg)
    # Return time as string.
    return addt

def get_dom_tag_value(dom, tag_name):
    """
    Return value of a tag from dom (XML file).
    Arguments:
        tag_name -- name of dom tag for which the value should be returned.
    """
    tag=dom.getElementsByTagName(tag_name)
    value=tag[0].firstChild.data.strip()
    return value

def get_input_files(dom):
    """
    Returns comma-separated list of files from <input_files> element.
    Arguments:
        dom -- The XML dom in which to retrieve <input_files> element.
    """
    files = []
    input_file_element = dom.getElementsByTagName("input_files")[0]
    file_elements = input_file_element.getElementsByTagName("file")
    if len(file_elements) > 0:
        for element in file_elements:
            files.append(element.firstChild.data.strip())
    else:
        files.append(input_file_element.firstChild.data.strip()) 
    return ",".join(files)

def remove_file(filename):
    """
    Delete a file or link, and report this action to the log.
    Arguments:
        filename -- file to remove.
    """
    #preexisting=glob.glob(str().join([input_dir, filename]))
    preexisting=glob.glob(filename)
    if len(preexisting) > 0:
        # Send to log.
        if os.path.islink(filename):
            log_info_mssg(str().join(['Removing link:  ', filename]))
        else:
            log_info_mssg(str().join(['Removing file:  ', filename]))
        os.remove(filename)
    #THE "CORRECT" TECHNIQUE:
    #dirname = '/some/path/'
    #filename = 'somefile.txt'
    #pathname = os.path.abspath(os.path.join(dirname, filename))
    #if pathname.startswith(dirname):
    #   os.remove(pathname)
    #Normalizing the path with abspath and comparing it against the target 
    #directory avoids file names like "../../../etc/passwd" or similar.

def check_abs_path(directory_path):
    """
    Check if directory is absolute path.
    If not, prepend current working directory.
        Argument:
            directory_path -- path to check if absolute
    """
    if directory_path[0] != '/':
        directory_path = os.getcwd() +'/' + directory_path
    
    return directory_path
    

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

def verify_directory_path_exists(directory_path, variable_name):
    """
    Verify that directory_path exists.
    Argument:
        directory_path -- path whose existence needs to be verified.
    """
    if not os.path.isdir(directory_path):
        mssg=str().join([variable_name, ' ', directory_path, 
                         ' does not exist.'])
        log_sig_exit('ERROR', mssg, sigevent_url)

def get_doy_string(date_of_data):
    """
    Convert date_of_data string into three-digit doy string.
    Argument:
        date_of_data -- string variable, example: 20120730
    """
    y=int(date_of_data[0:4])
    m=int(date_of_data[4:6])
    d=int(date_of_data[6:8])
    doy=str(datetime.datetime(y, m, d).timetuple().tm_yday)
    if int(doy) < 10:
        doy=str().join(['00', str(int(doy))])
    elif int(doy) < 100:
        doy=str().join(['0', str(int(doy))])
    return doy

def lookupEmptyTile(empty_tile):
    """
    Lookup predefined empty tiles form config file
    """
    script_dir = os.path.dirname(__file__)
    if script_dir == '/usr/bin':
        script_dir = '/usr/share/onearth/mrfgen' # use default directory if in bin
    try:
        empty_config_file=open(script_dir+"/empty_config", 'r')
    except IOError:
        log_sig_exit('ERROR', script_dir+"/empty_config could not be found", sigevent_url)
    tiles = {}
    for line in empty_config_file:
        (key, val) = line.split()
        tiles[key] = val
    empty_config_file.close()
    try:
        if tiles[empty_tile][0] == '/':   
            return os.path.abspath(tiles[empty_tile])
        else:
            return os.path.abspath(script_dir+"/"+tiles[empty_tile])
    except KeyError:
        mssg = '"' + empty_tile + '" is not a valid empty tile.'
        log_sig_exit('ERROR', mssg, sigevent_url)
        
def get_mrf_names(mrf_data, mrf_name, parameter_name, date_of_data, time_of_data):
    """
    Convert MRF filenames to specified naming convention (mrf_name).
    Argument:
        mrf_data -- the created MRF data file
        mrf_name -- the MRF naming convention to use
        parameter_name -- MRF parameter name
        date_of_data -- the date of the MRF data, example: 20120730
        time_of_data -- the time of subdaily MRF data in UTC, 113019 (11:30:19am)
    """
    if len(time_of_data) == 6:
        mrf_date = datetime.datetime.strptime(str(date_of_data)+str(time_of_data),"%Y%m%d%H%M%S")
    else: 
        mrf_date = datetime.datetime.strptime(date_of_data,"%Y%m%d")
    mrf = mrf_name.replace('{$parameter_name}', parameter_name)
    time_params = []
    for i, char in enumerate(mrf):
        if char == '%':
            time_params.append(char+mrf[i+1])
    for time_param in time_params:
        mrf = mrf.replace(time_param,datetime.datetime.strftime(mrf_date,time_param))
    index = mrf.replace('.mrf', '.idx')
    data = mrf.replace('.mrf', os.path.basename(mrf_data)[-4:])
    aux = mrf + '.aux.xml'
    vrt = mrf.replace('.mrf', '.vrt')
    return (mrf, index, data, aux, vrt)

def diff_resolution(tiles):
    if len(tiles) <= 1:
        print "Single tile detected"
        return False
    
    print "Checking for different resolutions in tiles"
    res = ""
    for tile in tiles:
        gdalinfo_command_list=['gdalinfo', tile]
        gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for line in gdalinfo.stdout.readlines():
            if "Pixel Size =" in line:
                if res == "":
                    res = line.split("=")[1].strip()
                    print "Input tile pixel size is: " + res
                else:
                    if line.split("=")[1].strip() != res:
                        print "Different tile resolutions detected"
                        return True              
    return False

#-------------------------------------------------------------------------------
# Finished defining subroutines.  Begin main program.
#-------------------------------------------------------------------------------

# Define command line options and args.
parser=OptionParser(version=versionNumber)
parser.add_option('-c', '--configuration_filename',
                  action='store', type='string', dest='configuration_filename',
                  default='./mrfgen_configuration_file.xml',
                  help='Full path of configuration filename.  Default:  ./mrfgen_configuration_file.xml')
parser.add_option("-d", "--data_only", action="store_true", dest="data_only", 
                  default=False, help="Only output the MRF data, index, and header files")
parser.add_option('-s', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')

# Read command line args.
(options, args) = parser.parse_args()
# Configuration filename.
configuration_filename=options.configuration_filename
# Sigevent URL.
sigevent_url=options.sigevent_url
# Data only.
data_only = options.data_only

# Read XML configuration file.
try:
    # Open file.
    config_file=open(configuration_filename, 'r')
except IOError:
    mssg=str().join(['Cannot read configuration file:  ', 
                     configuration_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
else:
    # Get dom from XML file.
    dom=xml.dom.minidom.parse(config_file)
    # Parameter name.
    parameter_name         =get_dom_tag_value(dom, 'parameter_name')
    date_of_data           =get_dom_tag_value(dom, 'date_of_data')
    # for sub-daily imagery
    try: 
        time_of_data = get_dom_tag_value(dom, 'time_of_data')
    except:
        time_of_data = ''
    # Directories.
    try:
        input_dir = get_dom_tag_value(dom, 'input_dir')
    except: 
        input_dir = None
    output_dir             =get_dom_tag_value(dom, 'output_dir')
    try:
        working_dir            =get_dom_tag_value(dom, 'working_dir')
    except: # use /tmp/ as default
        working_dir            ='/tmp/'
    try:
        logfile_dir            =get_dom_tag_value(dom, 'logfile_dir')
    except: #use working_dir if not specified
        logfile_dir            =working_dir
    try:
        mrf_name=get_dom_tag_value(dom, 'mrf_name')
    except:
        # default to GIBS naming convention
        mrf_name='{$parameter_name}%Y%j_.mrf'
    # MRF specific parameters.
    try:
        mrf_empty_tile_filename=check_abs_path(get_dom_tag_value(dom, 'mrf_empty_tile_filename'))
    except:
        try:
            mrf_empty_tile_filename=lookupEmptyTile(get_dom_tag_value(dom, 'empty_tile'))
        except:
            log_sig_warn("Empty tile was not found for " + parameter_name, sigevent_url)
            mrf_empty_tile_filename = ''
    try:
        vrtnodata = get_dom_tag_value(dom, 'vrtnodata')
    except:
        vrtnodata = ""
    mrf_blocksize          =get_dom_tag_value(dom, 'mrf_blocksize')
    mrf_compression_type   =get_dom_tag_value(dom, 'mrf_compression_type')
    try:
        outsize = get_dom_tag_value(dom, 'outsize')
        target_x, target_y = outsize.split(' ')
    except:
        outsize = ''
        try:
            target_x               =get_dom_tag_value(dom, 'target_x')
        except:
            target_x = '' # if no target_x then use rasterXSize and rasterYSize from VRT file
        try:
            target_y               =get_dom_tag_value(dom, 'target_y')
        except:
            target_y = ''
    # EPSG code projection.
    try:
        target_epsg        = 'EPSG:' + str(get_dom_tag_value(dom, 'target_epsg'))
    except:
        target_epsg = 'EPSG:4326' # default to geographic
    try:
        source_epsg        = 'EPSG:' + str(get_dom_tag_value(dom, 'source_epsg'))
    except:
        source_epsg = 'EPSG:4326' # default to geographic
    # Target extents.
    try:
        extents        =get_dom_tag_value(dom, 'extents')
    except:
        extents = '-180,-90,180,90' # default to geographic
    xmin, ymin, xmax, ymax = extents.split(',')
    try:
        target_extents        =get_dom_tag_value(dom, 'target_extents')
    except:
        if target_epsg == 'EPSG:3857':
            target_extents = '-20037508.34,-20037508.34,20037508.34,20037508.34'
        else:
            target_extents = extents # default to extents
    target_xmin, target_ymin, target_xmax, target_ymax = target_extents.split(',')
    # Input files.
    try:
        input_files = get_input_files(dom)
    except:
        if input_dir == None:
            log_sig_exit('ERROR', "<input_files> or <input_dir> is required", sigevent_url)
        else:
            input_files = ''
    # overview levels
    try:
        overview_levels       =get_dom_tag_value(dom, 'overview_levels').split(' ')
        for level in overview_levels:
            if level.isdigit() == False:
                log_sig_exit("ERROR", "'" + level + "' is not a valid overview value.", sigevent_url)
    except:
        overview_levels = ''
    # resampling method
    try:
        overview_resampling        =get_dom_tag_value(dom, 'overview_resampling')
    except:
        overview_resampling = 'nearest'    
    # gdalwarp resampling method for resizing
    try:
        resize_resampling        =get_dom_tag_value(dom, 'resize_resampling')
        if resize_resampling == "none":
            resize_resampling = ''
    except:
        resize_resampling = ''
    if resize_resampling != '' and target_x == '':
        log_sig_exit('ERROR', "target_x or outsize must be provided for resizing", sigevent_url)
          
    # gdalwarp resampling method for reprojection
    try:
        reprojection_resampling = get_dom_tag_value(dom, 'reprojection_resampling')
    except:
        reprojection_resampling = 'cubic' # default to cubic  
    # colormap
    try:
        colormap = get_dom_tag_value(dom, 'colormap')
    except:
        colormap = ''  
    # z-levels
    try:
        zlevels = get_dom_tag_value(dom, 'mrf_z_levels')
    except:
        zlevels = ''      
    # z key
    z = None
    zkey_type = "string" # default to only string for now
    try:
        zkey = get_dom_tag_value(dom, 'mrf_z_key')
    except:
        zkey = ''    
    # nocopy
    try:
        if get_dom_tag_value(dom, 'mrf_nocopy') == "true":
            nocopy = True
        else:
            nocopy = False
    except:
        nocopy = False
    # Close file.
    config_file.close()

# Make certain each directory exists and has a trailing slash.
if input_dir != None:
    input_dir = add_trailing_slash(check_abs_path(input_dir))
output_dir = add_trailing_slash(check_abs_path(output_dir))
working_dir = add_trailing_slash(check_abs_path(working_dir))
logfile_dir = add_trailing_slash(check_abs_path(logfile_dir))

# Save script_dir
script_dir = add_trailing_slash(os.path.dirname(os.path.abspath(__file__)))

# Ensure that mrf_compression_type is uppercase.
mrf_compression_type=string.upper(mrf_compression_type)

# Get current time, which is written to a file as the previous cycle time.  
# Time format is "yyyymmdd.hhmmss".  Do this first to avoid any gap where tiles 
# may get passed over because they were created while this script is running.
current_cycle_time=time.strftime('%Y%m%d.%H%M%S', time.localtime())

# Define output basename for log, txt, vrt, .mrf, .idx and .ppg or .pjg
# Files get date_of_date added, links do not.
basename=str().join([parameter_name, '_', date_of_data, '___', 'mrfgen_', 
                     current_cycle_time])

# Verify logfile_dir first so that the log can be started.
verify_directory_path_exists(logfile_dir, 'logfile_dir')
# Initialize log file.
log_filename=str().join([logfile_dir, basename, '.log'])
logging.basicConfig(filename=log_filename, level=logging.INFO)

# Verify remaining directory paths.
if input_dir != None:
    verify_directory_path_exists(input_dir, 'input_dir')
verify_directory_path_exists(output_dir, 'output_dir')
verify_directory_path_exists(working_dir, 'working_dir')

# Log all of the configuration information.
log_info_mssg_with_timestamp(str().join(['config XML file:  ', 
                                          configuration_filename]))
                                          
# Copy configuration file to working_dir (if it's not already there)
# so that the MRF can be recreated if needed.
if os.path.dirname(configuration_filename) != os.path.dirname(working_dir):
    config_preexisting=glob.glob(configuration_filename)
    if len(config_preexisting) > 0:
        at_dest_filename=str().join([working_dir, configuration_filename])
        at_dest_preexisting=glob.glob(at_dest_filename)
        if len(at_dest_preexisting) > 0:
            remove_file(at_dest_filename)
        shutil.copy(configuration_filename, working_dir+"/"+basename+".configuration_file.xml")
        log_info_mssg(str().join([
                          'config XML file:  copied to     ', working_dir]))
log_info_mssg(str().join(['config parameter_name:          ', parameter_name]))
log_info_mssg(str().join(['config date_of_data:            ', date_of_data]))
log_info_mssg(str().join(['config time_of_data:            ', time_of_data]))
if input_files != '':
    log_info_mssg(str().join(['config input_files:             ', input_files]))
if input_dir != None:
    log_info_mssg(str().join(['config input_dir:               ', input_dir]))
log_info_mssg(str().join(['config output_dir:              ', output_dir]))
log_info_mssg(str().join(['config working_dir:             ', working_dir]))
log_info_mssg(str().join(['config logfile_dir:             ', logfile_dir]))
log_info_mssg(str().join(['config mrf_name:                ', mrf_name]))
log_info_mssg(str().join(['config mrf_empty_tile_filename: ', 
                          mrf_empty_tile_filename]))
log_info_mssg(str().join(['config vrtnodata:               ', vrtnodata]))
log_info_mssg(str().join(['config mrf_blocksize:           ', mrf_blocksize]))
log_info_mssg(str().join(['config mrf_compression_type:    ',
                          mrf_compression_type]))
log_info_mssg(str().join(['config outsize:                 ', outsize]))
log_info_mssg(str().join(['config target_x:                ', target_x]))
log_info_mssg(str().join(['config target_y:                ', target_y]))
log_info_mssg(str().join(['config target_epsg:             ', target_epsg]))
log_info_mssg(str().join(['config source_epsg:             ', source_epsg]))
log_info_mssg(str().join(['config extents:                 ', extents]))
log_info_mssg(str().join(['config target_extents:          ', target_extents]))
log_info_mssg(str().join(['config overview levels:         ', ' '.join(overview_levels)]))
log_info_mssg(str().join(['config overview resampling:     ', overview_resampling]))
log_info_mssg(str().join(['config reprojection resampling: ', reprojection_resampling]))
log_info_mssg(str().join(['config resize resampling:       ', resize_resampling]))
log_info_mssg(str().join(['config colormap:                ', colormap]))
log_info_mssg(str().join(['config mrf_nocopy:              ', str(nocopy)]))
log_info_mssg(str().join(['config mrf_z_levels:            ', zlevels]))
log_info_mssg(str().join(['config mrf_z_key:               ', zkey]))
log_info_mssg(str().join(['mrfgen current_cycle_time:      ', current_cycle_time]))
log_info_mssg(str().join(['mrfgen basename:                ', basename]))

# Verify that date is 8 characters.
if len(date_of_data) != 8:
    mssg='Format for <date_of_data> (in mrfgen XML config file) is:  yyyymmdd'
    log_sig_exit('ERROR', mssg, sigevent_url)
    
if time_of_data != '' and len(time_of_data) != 6:
    mssg='Format for <time_of_data> (in mrfgen XML config file) is:  HHMMSS'
    log_sig_exit('ERROR', mssg, sigevent_url)

# Check if empty tile filename was specified.
if len(mrf_empty_tile_filename) == 0:
    log_info_mssg(str('Empty tile not specified, none will be used.'))
    mrf_empty_tile_bytes=0
else:
    # Verify that the empty tile can be found.
    mrf_empty_tile_existing=glob.glob(mrf_empty_tile_filename)
    if len(mrf_empty_tile_existing) == 0:
        mssg=str().join(['Specified empty tile file not found:  ', mrf_empty_tile_filename])
        log_sig_exit('ERROR', mssg, sigevent_url)

    # Verify that the empty tile image format is either PNG or JPEG.
    mrf_empty_tile_what=imghdr.what(mrf_empty_tile_filename)
    if mrf_empty_tile_what != 'png' and mrf_empty_tile_what != 'jpeg' and mrf_empty_tile_what != 'tiff':
        mssg='Empty tile image format must be either png, jpeg, or tiff.'
        log_sig_exit('ERROR', mssg, sigevent_url)
    
    # Verify that the empty tile matches MRF compression type.
    if mrf_empty_tile_what == 'png':
        # Check the last 3 characters in case of PNG or PPNG.
        if mrf_compression_type[-3:len(mrf_compression_type)] != 'PNG':
            mssg='Empty tile format does not match MRF compression type.'
            log_sig_exit('ERROR', mssg, sigevent_url)
    
    if mrf_empty_tile_what == 'jpeg':
        # Check the first 2 characters in case of JPG or JPEG.
        if mrf_compression_type[0:2] != 'JP':
            mssg='Empty tile format does not match MRF compression type.'
            log_sig_exit('ERROR', mssg, sigevent_url)
    
    # Report empty tile size in bytes.
    mrf_empty_tile_bytes=os.path.getsize(mrf_empty_tile_filename)
    log_info_mssg(str().join(['Empty tile size is:             ',
                              str(mrf_empty_tile_bytes), ' bytes.']))

##IS LOCK FILE NECESSARY?
## Lock file indicates tile generation in progress.
#lock=glob.glob(str().join([input_dir, '*lock*']))
#if len(lock) > 0:
#    mssg='Lock found.'
#    log_sig_exit('INFO', mssg, sigevent_url)

#-------------------------------------------------------------------------------
# Organize output filenames.
#-------------------------------------------------------------------------------

# Change directory to working_dir.
os.chdir(working_dir)

# transparency flag for custom color maps; default to False
add_transparency = False

# Get list of all tile filenames.
if input_files == '':
    if mrf_compression_type.lower() == 'jpeg' or mrf_compression_type.lower() == 'jpg':
        alltiles=glob.glob(str().join([input_dir, '*.jpg']))
    else: #default to png
        alltiles=glob.glob(str().join([input_dir, '*.png']))
else:
    input_files = input_files.strip()
    alltiles = input_files.split(',')

if len(alltiles) == 0: # No tiles, check for possible tiffs
    alltiles=glob.glob(str().join([input_dir, '*.tif*']))

if mrf_compression_type.lower() == 'jpeg' or mrf_compression_type.lower() == 'jpg':
    tiff_compress = "JPEG"
else: # Default to png
    tiff_compress = "PNG"
    
# Filter out bad JPEGs
goodtiles = []
if mrf_compression_type.lower() == 'jpeg' or mrf_compression_type.lower() == 'jpg':
    for i, tile in enumerate(alltiles):
        # Create the identify command.
        identify_command_list=['identify', tile]
        if ".mrf" in tile: # ignore MRF inserts
            goodtiles.append(tile)
        else:
            # Execute identify.
            try:
                identify_process = subprocess.Popen(identify_command_list, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                identify_process.wait()
                if 'DirectClass' in identify_process.stdout.readlines()[0]:
                    goodtiles.append(tile)
                else:
                    try:
                        sigevent('ERROR', 'Bad JPEG tile detected: ' + tile, sigevent_url)
                    except urllib2.URLError:
                        print 'sigevent service is unavailable'
            except OSError:
                if i==0:
                    log_sig_warn('identify command not found, unable to detect bad JPEG tiles', sigevent_url)
                goodtiles.append(tile)
    alltiles = goodtiles
    
# Convert TIFF files
# for i, tile in enumerate(alltiles):
#     if '.tif' in tile:
#         print "Converting TIFF file " + tile + " to " + tiff_compress
#           
#         # Create the gdal_translate command.
#         gdal_translate_command_list=['gdal_translate', '-q', '-of', tiff_compress, '-co', 'WORLDFILE=YES',
#                                      tile, working_dir+os.path.basename(tile).split('.')[0]+'.'+str(tiff_compress).lower()]
#         # Log the gdal_translate command.
#         log_the_command(gdal_translate_command_list)
#   
#         # Execute gdal_translate.
#         subprocess.call(gdal_translate_command_list, stdout=subprocess.PIPE,
#                         stderr=subprocess.PIPE)
#           
#         # Replace with new tiles
#         alltiles[i] = working_dir+os.path.basename(tile).split('.')[0]+'.'+str(tiff_compress).lower()
        

# Convert RGBA PNGs to indexed paletted PNGs if requested
if mrf_compression_type == 'PPNG' and colormap != '':
    for i, tile in enumerate(alltiles):
        temp_tile = None
        
        # Check input PNGs/TIFFs if RGBA, then convert        
        if '.png' or '.tif' in tile.lower():
            
            # Run the gdal_info on PNG tile.
            gdalinfo_command_list=['gdalinfo', tile]
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            
            # Read gdal_info output
            if "ColorInterp=Palette" not in gdalinfo.stdout.read():
                if '.tif' in tile.lower():
                    # Convert TIFF files to PNG
                    print "Converting TIFF file " + tile + " to " + tiff_compress
                       
                    # Create the gdal_translate command.
                    gdal_translate_command_list=['gdal_translate', '-q', '-of', tiff_compress, '-co', 'WORLDFILE=YES',
                                                 tile, working_dir+os.path.basename(tile).split('.')[0]+'.'+str(tiff_compress).lower()]
                    # Log the gdal_translate command.
                    log_the_command(gdal_translate_command_list)
               
                    # Execute gdal_translate.
                    subprocess.call(gdal_translate_command_list, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
                       
                    # Replace with new tiles
                    tile = working_dir+os.path.basename(tile).split('.')[0]+'.'+str(tiff_compress).lower()
                    temp_tile = tile
                
                print "Converting RGBA PNG to indexed paletted PNG"
                
                output_tile = working_dir + os.path.basename(tile).split('.')[0]+'_indexed.png'
                
                # Create the RGBApng2Palpng command.
                if vrtnodata == "":
                    fill = 0
                else:
                    fill = vrtnodata
                RGBApng2Palpng_command_list=[script_dir+'RGBApng2Palpng', '-v', '-lut=' + colormap,
                                             '-fill='+str(fill), '-of='+output_tile, tile]
                # Log the RGBApng2Palpng command.
                log_the_command(RGBApng2Palpng_command_list)
         
                # Execute RGBApng2Palpng.
                try:
                    RGBApng2Palpng = subprocess.Popen(RGBApng2Palpng_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except OSError:
                    log_sig_exit('ERROR', "RGBApng2Palpng tool cannot be found.", sigevent_url)
                
                RGBApng2Palpng.wait()
                if RGBApng2Palpng.returncode != None:
                    if  0 < RGBApng2Palpng.returncode < 255:
                        mssg = "RGBApng2Palpng: " + str(RGBApng2Palpng.returncode) + " colors in image not found in color table"
                        log_sig_warn(mssg, sigevent_url)
                    if RGBApng2Palpng.returncode == 255:
                        try:
                            mssg = sigevent('ERROR', "RGBApng2Palpng: " + str(RGBApng2Palpng.stderr.readlines()[-1]), sigevent_url)
                        except urllib2.URLError:
                            print 'sigevent service is unavailable'
                
                if os.path.isfile(output_tile):
                    mssg = output_tile + " created"
                    try:
                        sigevent('INFO', mssg, sigevent_url)
                    except urllib2.URLError:
                        print 'sigevent service is unavailable'
                    # Replace with new tiles
                    alltiles[i] = output_tile
                else:
                    try:
                        sigevent('ERROR', "RGBApng2Palpng failed to create " + output_tile, sigevent_url)
                    except urllib2.URLError:
                        print 'sigevent service is unavailable'
                
                # Make a copy of world file
                if os.path.isfile(tile.split('.')[0]+'.pgw'):
                    shutil.copy(tile.split('.')[0]+'.pgw', output_tile.split('.')[0]+'.pgw')
                elif os.path.isfile(tile.split('.')[0]+'.wld'):
                    shutil.copy(tile.split('.')[0]+'.wld', output_tile.split('.')[0]+'.pgw')
                else:
                    print "World file does not exist for tile: " + tile
                    
                # add transparency flag for custom color map
                add_transparency = True
            else:
                print "Paletted image verified"
                
        # remove tif temp tiles
        if temp_tile != None:
            remove_file(temp_tile)
            remove_file(temp_tile+'.aux.xml')
            remove_file(temp_tile.split('.')[0]+'.wld')     
        
# sort
alltiles.sort()

# check for different resolutions
diff_res = diff_resolution(alltiles)

#UNTIL MRF PARTIAL UPDATES ARE IMPLEMENTED, PROCESS ENTIRE GLOBE IF ANY NEW 
#TILES ARE DETECTED.
# Write all tiles list to a file on disk.
all_tiles_filename=str().join([working_dir, basename, '_all_tiles.txt'])
try:
    # Open file.
    alltilesfile=open(all_tiles_filename, 'w')
except IOError:
    mssg=str().join(['Cannot open for write:  ', all_tiles_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
else:
    # Write to file with line termination.
    for ndx in range(len(alltiles)):
        alltilesfile.write(str().join([alltiles[ndx], '\n']))
    # Close file.
    alltilesfile.close()
# Send to log.
log_info_mssg(str().join(['all tiles:  ', str(len(alltiles))]))
log_info_mssg(all_tiles_filename)

#-------------------------------------------------------------------------------
# Begin GDAL processing.
#-------------------------------------------------------------------------------

# Convert date of the data into day of the year.  Requred for TWMS server.
doy=get_doy_string(date_of_data)
# Combine year and doy to conform to TWMS convention (yyyydoy).
doy=str().join([date_of_data[0:4], str(doy)])
# Send to log.
log_info_mssg(str().join(['doy:  ', doy]))

# The .mrf file is the XML component of the MRF format.
mrf_filename=str().join([output_dir, basename, '.mrf'])
# The .idx file is the index compnent of the MRF format.
idx_filename=str().join([output_dir, basename, '.idx'])

# The image component of MRF is .pjg or .ppg, depending on compression type.
if mrf_compression_type == 'PNG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ppg'])
elif mrf_compression_type == 'PPNG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ppg'])
elif mrf_compression_type == 'JPG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.pjg'])
elif mrf_compression_type == 'JPEG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.pjg'])
elif mrf_compression_type == 'TIF' or mrf_compression_type == 'TIFF':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ptf'])
else:
    mssg='Unrecognized compression type for MRF: ' + mrf_compression_type 
    log_sig_exit('ERROR', mssg, sigevent_url)

# The .vrt file is the XML describing the virtual image mosaic layout.
vrt_filename=str().join([working_dir, basename, '.vrt'])

# Make certain output files do not preexist.  GDAL has issues with that.
remove_file(mrf_filename)
remove_file(idx_filename)
remove_file(out_filename)
remove_file(vrt_filename)

# Check if this is an MRF insert update, if not then regenerate a new MRF
mrf_list = []
for tile in list(alltiles):
    if '.mrf' in tile.lower():
        mrf_list.append(tile)
        alltiles.remove(tile)
if len(mrf_list) == 0 and input_files == '':
    mrf_list = glob.glob(str().join([input_dir, '*.mrf']))
# Should only be one MRF, so use that one
if len(mrf_list) > 0:
    mrf = mrf_list[0]
    print "Inserting new tiles to", mrf
    
    mrf_insert_command_list = ['mrf_insert', '-v', '-r', 'avg']
    for tile in alltiles:
        mrf_insert_command_list.append(tile)
    mrf_insert_command_list.append(mrf)
    log_the_command(mrf_insert_command_list)
    try:
        mrf_insert = subprocess.Popen(mrf_insert_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        log_sig_exit('ERROR', "mrf_insert tool cannot be found.", sigevent_url)
    insert_message = mrf_insert.stderr.readlines()
    # Continue or break if there is an error?
    for message in insert_message:
        # Break on error
        if 'ERROR' in message:
            log_sig_exit('ERROR', message, sigevent_url)
        else:
            print message.strip()

    # Copy MRF to output
    shutil.copy(mrf, mrf_filename)
    shutil.copy(mrf.replace('.mrf','.idx'), idx_filename)
    shutil.copy(mrf.replace('.mrf',out_filename[-4:]), out_filename)
    
    # Clean up
    remove_file(all_tiles_filename)

    # Exit here since we don't need to build an MRF from scratch
    mssg=str().join(['MRF created:  ', out_filename])
    log_sig_exit('INFO', mssg, sigevent_url)
  
    
# Check if z-dimension is consistent if it's being used
if zlevels != '':
    mrf_out = output_dir + get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data, time_of_data)[0]
    try:
        # Open file.
        mrf_file=open(mrf_out, 'r')
    except IOError:
        mssg=str().join(['MRF not yet generated:  ', mrf_out])
        log_info_mssg(mssg)
    else:
        dom=xml.dom.minidom.parse(mrf_file)           
        size_elements = dom.getElementsByTagName('Size')
        sizeZ=size_elements[0].getAttribute('z') #bands
        if sizeZ == '':
            mssg = "The output MRF does not contain z-levels: " + mrf_out
            log_sig_exit('ERROR', mssg, sigevent_url)            
        
        # Send to log.
        log_info_mssg(str().join(['size of existing MRF z-dimension:  ', str(sizeZ)]))
        # Close file.
        mrf_file.close()
        # Validate
        if zlevels != str(sizeZ):
            mssg=str().join(['Z-level size does not match existing MRF: ', zlevels])
            log_sig_warn(mssg, sigevent_url)

# Get z-index from ZDB if using z-dimension
con = None
if zkey != '':
    mrf_filename, idx_filename, out_filename, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data, time_of_data)
    mrf_filename = output_dir + mrf_filename
    idx_filename = output_dir + idx_filename
    out_filename = output_dir + out_filename
    zdb_out = mrf_filename.replace('.mrf','.zdb')
    try:
        db_exists = os.path.isfile(zdb_out)
        log_info_mssg("Connecting to " + zdb_out)
        con = sqlite3.connect(zdb_out, timeout=600.0) # 10 minute timeout
        
        if db_exists == False:
            cur = con.cursor() 
            cur.executescript("CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT);")
            cur.execute("INSERT INTO ZINDEX(z, key_str) VALUES (0,'"+zkey+"')")
            z = cur.lastrowid
        else: 
            cur = con.cursor()
            
            # Check for existing key
            cur.execute("SELECT COUNT(*) FROM ZINDEX WHERE key_str='"+zkey+"';")
            lid = int(cur.fetchone()[0])
            if lid > 0:                
                mssg = zkey + " key already exists...overwriting"
                log_sig_warn(mssg, sigevent_url)
                cur.execute("SELECT z FROM ZINDEX WHERE key_str='"+zkey+"';")
                z = int(cur.fetchone()[0]) 
            else:              
                # Check z size
                cur.execute("SELECT COUNT(*) FROM ZINDEX;")
                lid = int(cur.fetchone()[0])
                if lid >= int(zlevels):
                    mssg = str(lid+1) + " z-levels is more than the maximum allowed: " + str(zlevels)
                    log_sig_exit('ERROR', mssg, sigevent_url)
                # Insert values
                cur.execute("INSERT INTO ZINDEX(key_str) VALUES ('"+zkey+"')")
                z = cur.lastrowid
        log_info_mssg("Current z-level is " +str(z))
        
    except sqlite3.Error, e:
        if con:
            con.rollback()
        mssg = "%s:" % e.args[0]
        log_sig_exit('ERROR', mssg, sigevent_url)
    
# Use specific z if appropriate
if z != None:
    gdal_mrf_filename = mrf_filename + ":MRF:Z" + str(z)
else:
    gdal_mrf_filename = mrf_filename
    
        
# Create the gdalbuildvrt command.
#RESCALE BLUE MARBLE AND USE BLOCKSIZE=256.
#CONSIDER DOING THIS FOR EVERY SOTO DATASET.
#xres=str(360./65536)
#yres=xres
#              '-resolution', 'user', '-tr', xres, yres,
#              '-addalpha',
#target_x=str(360.0/int(target_x))
#target_y=target_x

gdalbuildvrt_command_list=['gdalbuildvrt','-q', '-te', xmin, ymin, xmax, ymax,'-input_file_list', all_tiles_filename]
# use resolution?
if diff_res == True:
    xres = str(360.0/int(target_x))
    yres = xres
    log_sig_warn("Different tile resolutions detected, using: " + str(xres), sigevent_url)
    gdalbuildvrt_command_list.append('-resolution')
    gdalbuildvrt_command_list.append('user')
    gdalbuildvrt_command_list.append('-tr')
    gdalbuildvrt_command_list.append(xres)
    gdalbuildvrt_command_list.append(yres)
if source_epsg != "":
    gdalbuildvrt_command_list.append('-a_srs')
    gdalbuildvrt_command_list.append(source_epsg)
if vrtnodata != "":
    gdalbuildvrt_command_list.append('-vrtnodata')
    gdalbuildvrt_command_list.append(vrtnodata)
# add VRT filename at the end        
gdalbuildvrt_command_list.append(vrt_filename)

# USE GDAL_TRANSLATE -OUTSIZE INSTEAD OF -TR.
#'-tr', target_x, target_y, '-resolution', 'user'
# Log the gdalbuildvrt command.
log_the_command(gdalbuildvrt_command_list)
# Capture stderr to record skipped .png files that are not valid PNG+World.
gdalbuildvrt_stderr_filename=str().join([working_dir, basename,
                                         '_gdalbuildvrt_stderr.txt'])
# Open stderr file for write.
gdalbuildvrt_stderr_file=open(gdalbuildvrt_stderr_filename, 'w')

#---------------------------------------------------------------------------
# Execute gdalbuildvrt.
subprocess.call(gdalbuildvrt_command_list, stderr=gdalbuildvrt_stderr_file)
#---------------------------------------------------------------------------

# Reproject to target EPSG
if target_epsg != source_epsg:
    log_info_mssg("Converting tiles to " + target_epsg)
    gdal_warp_command_list = ['gdalwarp', '-of', 'VRT' ,'-r', reprojection_resampling, '-s_srs', source_epsg, '-t_srs', target_epsg, '-te', target_xmin, target_ymin, target_xmax, target_ymax, '-multi', vrt_filename, vrt_filename.replace('.vrt','_reproj.vrt')]
    log_the_command(gdal_warp_command_list)
    subprocess.call(gdal_warp_command_list, stderr=gdalbuildvrt_stderr_file)
    vrt_filename = vrt_filename.replace('.vrt','_reproj.vrt')

# use gdalwarp if resize with resampling method is declared
if resize_resampling != '':
    if target_y == '':
        target_y = int(int(target_x)/2)
    gdal_warp_command_list = ['gdalwarp', '-of', 'VRT' ,'-r', resize_resampling, '-ts', str(target_x), str(target_y), '-te', target_xmin, target_ymin, target_xmax, target_ymax, '-overwrite', vrt_filename, vrt_filename.replace('.vrt','_resample.vrt')]
    log_the_command(gdal_warp_command_list)
    subprocess.call(gdal_warp_command_list, stderr=gdalbuildvrt_stderr_file)
    vrt_filename = vrt_filename.replace('.vrt','_resample.vrt')

# Close stderr file.
gdalbuildvrt_stderr_file.close()

# Open stderr file for read.
try:
    gdalbuildvrt_stderr_file=open(gdalbuildvrt_stderr_filename, 'r')
    # Report skipped .png files that are not valid PNG+World.
    gdalbuildvrt_stderr=gdalbuildvrt_stderr_file.readlines()
    # Loop over all lines in file.
    for ndx in range(len(gdalbuildvrt_stderr)):
        # Get line number(s) where skipped files appear in the stderr file.
        skipped=gdalbuildvrt_stderr[ndx].find('Warning')
        # If a line (including line 0) was found.
        if skipped >= 0:
            mssg=str().join(['gdalbuildvrt ', gdalbuildvrt_stderr[ndx]])
            log_sig_warn(mssg, sigevent_url)
    # Close file.
    gdalbuildvrt_stderr_file.close()
except IOError:
    mssg=str().join(['Cannot read:  ', gdalbuildvrt_stderr_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)

# Clean up.
remove_file(all_tiles_filename)
# Check if vrt was created.
vrt_output=glob.glob(vrt_filename)
if len(vrt_output) == 0:
    mssg=str().join(['Fail:  gdalbuildvrt',
                     '  May indicate no georeferenced tiles found.',
                     #'  May indicate unappropriate target_x.',
                     '  Look at stderr file:  ', 
                     gdalbuildvrt_stderr_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)

# Create mrf only if vrt was successful.
vrtf=get_modification_time(vrt_filename)
remove_file(gdalbuildvrt_stderr_filename)
# Set the compression type for gdal_translate (-co NAME=VALUE).
if mrf_compression_type == 'PNG':
    # Unpaletted PNG.
    compress=str('COMPRESS=PNG')
elif mrf_compression_type == 'PPNG':
    # Paletted PNG.
    compress=str('COMPRESS=PPNG')
elif mrf_compression_type == 'JPG':
    compress=str('COMPRESS=JPEG')
elif mrf_compression_type == 'JPEG':
    compress=str('COMPRESS=JPEG')
elif mrf_compression_type == 'TIFF' or mrf_compression_type == 'TIF':
    compress=str('COMPRESS=TIF')
else:
    mssg='Unrecognized compression type for MRF.'
    log_sig_exit('ERROR', mssg, sigevent_url)
    
# Insert color map into VRT if provided
if colormap != '':
    new_vrt_filename = vrt_filename.replace('.vrt','_newcolormap.vrt')
    if add_transparency == True:
        colormap2vrt_command_list=[script_dir+'colormap2vrt.py','--colormap',colormap,'--output',new_vrt_filename,'--merge',vrt_filename, '--sigevent_url', sigevent_url, '--transparent']
    else:
        colormap2vrt_command_list=[script_dir+'colormap2vrt.py','--colormap',colormap,'--output',new_vrt_filename,'--merge',vrt_filename, '--sigevent_url', sigevent_url]
    log_the_command(colormap2vrt_command_list)
    colormap2vrt_stderr_filename=str().join([working_dir, basename,'_colormap2vrt_stderr.txt'])
    colormap2vrt_stderr_file=open(colormap2vrt_stderr_filename, 'w+')
    subprocess.call(colormap2vrt_command_list, stderr=colormap2vrt_stderr_file)
    colormap2vrt_stderr_file.seek(0)
    colormap2vrt_stderr = colormap2vrt_stderr_file.read()
    print colormap2vrt_stderr
    if "Error" in colormap2vrt_stderr:
        log_sig_exit('ERROR', "Error executing colormap2vrt.py with colormap:" + colormap, sigevent_url)
    colormap2vrt_stderr_file.close()
    if os.path.isfile(new_vrt_filename):
        remove_file(colormap2vrt_stderr_filename)
        vrt_filename = new_vrt_filename

# Set the blocksize for gdal_translate (-co NAME=VALUE).
blocksize=str().join(['BLOCKSIZE=', mrf_blocksize])

# Get input size.
dom=xml.dom.minidom.parse(vrt_filename)
rastersize_elements=dom.getElementsByTagName('VRTDataset')
x_size=rastersize_elements[0].getAttribute('rasterXSize') #width
y_size=rastersize_elements[0].getAttribute('rasterYSize') #height

if target_x == '':
    log_info_mssg('x size and y size from VRT ' + x_size + "," + y_size)
    exp=11 #minimum outsize 20480 for EPSG4326_2km
    while int(10*(2**exp)) < int(x_size):
        #print str(10*(2**exp)) + " is less than " + str(x_size)
        exp+=1
    target_x=str(10*(2**exp))            
    log_info_mssg('Calculating target_x from VRT to ' + target_x)          

# Only use new target size if different.
if target_x != x_size:
    # Calculate output size of Y dimension and maintain aspect ratio.
    target_y=str(int(float(target_x)*(float(y_size)/float(x_size))))
    log_info_mssg('Calculating target_y ' + target_y)
    if resize_resampling == '':
        log_sig_warn('Target size (' + target_x + 'x' + target_y + ') differs from input size (' + x_size + 'x' + y_size + ')' + ', but <resize_resampling> flag has not been set.', sigevent_url)
else: #don't bother calculating y
    #target_x=x_size
    target_y=y_size
    log_info_mssg('Setting target_y from VRT to ' + target_y)
    
# if target_epsg == "EPSG:3857":
#     target_y = target_x

#-----------------------------------------------------------------------
# Seed the MRF data file (.ppg or .pjg) with a copy of the empty tile.
if mrf_empty_tile_filename != '' and (z == None or z == 0):
    log_info_mssg('Seed the MRF data file with a copy of the empty tile.' )
    log_info_mssg(str().join(['Copy ', mrf_empty_tile_filename,' to ', out_filename]))
    shutil.copy(mrf_empty_tile_filename, out_filename)
#-----------------------------------------------------------------------    

# Create the gdal_translate command.         
gdal_translate_command_list=['gdal_translate', '-q', '-of', 'MRF', '-co', compress, '-co', blocksize,'-outsize', target_x, target_y]    
if compress == "COMPRESS=JPEG":
    # Use JPEG quality of 80
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('QUALITY=80')
if zlevels != '':
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('ZSIZE='+str(zlevels))
if nocopy == True:
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('NOCOPY=true')
        
# add ending parameters      
gdal_translate_command_list.append(vrt_filename)
gdal_translate_command_list.append(gdal_mrf_filename)
    
# Log the gdal_translate command.
log_the_command(gdal_translate_command_list)
# Capture stderr.
gdal_translate_stderr_filename=str().join([working_dir, basename, '_gdal_translate_stderr.txt'])
# Open stderr file for write.
gdal_translate_stderr_file=open(gdal_translate_stderr_filename, 'w')

#-----------------------------------------------------------------------
# Execute gdal_translate.
subprocess.call(gdal_translate_command_list, stderr=gdal_translate_stderr_file)
#-----------------------------------------------------------------------

# Close stderr file.
gdal_translate_stderr_file.close()

# Copy vrt to output
if data_only == False:
    shutil.copy(vrt_filename, str().join([output_dir, basename, '.vrt']))

# Clean up.
vrt_files = glob.glob(str().join([working_dir, basename, '*.vrt']))
for vrt in vrt_files:
    remove_file(vrt)

# Check if MRF was created.
mrf_output=glob.glob(mrf_filename)
if len(mrf_output) == 0:
    mssg=str().join(['Fail:  gdal_translate',
                     ' Check gdal mrf driver plugin.',
                     ' Check stderr file:  ', 
                     gdal_translate_stderr_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)

# Get largest x,y dimension of MRF, usually x.
try:
    # Open file.
    mrf_file=open(mrf_filename, 'r')
except IOError:
    mssg=str().join(['Cannot read:  ', mrf_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
else:
    dom=xml.dom.minidom.parse(mrf_file)
    # Raster
    size_elements=dom.getElementsByTagName('Size')
    sizeX=size_elements[0].getAttribute('x') #width
    sizeY=size_elements[0].getAttribute('y') #height
    sizeC=size_elements[0].getAttribute('c') #bands
    sizeZ=size_elements[0].getAttribute('z') #bands
    # Send to log.
    log_info_mssg(str().join(['size of MRF:  ', sizeX, ' x ', sizeY]))
    # Close file.
    mrf_file.close()
    # Get largest dimension, usually X.
    actual_size=max([int(sizeX), int(sizeY)])

# Create pyramid only if idx (MRF index file) was successfully created.
idxf=get_modification_time(idx_filename)
compare_time=time.strftime('%Y%m%d.%H%M%S', time.localtime())
old_stats=os.stat(idx_filename)
if idxf >= vrtf:
    remove_file(gdal_translate_stderr_filename)

    if overview_levels == '' or int(overview_levels[0])>1:
        # Create the gdaladdo command.
        gdaladdo_command_list=['gdaladdo', '-q', '-r', overview_resampling,
                               str(gdal_mrf_filename)]
        # Build out the list of gdaladdo pyramid levels (a.k.a. overviews).
        if overview_levels == '':
            overview=2
            gdaladdo_command_list.append(str(overview))
            exp=2
            while (overview*long(mrf_blocksize)) < actual_size:
                overview=2**exp
                exp=exp+1
                gdaladdo_command_list.append(str(overview))
        else:
            for overview in overview_levels:
                gdaladdo_command_list.append(str(overview))
        # Log the gdaladdo command.
        log_the_command(gdaladdo_command_list)
        # Capture stderr.
        gdaladdo_stderr_filename=str().join([working_dir, basename,
                                             '_gdaladdo_stderr.txt'])
        # Open stderr file for write.
        gdaladdo_stderr_file=open(gdaladdo_stderr_filename, 'w')

        #-------------------------------------------------------------------
        # Execute gdaladdo.
        subprocess.call(gdaladdo_command_list, stderr=gdaladdo_stderr_file)
        #-------------------------------------------------------------------

        # Close stderr file.
        gdaladdo_stderr_file.close()

        # Update previous cycle time only if gdaladdo was successful.
        addf=get_modification_time(idx_filename)
        new_stats=os.stat(idx_filename)

        # Check for gdaladdo success by checking time stamp and file size.
        if (addf >= compare_time) or (new_stats.st_size >= old_stats.st_size):
            remove_file(gdaladdo_stderr_filename)
        else:
            log_info_mssg(str().join(['addf = ',str(addf)]))
            log_info_mssg(str().join(['compare_time = ',str(compare_time)]))
            log_info_mssg('addf should be >= compare_time')
            log_info_mssg(str().join(['new_stats.st_size = ',
                                      str(new_stats.st_size)]))
            log_info_mssg(str().join(['old_stats.st_size = ',
                                      str(old_stats.st_size)]))
            log_info_mssg('new_stats.st_size should be >= old_stats.st_size')
            mssg=str().join(['Unsuccessful:  gdaladdo   Check stderr file: ',
                             gdaladdo_stderr_filename])
            log_sig_exit('ERROR', mssg, sigevent_url)
else:
    log_info_mssg(str().join(['idxf = ',str(idxf)]))
    log_info_mssg(str().join(['vrtf = ',str(vrtf)]))
    log_info_mssg('idxf should be >= vrtf')
    mssg=str().join(['Unsuccessful:  gdal_translate   ',
                     'Check the gdal mrf driver plugin.  ',
                     'Check stderr file: ',
                     gdal_translate_stderr_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
    
# Insert into nocopy
if nocopy==True:
    print "Inserting new tiles to", gdal_mrf_filename
    mrf_insert_command_list = ['mrf_insert', '-v', '-r', 'Avg']
    for tile in alltiles:
        if diff_resolution([tile, mrf_filename]):
            # convert tile to matching resolution
            tile_vrt_command_list = ['gdalwarp', '-of', 'VRT', '-tr', str(360.0/int(target_x)), str(-360.0/int(target_x)), tile, tile+".vrt"]
            log_the_command(tile_vrt_command_list)
            tile_vrt = subprocess.Popen(tile_vrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tile_vrt.wait()
            mrf_insert_command_list.append(tile+".vrt")
        else:
            mrf_insert_command_list.append(tile)
    mrf_insert_command_list.append(gdal_mrf_filename)
    log_the_command(mrf_insert_command_list)
    try:
        mrf_insert = subprocess.Popen(mrf_insert_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        log_sig_exit('ERROR', "mrf_insert tool cannot be found.", sigevent_url)
    insert_message = mrf_insert.stderr.readlines()
    for message in insert_message:
        # Break on error
        if 'ERROR' in message:
            log_sig_exit('ERROR', message, sigevent_url)
        else:
            print message.strip()
    remove_file(tile+".vrt")
    
# Rename MRFs
if mrf_name != '':
    output_mrf, output_idx, output_data, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data, time_of_data)
    if (output_dir+output_mrf) != mrf_filename:
        log_info_mssg(str().join(['Moving ',mrf_filename, ' to ', output_dir+output_mrf]))
        shutil.move(mrf_filename, output_dir+output_mrf)
    if (output_dir+output_idx) != idx_filename:
        log_info_mssg(str().join(['Moving ',idx_filename, ' to ', output_dir+output_idx]))
        shutil.move(idx_filename, output_dir+output_idx)
    if (output_dir+output_data) != out_filename:
        log_info_mssg(str().join(['Moving ',out_filename, ' to ', output_dir+output_data]))
        shutil.move(out_filename, output_dir+output_data)
    if data_only == False:
        if os.path.isfile(mrf_filename+".aux.xml"):
            log_info_mssg(str().join(['Moving ',mrf_filename+".aux.xml", ' to ', working_dir+output_aux]))
            shutil.move(mrf_filename+".aux.xml", working_dir+output_aux)
        if os.path.isfile(str().join([output_dir, basename, '.vrt'])):
            log_info_mssg(str().join(['Moving ',str().join([output_dir, basename, '.vrt']), ' to ', working_dir+output_vrt]))
            shutil.move(str().join([output_dir, basename, '.vrt']), working_dir+output_vrt)
    mrf_filename = output_dir+output_mrf
    out_filename = output_dir+output_data
    
# Leave only MRF data, index, and header files
if data_only == True:
    remove_file(log_filename)
    remove_file(output_dir+"/"+basename+".mrf.aux.xml")
    remove_file(working_dir+"/"+basename+".configuration_file.xml")
    
# Commit database if successful
if con:
    con.commit()
    con.close()
    log_info_mssg("Successfully committed record to " + zdb_out)
else:
    log_info_mssg("No ZDB record created")

# Remove temp tiles
for tilename in (alltiles):
    if working_dir in tilename:
        remove_file(tilename)
        if tiff_compress != None:
            remove_file(tilename+'.aux.xml')
        if '_indexed.' in tilename:
            remove_file(tilename.split('.')[0]+'.pgw')

# Send to log.
mssg=str().join(['MRF created:  ', out_filename])
log_sig_exit('INFO', mssg, sigevent_url)