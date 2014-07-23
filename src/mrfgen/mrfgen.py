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
#  <vrtnodata>0</vrtnodata>
#  <mrf_blocksize>512</mrf_blocksize>
#  <mrf_compression_type>JPEG</mrf_compression_type>
#  <resampling>nearest</resampling>
#  <extents>-180,-90,180,90</extents>
#  <mrf_name>{$parameter_name}%Y%j_.mrf</mrf_name>
#  <colormap></colormap>
# </mrfgen_configuration>
#
# Global Imagery Browse Services / Physical Oceanography Distributed Active Archive Center (PO.DAAC)
# NASA Jet Propulsion Laboratory
# 2014
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
        script_dir = '/usr/share/onearth' # use default directory if in bin
    empty_config_file=open(script_dir+"/empty_tiles/empty_config", 'r')
    tiles = {}
    for line in empty_config_file:
        (key, val) = line.split()
        tiles[key] = val
    
    try:   
        return os.path.abspath(script_dir+"/empty_tiles/"+tiles[empty_tile])
    except KeyError:
        mssg = '"' + empty_tile + '" is not a valid empty tile.'
        log_sig_exit('ERROR', mssg, sigevent_url)
        
def get_mrf_names(mrf_data, mrf_name, parameter_name, date_of_data):
    """
    Convert MRF filenames to specified naming convention (mrf_name).
    Argument:
        mrf_data -- the created MRF data file
        mrf_name -- the MRF naming convention to use
        parameter_name -- MRF parameter name
        date_of_data -- the date of the MRF data, example: 20120730
    """
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

#-------------------------------------------------------------------------------
# Finished defining subroutines.  Begin main program.
#-------------------------------------------------------------------------------

# Define command line options and args.
parser=OptionParser()
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
    sent=sigevent('ERROR', mssg, sigevent_url)
    sys.exit(mssg)
else:
    # Get dom from XML file.
    dom=xml.dom.minidom.parse(config_file)
    # Parameter name.
    parameter_name         =get_dom_tag_value(dom, 'parameter_name')
    date_of_data           =get_dom_tag_value(dom, 'date_of_data')
    # Directories.
    try:
        input_dir            =get_dom_tag_value(dom, 'input_dir')
    except IndexError: #use output_dir if not specified (for previous cycle time)
        input_dir            =get_dom_tag_value(dom, 'output_dir')
    output_dir             =get_dom_tag_value(dom, 'output_dir')
    try:
        cache_dir              =get_dom_tag_value(dom, 'cache_dir')
    except IndexError: # use output dir if not provided
        cache_dir              =get_dom_tag_value(dom, 'output_dir')
    try:
        working_dir            =get_dom_tag_value(dom, 'working_dir')
    except IndexError: # use /tmp/ as default
        working_dir            ='/tmp/'
    try:
        logfile_dir            =get_dom_tag_value(dom, 'logfile_dir')
    except IndexError: #use working_dir if not specified
        logfile_dir            =working_dir
    try:
        mrf_name=get_dom_tag_value(dom, 'mrf_name')
    except IndexError:
        # default to GIBS naming convention
        mrf_name='{$parameter_name}%Y%j_.mrf'
    # MRF specific parameters.
    try:
        mrf_empty_tile_filename=check_abs_path(get_dom_tag_value(dom, 'mrf_empty_tile_filename'))
    except IndexError:
        mrf_empty_tile_filename=lookupEmptyTile(get_dom_tag_value(dom, 'empty_tile'))
    vrtnodata              =get_dom_tag_value(dom, 'vrtnodata')
    mrf_blocksize          =get_dom_tag_value(dom, 'mrf_blocksize')
    mrf_compression_type   =get_dom_tag_value(dom, 'mrf_compression_type')
    try:
        target_x               =get_dom_tag_value(dom, 'target_x')
    except IndexError:
        target_x = '' # if no target_x then use rasterXSize and rasterYSize from VRT file
    # Target extents.
    try:
        extents        =get_dom_tag_value(dom, 'extents')
    except IndexError:
        extents = '-180,-90,180,90' # default to geographic
    xmin, ymin, xmax, ymax = extents.split(',')
    # Input files.
    try:
        input_files        =get_dom_tag_value(dom, 'input_files')
    except IndexError:
        input_files = ''
    # resampling method
    try:
        resampling        =get_dom_tag_value(dom, 'resampling')
    except IndexError:
        resampling = 'nearest'    
    # gdalwarp resampling method
    try:
        resize_resampling        =get_dom_tag_value(dom, 'resize')
    except IndexError:
        resize_resampling = ''   
    # colormap
    try:
        colormap               =get_dom_tag_value(dom, 'colormap')
    except:
        colormap = ''    
    # Close file.
    config_file.close()

# Make certain each directory exists and has a trailing slash.
input_dir  =add_trailing_slash(check_abs_path(input_dir))
output_dir =add_trailing_slash(check_abs_path(output_dir))
cache_dir  =add_trailing_slash(check_abs_path(cache_dir))
working_dir=add_trailing_slash(check_abs_path(working_dir))
logfile_dir=add_trailing_slash(check_abs_path(logfile_dir))

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
verify_directory_path_exists(input_dir, 'input_dir')
verify_directory_path_exists(output_dir, 'output_dir')
verify_directory_path_exists(cache_dir, 'cache_dir')
verify_directory_path_exists(working_dir, 'working_dir')

# Log all of the configuration information.
log_info_mssg_with_timestamp(str().join(['config XML file:  ', 
                                          configuration_filename]))
# Copy configuration file to input_dir (if it's not already there)
# so that the MRF can be recreated if needed.
if os.path.dirname(configuration_filename) != os.path.dirname(input_dir):
    config_preexisting=glob.glob(configuration_filename)
    if len(config_preexisting) > 0:
        at_dest_filename=str().join([input_dir, configuration_filename])
        at_dest_preexisting=glob.glob(at_dest_filename)
        if len(at_dest_preexisting) > 0:
            remove_file(at_dest_filename)
        shutil.copy(configuration_filename, working_dir+"/"+basename+".configuration_file.xml")
        log_info_mssg(str().join([
                          'config XML file:  moved to      ', input_dir]))
log_info_mssg(str().join(['config parameter_name:          ', parameter_name]))
log_info_mssg(str().join(['config date_of_data:            ', date_of_data]))
log_info_mssg(str().join(['config input_files:             ', input_files]))
log_info_mssg(str().join(['config input_dir:               ', input_dir]))
log_info_mssg(str().join(['config output_dir:              ', output_dir]))
log_info_mssg(str().join(['config cache_dir:               ', cache_dir]))
log_info_mssg(str().join(['config working_dir:             ', working_dir]))
log_info_mssg(str().join(['config logfile_dir:             ', logfile_dir]))
log_info_mssg(str().join(['config mrf_name:                ', mrf_name]))
log_info_mssg(str().join(['config mrf_empty_tile_filename: ', 
                          mrf_empty_tile_filename]))
log_info_mssg(str().join(['config vrtnodata:               ', vrtnodata]))
log_info_mssg(str().join(['config mrf_blocksize:           ', mrf_blocksize]))
log_info_mssg(str().join(['config mrf_compression_type:    ',
                          mrf_compression_type]))
log_info_mssg(str().join(['config target_x:                ', target_x]))
log_info_mssg(str().join(['config extents:                 ', extents]))
log_info_mssg(str().join(['config resampling:              ', resampling]))
log_info_mssg(str().join(['config resize:                  ', resize_resampling]))
log_info_mssg(str().join(['config colormap:                     ', colormap]))
log_info_mssg(str().join(['mrfgen current_cycle_time:      ', current_cycle_time]))
log_info_mssg(str().join(['mrfgen basename:                ', basename]))

# Verify that date is 8 characters.
if len(date_of_data) != 8:
    mssg='Format for <date_of_data> (in mrfgen XML config file) is:  yyyymmdd'
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

# Read previous cycle time string value from disk file.  
# Time format in txt file is "yyyymmdd.hhmmss" and will be treated as a double 
# precision value for comparing time stamps.
ptime_filename=str().join([input_dir, 'mrfgen_previous_cycle_time.txt'])
ptime_preexisting=glob.glob(ptime_filename)
# Default setting of zero will result in all tiles being procesed.
pretime='0.0'
if len(ptime_preexisting) > 0:
    try:
        # Open file.  Time format is "yyyymmdd.hhmmss".
        ptime_file=open(ptime_filename, 'r')
    except IOError:
        # Use time zero if file unreadable or not found.
        mssg=str().join(['All tiles will be processed because cannot open ', 
                         ptime_filename])
        # Send to log.
        log_info_mssg(mssg)
    else:
        # Read file.
        ptime_lines=ptime_file.readlines()
        #INDEX [0] NEEDS TO BE UN-HARDWIRED AS PART OF FUTURE XML PARSING.
        # Remove line termination.
# Ignore previous cycle time
#        pretime=ptime_lines[0].strip('\n')
        # Close file.
        ptime_file.close()

if pretime == '0.0':
    # Send to log.
    log_info_mssg(str().join(['No previous cycle time.',
                              ' All tiles will be processed.']))
else:
    # Send to log.
    log_info_mssg(str().join(['mrfgen previous_cycle_time:     ', pretime]))
    log_info_mssg(str().join(['mrfgen previous cycle from:     ',
                              ptime_filename]))

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
        
        # Check to see if tif files need to be converted
        if '.tif' in tile.lower():
            # Convert TIFF files
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
            
        # Check input PNGs if RGBA, then convert        
        if '.png' in tile.lower():
            
            # Run the gdal_info on PNG tile.
            gdalinfo_command_list=['gdalinfo', tile]
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            
            # Read gdal_info output
            if "ColorInterp=Palette" not in gdalinfo.stdout.read():
                print "Converting RGBA PNG to indexed paletted PNG"
                
                output_tile = working_dir + os.path.basename(tile).split('.')[0]+'_indexed.png'
                
                # Create the RGBApng2Palpng command.
                RGBApng2Palpng_command_list=[script_dir+'RGBApng2Palpng', '-v', '-lut=' + colormap,
                                             '-fill='+vrtnodata, '-of='+output_tile, tile]
                # Log the RGBApng2Palpng command.
                log_the_command(RGBApng2Palpng_command_list)
         
                # Execute RGBApng2Palpng.
                subprocess.call(RGBApng2Palpng_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if os.path.isfile(output_tile):
                    print output_tile, "created"
                    # Replace with new tiles
                    alltiles[i] = output_tile
                else:
                    raise Exception("Failed to create " + output_tile) #exception or warning?
                
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
                print "Paletted PNG verified"
                
        # remove tif temp tiles
        if temp_tile != None:
            remove_file(temp_tile)
            remove_file(temp_tile+'.aux.xml')
            remove_file(temp_tile.split('.')[0]+'.wld')     
        
#print alltiles
alltiles.sort()

# Initialize list of tile modification times.
modtimes=[]
# Initialize list of modified tiles.
modtiles=[]

#THIS TO BE USED WHEN MRF PARITAL UPDATE IS IMPLEMENTED.
#MEANWHILE IF ANY NEW TILES ARE DETECTED THEN REPROCESS ENTIRE GLOBE.
# Get modification time.  To be used for comparing to previous cycle time, so 
# literal time accuracy is unimportant.  Specifically, time ranking will be 
# used to check for tiles that have been created or updated since the last MRF 
# processing cycle.
log_info_mssg('List modification time for each input tile:')
for ndx in range(len(alltiles)):
    # Get modification time for each file.
    modf=get_modification_time(alltiles[ndx])
    # Append to list.
    modtimes.append(modf)
    # Add to modtiles list only if tile is updated since previous cycle time.
    if modtimes[ndx] > pretime:
        modtiles.append(alltiles[ndx])

if len(modtiles) == 0:
    mssg='No new tiles since previous cycle time.'
    log_sig_exit('INFO', mssg, sigevent_url)

# Send to log.
log_info_mssg(str().join(['new tiles:  ', str(len(modtiles))]))

# Write list of modified tiles to disk file.
mod_tiles_filename=str().join([working_dir, basename, '_mod_tiles.txt'])
try:
    # Open file.
    modtilesfile=open(mod_tiles_filename, 'w')
except IOError:
    mssg=str().join(['Cannot open for write:  ', mod_tiles_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
else:
    # Write to file with line termination.
    for ndx in range(len(modtiles)):
        modtilesfile.write(str().join([modtiles[ndx], '\n']))
    # Close file.
    modtilesfile.close()

# Send to log.
log_info_mssg(mod_tiles_filename)

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
#THIS SHOULD BE FOR MODIFIED TILES, ONCE MRF UPDATES ARE ENABLED.
# Send to log.
log_info_mssg(str().join(['all tiles:  ', str(len(alltiles))]))
log_info_mssg(all_tiles_filename)

#-------------------------------------------------------------------------------
# Begin GDAL processing.
#-------------------------------------------------------------------------------

#UNTIL MRF PARTIAL UPDATES ARE IMPLEMENTED, PROCESS ENTIRE GLOBE IF ANY NEW 
#TILES HAVE BEEN DETECTED.
if len(modtiles) > 0:
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
    # Construct the linknames.  These "idx" links will make the data active.
    cache_idx_linkname=str().join([cache_dir, parameter_name, doy, '_.idx'])
    cache_idx_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.idx'])

    # The image component of MRF is .pjg or .ppg, depending on compression type.
    if mrf_compression_type == 'PNG':
        # Output filename.
        out_filename=str().join([output_dir, basename, '.ppg'])
        # Linknames.
        cache_out_linkname=str().join([cache_dir, parameter_name, doy, '_.ppg'])
        cache_out_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.ppg'])
    elif mrf_compression_type == 'PPNG':
        # Output filename.
        out_filename=str().join([output_dir, basename, '.ppg'])
        # Linknames.
        cache_out_linkname=str().join([cache_dir, parameter_name, doy, '_.ppg'])
        cache_out_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.ppg'])
    elif mrf_compression_type == 'JPG':
        # Output filename.
        out_filename=str().join([output_dir, basename, '.pjg'])
        # Linknames.
        cache_out_linkname=str().join([cache_dir, parameter_name, doy, '_.pjg'])
        cache_out_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.pjg'])
    elif mrf_compression_type == 'JPEG':
        # Output filename.
        out_filename=str().join([output_dir, basename, '.pjg'])
        # Linknames.
        cache_out_linkname=str().join([cache_dir, parameter_name, doy, '_.pjg'])
        cache_out_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.pjg'])
    elif mrf_compression_type == 'TIFF':
        # Output filename.
        out_filename=str().join([output_dir, basename, '.ptf'])
        # Linknames.
        cache_out_linkname=str().join([cache_dir, parameter_name, doy, '_.ptf'])
        cache_out_ttttttt=str().join([cache_dir, parameter_name, 'TTTTTTT_.ptf'])
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
    if len(mrf_list) == 0:
        mrf_list = glob.glob(str().join([input_dir, '*.mrf']))
    # Should only be one MRF, so use that one
    if len(mrf_list) > 0:
        mrf = mrf_list[0]
        print "Inserting new tiles to", mrf
        
        mrf_insert_command_list = ['mrf_insert', '-v', '-r', 'average']
        for tile in alltiles:
            mrf_insert_command_list.append(tile)
        mrf_insert_command_list.append(mrf)
        log_the_command(mrf_insert_command_list)
        mrf_insert = subprocess.Popen(mrf_insert_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        remove_file(mod_tiles_filename)
        remove_file(all_tiles_filename)
        remove_file(ptime_filename)

        # Exit here since we don't need to build an MRF from scratch
        mssg=str().join(['MRF created:  ', out_filename])
        log_sig_exit('INFO', mssg, sigevent_url)

    # Create the gdalbuildvrt command.
    #RESCALE BLUE MARBLE AND USE BLOCKSIZE=256.
    #CONSIDER DOING THIS FOR EVERY SOTO DATASET.
    #xres=str(360./65536)
    #yres=xres
    #              '-resolution', 'user', '-tr', xres, yres,
    #              '-addalpha',
    #target_x=str(360.0/int(target_x))
    #target_y=target_x
    
    # use resolution?
    if target_x != '':
        xres = str(360.0/int(target_x))
        yres = xres
        gdalbuildvrt_command_list=['gdalbuildvrt',
            '-q', '-te', xmin, ymin, xmax, ymax,
            '-vrtnodata', vrtnodata,'-resolution', 'user', '-tr',xres, yres,
            '-input_file_list', all_tiles_filename,
            vrt_filename]
    else:
        gdalbuildvrt_command_list=['gdalbuildvrt',
            '-q', '-te', xmin, ymin, xmax, ymax,
            '-vrtnodata', vrtnodata,
            '-input_file_list', all_tiles_filename,
            vrt_filename]
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

    # use gdalwarp if resize with resampling method is declared
    if resize_resampling != '':
        target_y = int(int(target_x)/2)
        gdal_warp_command_list = ['gdalwarp', '-of', 'GTiff' ,'-r', resize_resampling, '-ts', str(target_x), str(target_y), '-te', xmin, ymin, xmax, ymax, '-overwrite', vrt_filename, vrt_filename.replace('.vrt','.tif')]
        gdalbuildvrt_command_list2 = ['gdalbuildvrt', '-q', '-srcnodata', '0', '-overwrite', vrt_filename, vrt_filename.replace('.vrt','.tif')]
         
        log_the_command(gdal_warp_command_list)
        log_the_command(gdalbuildvrt_command_list2)
        subprocess.call(gdal_warp_command_list, stderr=gdalbuildvrt_stderr_file)
        subprocess.call(gdalbuildvrt_command_list2, stderr=gdalbuildvrt_stderr_file)
        
        # add transparency
        new_vrt = open(vrt_filename,"r+")
        vrt_lines = new_vrt.readlines()
        for idx in range(0, len(vrt_lines)):
            vrt_lines[idx] = vrt_lines[idx].replace('c1="0" c2="0" c3="0" c4="255"', 'c1="0" c2="0" c3="0" c4="0"')
        new_vrt.seek(0)
        new_vrt.truncate()
        new_vrt.writelines(vrt_lines)
        new_vrt.close() 
    
    # Close stderr file.
    gdalbuildvrt_stderr_file.close()

    # Open stderr file for read.
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

    # Clean up.
    remove_file(mod_tiles_filename)
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
    if vrtf > pretime:
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
        elif mrf_compression_type == 'TIFF':
            compress=str('COMPRESS=TIFF')
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

            if os.path.isfile(new_vrt_filename):
                remove_file(vrt_filename)
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
        else: #don't bother calculating y
            #target_x=x_size
            target_y=y_size
            log_info_mssg('Setting target_y from VRT to ' + target_y)

        #-----------------------------------------------------------------------
        # Seed the MRF data file (.ppg or .pjg) with a copy of the empty tile.
        log_info_mssg('Seed the MRF data file with a copy of the empty tile.' )
        log_info_mssg(str().join(['Copy ', mrf_empty_tile_filename,' to ', out_filename]))
        shutil.copy(mrf_empty_tile_filename, out_filename)
        #-----------------------------------------------------------------------    

        # Create the gdal_translate command.
        gdal_translate_command_list=['gdal_translate', '-q', '-of', 'MRF',
                                     '-co', compress, '-co', blocksize,
                                     '-outsize', target_x, target_y,
                                     vrt_filename, mrf_filename]
        # Log the gdal_translate command.
        log_the_command(gdal_translate_command_list)
        # Capture stderr.
        gdal_translate_stderr_filename=str().join([working_dir, basename,
                                                  '_gdal_translate_stderr.txt'])
        # Open stderr file for write.
        gdal_translate_stderr_file=open(gdal_translate_stderr_filename, 'w')

        #-----------------------------------------------------------------------
        # Execute gdal_translate.
        subprocess.call(gdal_translate_command_list, 
                        stderr=gdal_translate_stderr_file)
        #-----------------------------------------------------------------------

        # Close stderr file.
        gdal_translate_stderr_file.close()
       
        # Copy vrt to output
        if data_only == False:
            shutil.copy(vrt_filename, str().join([output_dir, basename, '.vrt']))
       
        # Clean up.
        remove_file(vrt_filename)
        if resize_resampling != '':
            remove_file(vrt_filename.replace('.vrt','.tif'))

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

            # Create the gdaladdo command.
            gdaladdo_command_list=['gdaladdo', '-q', '-r', resampling,
                                   str(mrf_filename)]
            # Build out the list of gdaladdo pyramid levels (a.k.a. overviews).
            overview=2
            gdaladdo_command_list.append(str(overview))
            exp=2
            while (overview*long(mrf_blocksize)) < actual_size:
                overview=2**exp
                exp=exp+1
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
                # If MRF sucessfully created, then store current cycle time.
                # Write string value of current cycle time to disk file, to be 
                # used in the next cycle as the previous cycle time.  Time 
                # format is "yyyymmdd.hhmmss"
                try:
                    # GET FILENAME AND PATH FROM CONFIGURATION FILE.
                    # Open file.
                    ptime_file=open(ptime_filename, 'w')
                except IOError:
                    mssg1='Cannot open for write:  '
                    mssg2=ptime_filename
                    mssg3='  On next cycle all tiles will be processed.'
                    mssg=str().join([mssg1, mssg2, mssg3])
                    log_sig_warn(mssg, sigevent_url)
                else:
                    # Write to file with line termination.
                    ptime_file.write(str().join([current_cycle_time, '\n']))
                    # Close file.
                    ptime_file.close()
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
    else:
        log_info_mssg(str().join(['vrtf = ',str(vrtf)]))
        log_info_mssg(str().join(['pretime = ',str(pretime)]))
        log_info_mssg('vrtf should be >= pretime')
        mssg=str().join(['Unsuccessful:  gdalbuildvrt',
                         '  Possible that input files not found.',
                         '  Check stderr file: ',gdalbuildvrt_stderr_filename])
        log_sig_warn(mssg, sigevent_url)
        
    # Rename MRFs
    if mrf_name != '':
        output_mrf, output_idx, output_data, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data)
        log_info_mssg(str().join(['Moving ',mrf_filename, ' to ', output_dir+output_mrf]))
        shutil.move(mrf_filename, output_dir+output_mrf)
        log_info_mssg(str().join(['Moving ',idx_filename, ' to ', output_dir+output_idx]))
        shutil.move(idx_filename, output_dir+output_idx)
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

#-------------------------------------------------------------------------------
# Activate the data by linking it into the Tiled-WMS cache directory.
#-------------------------------------------------------------------------------
'''
# Link .pjg (or ppg) into Tiled-WMS cache.
remove_file(cache_out_linkname)
os.symlink(out_filename, cache_out_linkname)
# Link .idx into Tiled-WMS cache.  This step activates the data.
remove_file(cache_idx_linkname)
os.symlink(idx_filename, cache_idx_linkname)
# List of links omitting "TTTTTTT" links.
# THIS WILL NOT WORK FOR DATA OLDER THAN YEAR 2000.
list_of_links=glob.glob(str().join([cache_dir,'*2??????_.ppg']))
list_of_links.sort(reverse=True)
most_recent_link = ""
if(len(list_of_links) > 0):
    # NOT SURE WHY THIS IS BREAKING
    most_recent_link=list_of_links[0]
if cache_out_linkname == most_recent_link:
    # Link .pjg (or .ppg) to the link of the most recent data.
    remove_file(cache_out_ttttttt)
    os.symlink(out_filename, cache_out_ttttttt)
    # Link .idx to the link of the most recent data.
    remove_file(cache_idx_ttttttt)
    os.symlink(idx_filename, cache_idx_ttttttt)
    
# Send to log.
log_info_mssg_with_timestamp(str().join(['MRF activated:  ', 
                                         cache_out_linkname]))
'''