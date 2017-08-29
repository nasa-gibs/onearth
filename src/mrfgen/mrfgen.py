#!/bin/env python

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
#  <mrf_empty_tile_filename>/mrfgen/empty_tiles/Blank_RGB_512.jpg</mrf_empty_tile_filename>
#  <mrf_blocksize>512</mrf_blocksize>
#  <mrf_compression_type>JPEG</mrf_compression_type>
#  <outsize>327680 163840</outsize>
#  <overview_levels>2 4 8 16 32 64 128 256 512 1024</overview_levels>
#  <overview_resampling>nearest</overview_resampling>
#  <target_epsg>4326</target_epsg>
#  <extents>-180,-90,180,90</extents>
#  <colormap></colormap>
#  <mrf_name>{$parameter_name}%Y%j_.mrf</mrf_name>
#  <mrf_nocopy>true</mrf_nocopy>
#  <mrf_merge>false</mrf_merge>
# </mrfgen_configuration>
#
# Global Imagery Browse Services / Physical Oceanography Distributed Active Archive Center (PO.DAAC)
# NASA Jet Propulsion Laboratory
# 2016
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
import math
from overtiffpacker import pack
from decimal import *

versionNumber = '1.3.1'
basename = None

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
    if basename != None:
        data['data']=basename
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
        
def log_sig_err(mssg, sigevent_url):
    """
    Send an error to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(time.asctime())
    logging.warning(mssg)
    # Send to sigevent.
    try:
        sent=sigevent('ERROR', mssg, sigevent_url)
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

def remove_file(filename):
    """
    Delete a file or link, and report this action to the log.
    Arguments:
        filename -- file to remove.
    """
    preexisting=glob.glob(filename)
    if len(preexisting) > 0:
        # Send to log.
        if os.path.islink(filename):
            log_info_mssg(str().join(['Removing link:  ', filename]))
        else:
            log_info_mssg(str().join(['Removing file:  ', filename]))
        os.remove(filename)

def check_abs_path(directory_path):
    """
    Check if directory is absolute path.
    If not, prepend current working directory.
        Argument:
            directory_path -- path to check if absolute
    """
    # Check if already cwd
    if directory_path[:2] == './':
        directory_path = directory_path[2:]
    
    # Convert relative path to absolute
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
        directory_path = str().join([directory_path, '/'])
        
    # Make sure there are no double slashes anywhere
    directory_path = directory_path.replace('//', '/')
    
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
            files.append(check_abs_path(element.firstChild.data.strip()))
    else:
        files.append(check_abs_path(input_file_element.firstChild.data.strip())) 
    return ",".join(files)

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
    """
    Compares images within a list for different image resolutions
    Arguments:
        tiles -- List of images for comparison.
    """
    next_x = 0
    if len(tiles) <= 1:
        log_info_mssg("Single tile detected")
        return (False, next_x)
    
    log_info_mssg("Checking for different resolutions in tiles")
    res = ""
    for tile in tiles:
        gdalinfo_command_list=['gdalinfo', tile]
        gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for line in gdalinfo.stdout.readlines():
            if "Pixel Size =" in line:
                if res == "":
                    res = line.split("=")[1].strip()
                    log_info_mssg("Input tile pixel size is: " + res)
                    res_x = float(res.split(',')[0].replace('(',''))
                    res_y = float(res.split(',')[1].replace(')',''))
                else:
                    next_res = line.split("=")[1].strip()
                    next_x = float(next_res.split(',')[0].replace('(',''))
                    next_y = float(next_res.split(',')[1].replace(')',''))
                    if res_x != next_x and res_y != next_y:
                        log_info_mssg("Different tile resolutions detected")
                        return (True, next_x)              
    return (False, next_x)

def is_global_image(tile, xmin, ymin, xmax, ymax):
    """
    Test if input tile fills entire extent
    Argument:
        tile -- Tile to test
        xmin -- Minimum x value
        ymin -- Minimum y value
        xmax -- Maximum x value
        ymax -- Maximum y value
    """
    log_info_mssg("Checking for global image")
    upper_left = False
    lower_right = False
    gdalinfo_command_list=['gdalinfo', tile]
    gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for line in gdalinfo.stdout.readlines():
        if "Upper Left" in line:
            in_xmin,in_ymax = line.replace("Upper Left","").replace("(","").replace(")","").split(",")[:2]
            if int(round(float(in_xmin.strip()))) <= int(round(float(xmin))) and int(round(float(in_ymax.strip().split(' ')[0]))) >= int(round(float(ymax))):
                upper_left = True
        if "Lower Right" in line:
            in_xmax,in_ymin = line.replace("Lower Right","").replace("(","").replace(")","").split(",")[:2]
            if int(round(float(in_xmax.strip()))) >= int(round(float(xmax))) and int(round(float(in_ymin.strip().split(' ')[0]))) <= int(round(float(ymin))):
                lower_right = True
    if upper_left == True and lower_right == True:
        log_info_mssg(tile + " is a global image")
        return True
    else:
        return False
    
def is_granule_image(tile):
    """
    Test if input tile is a granule image
    Argument:
        tile -- Tile to test
    """
    log_info_mssg("Checking for granule image")
    is_granule = False
    gdalinfo_command_list=['gdalinfo', tile]
    gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for line in gdalinfo.stdout.readlines():
        if "Size is " in line:
            x, y = line.replace("Size is ","").split(",")[:2]
            if int(x) != int(y):
                is_granule = True
        if "Upper Left" in line:
            in_xmin,in_ymax = line.replace("Upper Left","").replace("(","").replace(")","").split(",")[:2]
            ulx = in_xmin.strip()
            uly = in_ymax.strip().split(' ')[0]
        if "Lower Right" in line:
            in_xmax,in_ymin = line.replace("Lower Right","").replace("(","").replace(")","").split(",")[:2]
            lrx = in_xmax.strip()
            lry = in_ymin.strip().split(' ')[0]
    try:
        log_info_mssg((tile + " is NOT a granule image", tile + " is a granule image")[is_granule])
        return (is_granule, [ulx, uly, lrx, lry])
    except:
        log_sig_exit('ERROR', "Error reading " + tile, sigevent_url)
        
def has_color_table(tile):
    """
    Test if input tile has a color table
    Argument:
        tile -- Tile to test
    """
    log_info_mssg("Checking for color table in " + tile)
    has_color_table = False
    gdalinfo_command_list=['gdalinfo', tile]
    gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for line in gdalinfo.stdout.readlines():
        if "Color Table" in line:
            has_color_table = True
    log_info_mssg(("No color table found","Color table found in image")[has_color_table])
    return has_color_table

def granule_align(extents, xmin, ymin, xmax, ymax, target_x, target_y, mrf_blocksize):
    """
    Aligns granule image to fit in a MRF block
    Arguments:
        extents -- spatial extents as ulx, uly, lrx, lry
        xmin -- Minimum x value
        ymin -- Minimum y value
        xmax -- Maximum x value
        ymax -- Maximum y value
        target_x -- The target resolution for x
        target_y -- The target resolution for y
        mrf_blocksize -- The block size of MRF tiles
    """
    extents = [Decimal(x) for x in extents]
    ulx, uly, lrx, lry = extents
    x_len = abs(Decimal(xmax)-Decimal(xmin))
    y_len = abs(Decimal(ymax)-Decimal(ymin))
    x_res = Decimal(target_x)/x_len
    y_res = Decimal(target_y)/y_len
    x_size = abs(lrx-ulx) * x_res
    y_size = abs(lry-uly) * y_res
    x_pixelsize = (Decimal(xmax)-Decimal(xmin))/Decimal(target_x)
    y_pixelsize = (Decimal(ymin)-Decimal(ymax))/Decimal(target_y)
    log_info_mssg ("x-res: " + str(x_res) + ", y-res: " + str(y_res) + ", x-size: " + str(x_size) + ", y-size: " + str(y_size) + ", x-pixelsize: " + str(x_pixelsize) + ", y-pixelsize: " + str(y_pixelsize))

    # figure out appropriate block size that covers extent of granule    
    block_x = Decimal(mrf_blocksize)
    block_y = Decimal(mrf_blocksize)
    while (block_x*2) < x_size:
        block_x = block_x * 2
    while (block_y*2) < y_size:
        block_y = block_y * 2
    block = Decimal(str(max([block_x,block_y])))
    
    log_info_mssg("Insert block size %s - (x: %s y: %s)" % (str(block), str(block_x), str(block_y)))
    
    # calculate new extents that align with MRF blocks
    ulx = Decimal(Decimal(str(math.floor((ulx*x_res) / block))) * block) / x_res
    uly = Decimal(Decimal(str(math.ceil((uly*y_res) / block))) * block) / y_res
    lrx = Decimal(Decimal(str(math.ceil((lrx*x_res) / block))) * block) / x_res
    lry = Decimal(Decimal(str(math.floor((lry*y_res) / block))) * block) / y_res

    # snap to min/max extents if on the edge
    if ulx < Decimal(xmin):
        ulx = xmin
    if uly > Decimal(ymax):
        uly = ymax
    if lrx > Decimal(xmax):
        lrx = str(Decimal(xmax) - x_pixelsize)
    if lry < Decimal(ymin):
        lry = str(Decimal(ymin) - y_pixelsize)
            
    return (str(ulx), str(uly), str(lrx), str(lry))

def gdalmerge(mrf, tile, extents, target_x, target_y, mrf_blocksize, xmin, ymin, xmax, ymax, nodata, resize_resampling, working_dir, target_epsg):
    """
    Runs gdalmerge and returns merged tile
    Arguments:
        mrf -- An existing MRF file
        tile -- Tile to insert
        extents -- spatial extents as ulx, uly, lrx, lry
        target_x -- The target resolution for x
        target_y -- The target resolution for y
        mrf_blocksize -- The block size of MRF tiles
        xmin -- Minimum x value
        ymin -- Minimum y value
        xmax -- Maximum x value
        ymax -- Maximum y value
        nodata -- nodata value
        resize_resampling -- resampling method; nearest is used for PPNG
        working_dir -- Directory to use for temporary files
        target_epsg -- EPSG code for output tile
    """
    if resize_resampling == '':
        resize_resampling = "average" # use average as default for RGBA
    ulx, uly, lrx, lry = granule_align(extents, xmin, ymin, xmax, ymax, target_x, target_y, mrf_blocksize)
    new_tile = working_dir + os.path.basename(tile)+".blend.tif"
    if has_color_table(tile) == True:
        gdal_merge_command_list = ['gdal_merge.py', '-ul_lr', ulx, uly, lrx, lry, '-ps', str((Decimal(xmax)-Decimal(xmin))/Decimal(target_x)), str((Decimal(ymin)-Decimal(ymax))/Decimal(target_y)), '-o', new_tile, '-of', 'GTiff', '-pct']
        if nodata != "":
            gdal_merge_command_list.append('-n')
            gdal_merge_command_list.append(nodata)
        gdal_merge_command_list.append(mrf)
        gdal_merge_command_list.append(tile)
    else: # use gdalbuildvrt/gdalwarp/gdal_translate for RGBA imagery
        
        # Build a VRT, adding SRS to the input. Technically, if this is a TIF we wouldn't have to do that
        vrt_tile = working_dir + os.path.basename(tile) + ".vrt"
        gdal_vrt_command_list = ['gdalbuildvrt', '-a_srs', target_epsg, vrt_tile, tile]
        log_the_command(gdal_vrt_command_list)
        gdal_vrt = subprocess.Popen(gdal_vrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        insert_message = gdal_vrt.stderr.readlines()
        for message in insert_message:
            if 'ERROR' in message.upper():
                log_sig_err(message + ' in merging image (gdalbuildvrt) while processing ' + tile, sigevent_url)
            else:
                log_info_mssg(message.strip())
        gdal_vrt.wait()
        
        # Warp the input image VRT to have the right resolution
        warp_vrt_tile = working_dir + os.path.basename(tile) + ".warp.vrt"
        gdal_warp_command_list = ['gdalwarp', '-of', 'VRT', '-tr', str((Decimal(xmax)-Decimal(xmin))/Decimal(target_x)), str((Decimal(ymin)-Decimal(ymax))/Decimal(target_y)), vrt_tile, warp_vrt_tile]
        log_the_command(gdal_warp_command_list)
        gdal_warp = subprocess.Popen(gdal_warp_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        insert_message = gdal_warp.stderr.readlines()
        for message in insert_message:
            if 'ERROR' in message.upper():
                log_sig_err(message + ' in merging image (gdalwarp) while processing ' + tile, sigevent_url)
            else:
                log_info_mssg(message.strip())
        gdal_warp.wait()
        
        # Now build a combined VRT for both the input VRT and the MRF
        combined_vrt_tile = working_dir + os.path.basename(tile) + ".combined.vrt"
        gdal_vrt_command_list2 = ['gdalbuildvrt', combined_vrt_tile, mrf, warp_vrt_tile]
        log_the_command(gdal_vrt_command_list2)
        gdal_vrt2 = subprocess.Popen(gdal_vrt_command_list2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        insert_message = gdal_vrt2.stderr.readlines()
        for message in insert_message:
            if 'ERROR' in message.upper():
                log_sig_err(message + ' in merging image (gdalbuildvrt - 2) while processing ' + tile, sigevent_url)
            else:
                log_info_mssg(message.strip())
        gdal_vrt2.wait()

        # Create a merged VRT containing only the portion of the combined VRT we will insert back into the MRF
        new_tile = working_dir + os.path.basename(tile)+".merge.vrt"
        gdal_merge_command_list = ['gdal_translate', '-outsize', str(int(round((Decimal(lrx)-Decimal(ulx))/((Decimal(xmax)-Decimal(xmin))/Decimal(target_x))))), str(int(round((Decimal(lry)-Decimal(uly))/((Decimal(ymin)-Decimal(ymax))/Decimal(target_y))))), '-projwin', ulx, uly, lrx, lry, '-of', 'VRT', combined_vrt_tile, new_tile]
        
    # Execute the merge
    log_the_command(gdal_merge_command_list)
    gdal_merge = subprocess.Popen(gdal_merge_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    insert_message = gdal_merge.stderr.readlines()
    for message in insert_message:
        if 'ERROR' in message.upper():
            log_sig_err(message + ' in merging image while processing ' + tile, sigevent_url)
        else:
            log_info_mssg(message.strip())
    gdal_merge.wait()
    return new_tile

def split_across_antimeridian(tile, extents, antimeridian, xres, yres, source_epsg, target_epsg, working_dir):
    """
    Splits up a tile that crosses the antimeridian
    Arguments:
        tile -- Tile to insert
        extents -- spatial extents as ulx, uly, lrx, lry
        antimeridian -- The antimeridian for the projection
        xres -- output x resolution
        yres -- output y resolution
        working_dir -- Directory to use for temporary files
    """
    temp_tile = working_dir + os.path.basename(tile) + '.temp.vrt'
    ulx, uly, lrx, lry = extents
    if Decimal(lrx) <= Decimal(antimeridian):
        new_lrx = str(Decimal(lrx)+Decimal(antimeridian)*2)
    else:
        new_lrx = lrx
        lrx = str(Decimal(antimeridian)*-1 - (Decimal(antimeridian)-Decimal(lrx)))
    cutline_template = """
    {
      "type": "Polygon",
      "coordinates": [
        $values
      ]
    }
    """
    cutline_values = "[[{0}, {3}], [{0}, {1}], [{2}, {1}], [{2}, {3}], [{0}, {3}]]"
    cutline_left = cutline_template.replace('$values',cutline_values.format(Decimal(ulx), Decimal(uly), Decimal(antimeridian), Decimal(lry)))
    cutline_right = cutline_template.replace('$values',cutline_values.format(Decimal(antimeridian), Decimal(uly), Decimal(new_lrx), Decimal(lry)))
    
    # Create VRT of input tile
    gdalbuildvrt_command_list = ['gdalwarp', '-of', 'VRT', '-tr', xres, yres, tile, temp_tile]
    log_the_command(gdalbuildvrt_command_list)
    gdalbuildvrt = subprocess.Popen(gdalbuildvrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    gdalbuildvrt.wait()
    tile = temp_tile
    tile_left = tile+".left_cut.vrt"
    tile_right = tile+".right_cut.vrt" 
    
    if Decimal(extents[2]) <= Decimal(antimeridian):
        # modify input into >180 space if not already
        gdal_edit_command_list = ['gdal_edit.py', tile, '-a_ullr', new_lrx, uly, ulx, lry]
        log_the_command(gdal_edit_command_list)
        gdal_edit = subprocess.Popen(gdal_edit_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gdal_edit.wait()  
    
    # cut the input at the antimeridian into left and right halves
    left_cut_command_list = ['gdalwarp', '-s_srs', source_epsg, '-t_srs', target_epsg, '-of', 'VRT', '-crop_to_cutline', '-cutline', cutline_left, tile, tile_left]
    right_cut_command_list = ['gdalwarp', '-s_srs', source_epsg, '-t_srs', target_epsg, '-of', 'VRT', '-crop_to_cutline', '-cutline', cutline_right, tile, tile_right]
    log_the_command(left_cut_command_list)
    left_cut = subprocess.Popen(left_cut_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    left_cut.wait()
    left_cut_stderr = left_cut.stderr.read()
    if len(left_cut_stderr) > 0:
        log_sig_err(left_cut_stderr, sigevent_url)
    log_the_command(right_cut_command_list)
    right_cut = subprocess.Popen(right_cut_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    right_cut.wait()
    right_cut_stderr = right_cut.stderr.read()
    if len(right_cut_stderr) > 0:
        log_sig_err(right_cut_stderr, sigevent_url)
    
    # flip the origin longitude of the right half
    gdal_edit_command_list = ['gdal_edit.py', tile_right, '-a_ullr', str(Decimal(antimeridian)*-1), uly, lrx, lry]
    log_the_command(gdal_edit_command_list)
    gdal_edit = subprocess.Popen(gdal_edit_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    gdal_edit.wait()  

    return (tile_left,  tile_right)

def run_mrf_insert(mrf, tiles, insert_method, resize_resampling, target_x, target_y, mrf_blocksize, source_extents, target_extents, source_epsg, target_epsg, nodata, blend, working_dir):
    """
    Inserts a list of tiles into an existing MRF
    Arguments:
        mrf -- An existing MRF file
        tiles -- List of tiles to insert
        insert_method -- The resampling method to use {Avg, NearNb}
        resize_resampling -- The resampling method to use for gdalwarp
        target_x -- The target resolution for x
        target_y -- The target resolution for y
        mrf_blocksize -- The block size of MRF tiles
        source_extents -- Full extents of the source imagery
        target_extents -- Full extents of the target imagery
        source_epsg -- The source EPSG code
        target_epsg -- The target EPSG code
        nodata -- nodata value
        blend -- Blend over transparent regions of imagery
        working_dir -- Directory to use for temporary files
    """
    errors = 0
    xmin, ymin, xmax, ymax = target_extents
    s_xmin, s_ymin, s_xmax, s_ymax = source_extents
    if target_y == '':
        target_y = float(int(target_x)/2)
    log_info_mssg("Inserting new tiles to " + mrf)
    mrf_insert_command_list = ['mrf_insert', '-r', insert_method]
    for tile in tiles:
        if os.path.splitext(tile)[1] == ".vrt" and "_cut." not in tile: #ignore temp VRTs unless it's an antimeridian cut
            log_info_mssg("Skipping insert of " + tile)
            continue
        granule, extents = is_granule_image(tile)
        diff_res, ps = diff_resolution([tile, mrf])
        log_info_mssg("Pixel size " + repr(ps))
        # check if granule crosses antimeridian
        if ((float(extents[0])-float(s_xmax)) > float(extents[2])) or (float(extents[2]) > float(s_xmax)):
            log_info_mssg(tile + " crosses antimeridian")
            left_half, right_half = split_across_antimeridian(tile, extents, s_xmax, str((Decimal(s_xmax)-Decimal(s_xmin))/Decimal(target_x)), str((Decimal(s_ymin)-Decimal(s_ymax))/Decimal(target_y)), source_epsg, target_epsg, working_dir)
            errors += run_mrf_insert(mrf, [left_half, right_half], insert_method, resize_resampling, target_x, target_y, mrf_blocksize, source_extents, target_extents, source_epsg, target_epsg, nodata, True, working_dir)
            continue
        if blend == True and target_epsg == source_epsg: # blend tile with existing imagery if true and same projection
            log_info_mssg(("Tile","Granule")[granule] + " extents " + str(extents))
            tile = gdalmerge(mrf, tile, extents, target_x, target_y, mrf_blocksize, xmin, ymin, xmax, ymax, nodata, resize_resampling, working_dir, target_epsg)
            diff_res = False # gdalmerge has corrected the resolutions
        vrt_tile = working_dir + os.path.basename(tile)+".vrt"
        if diff_res:
            # convert tile to matching resolution
            if resize_resampling == '':
                resize_resampling = "near" # use nearest neighbor as default
            tile_vrt_command_list = ['gdalwarp', '-of', 'VRT', '-r', resize_resampling, '-overwrite', '-tr', str((Decimal(xmax)-Decimal(xmin))/Decimal(target_x)), str((Decimal(ymin)-Decimal(ymax))/Decimal(target_y))]
            if target_epsg != source_epsg:
                tile_vrt_command_list.append('-s_srs')
                tile_vrt_command_list.append(source_epsg)
                tile_vrt_command_list.append('-t_srs')
                tile_vrt_command_list.append(target_epsg)
            if is_global_image(tile, xmin, ymin, xmax, ymax) == True and len(tiles) == 1:
                tile_vrt_command_list.append('-te')
                tile_vrt_command_list.append(xmin)
                tile_vrt_command_list.append(ymin)
                tile_vrt_command_list.append(xmax)
                tile_vrt_command_list.append(ymax)
            tile_vrt_command_list.append(tile)
            tile_vrt_command_list.append(vrt_tile)
            log_the_command(tile_vrt_command_list)
            tile_vrt = subprocess.Popen(tile_vrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tile_vrt.wait()
            if blend == True and target_epsg != source_epsg: # blend tile with existing imagery after reprojection
                granule, extents = is_granule_image(vrt_tile) # get new extents
                log_info_mssg(("Tile","Granule")[granule] + " extents " + str(extents))
                tile = gdalmerge(mrf, vrt_tile, extents, target_x, target_y, mrf_blocksize, xmin, ymin, xmax, ymax, nodata, resize_resampling, working_dir, target_epsg)
                mrf_insert_command_list.append(tile)
            else:
                mrf_insert_command_list.append(vrt_tile)
        else:
            mrf_insert_command_list.append(tile)
        mrf_insert_command_list.append(mrf)
        log_the_command(mrf_insert_command_list)
        try:
            mrf_insert = subprocess.Popen(mrf_insert_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            mrf_insert_command_list.pop()
            mrf_insert_command_list.pop()
        except OSError:
            log_sig_exit('ERROR', "mrf_insert tool cannot be found.", sigevent_url)
        insert_message = mrf_insert.stderr.readlines()
        for message in insert_message:
            if 'Access window out of range' in message:
                log_sig_warn(message, sigevent_url)
            elif 'ERROR' in message:
                errors += 1
                log_sig_err('mrf_insert ' + message, sigevent_url)
            else:
                log_info_mssg(message.strip())
        # clean up      
        if ".blend." in tile:
            remove_file(tile)
            tile = tile.split('.vrt.blend.')[0]
        remove_file(vrt_tile)
    for tile in tiles:
        temp_vrt_files = glob.glob(working_dir + os.path.basename(tile) + "*vrt*")
        for vrt in temp_vrt_files:
            remove_file(vrt)
    return errors


def insert_zdb(mrf, zlevels, zkey, source_url, scale, offset, units):
    """
    Inserts a list of tiles into an existing MRF
    Argument:
        mrf -- An MRF file
        zlevels -- The number of z-levels expected
        zkey -- The key to be used with the z-index
        source_url -- The URL of the source dataset
        scale -- Scale factor for encoded data values
        offset -- Offset of encoded data values
        units -- Units for encoded data values
    """  
    log_info_mssg("Modifying zdb for " + mrf + " with key " + zkey)  
    # Check if z-dimension is consistent if it's being used
    if zlevels != '':
        try:
            # Open file.
            mrf_file=open(mrf, 'r')
        except IOError:
            mssg=str().join(['MRF not yet generated:  ', mrf])
            log_info_mssg(mssg)
        else:
            dom=xml.dom.minidom.parse(mrf_file)           
            size_elements = dom.getElementsByTagName('Size')
            sizeZ=size_elements[0].getAttribute('z') #bands
            if sizeZ == '':
                mssg = "The output MRF does not contain z-levels: " + mrf
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
    zdb_out = mrf.replace('.mrf','.zdb')
    z = None
    try:
        db_exists = os.path.isfile(zdb_out)
        log_info_mssg("Connecting to " + zdb_out)
        con = sqlite3.connect(zdb_out, timeout=1800.0) # 30 minute timeout
        
        if db_exists == False:
            cur = con.cursor()
            create_script = "CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT);"
            if source_url != "": 
                create_script = "CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT, source_url TEXT);"
            if scale != None:
                create_script = "CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT, source_url TEXT, scale INTEGER, offset INTEGER, uom TEXT);"
            try:
                cur.executescript(create_script)
                con.commit()
            except sqlite3.Error, e:
                mssg = "%s:" % e.args[0]
                if "database schema has changed" in mssg: # in case two processes attempt to create schema at once
                    log_sig_warn(mssg + zdb_out, sigevent_url)

        if zkey != '':
            is_update = False
            cur = con.cursor()
            # Check for existing key
            cur.execute("SELECT COUNT(*) FROM ZINDEX WHERE key_str='"+zkey+"';")
            lid = int(cur.fetchone()[0])
            if lid > 0:                
                mssg = zkey + " key already exists...overwriting"
                log_sig_warn(mssg, sigevent_url)
                cur.execute("SELECT z FROM ZINDEX WHERE key_str='"+zkey+"';")
                z = int(cur.fetchone()[0])
                is_update = True
            else:              
                # Check z size
                cur.execute("SELECT COUNT(*) FROM ZINDEX;")
                lid = int(cur.fetchone()[0])
                if lid >= int(zlevels):
                    mssg = str(lid+1) + " z-levels is more than the maximum allowed: " + str(zlevels)
                    log_sig_exit('ERROR', mssg, sigevent_url)
                # Insert values
                if lid == 0:
                    try:
                        cur.execute("INSERT INTO ZINDEX(z, key_str) VALUES (0,'"+zkey+"')")
                    except sqlite3.Error, e: # if 0 index has already been taken
                        log_info_mssg("%s: trying new ID" % e.args[0])
                        cur.execute("INSERT INTO ZINDEX(key_str) VALUES ('"+zkey+"')")
                else:
                    cur.execute("INSERT INTO ZINDEX(key_str) VALUES ('"+zkey+"')")
                z = cur.lastrowid
                log_info_mssg("Current z-level is " +str(z))
            if source_url != "" and source_url != "NONE":
                log_info_mssg("Adding Source URL " + source_url + " to z=" +str(z))
                cur.execute("UPDATE ZINDEX SET source_url=('"+source_url+"') WHERE z="+str(z))
            if scale != None and offset != None:
                log_info_mssg("Adding Scale:" + str(scale) + " and Offset:" + str(offset) + " to z=" +str(z))
                cur.execute("UPDATE ZINDEX SET scale=("+str(scale)+"), offset=("+str(offset)+") WHERE z="+str(z))
            if scale != None:
                log_info_mssg("Adding Units:" + units + " to z=" +str(z))
                cur.execute("UPDATE ZINDEX SET uom=('"+units+"') WHERE z="+str(z))                

            if is_update == True: # commit if updating existing z; if not, hold off commit until MRF is updated to avoid having orphan z key
                if con:
                    con.commit()
                    con.close()
                    con = None
                    log_info_mssg("Successfully committed record to " + zdb_out)
        
    except sqlite3.Error, e:
        if con:
            con.rollback()
            con.close()
            con = None
        mssg = "%s:" % e.args[0]
        if "database is locked" in mssg or "no such table" in mssg:
            log_sig_warn(mssg + " retrying connection to " + zdb_out, sigevent_url)
            return insert_zdb(mrf, zlevels, zkey)
        else:
            log_sig_exit('ERROR', mssg, sigevent_url)
        
    # Use specific z if appropriate
    if z != None:
        gdal_mrf_filename = mrf + ":MRF:Z" + str(z)
    else:
        gdal_mrf_filename = mrf

    return (gdal_mrf_filename, z, zdb_out, con)


def create_vrt(basename, empty_tile, epsg, xmin, ymin, xmax, ymax):
    """
    Generates an empty VRT for a blank MRF
    Arguments:
        basename -- The base filename
        empty_tile -- The empty tile filename
        epsg -- The projection EPSG code 
        xmin -- Minimum x value
        ymin -- Minimum y value
        xmax -- Maximum x value
        ymax -- Maximum y value
    """  
    # copy empty tile and generate world file
    new_empty_tile = basename + "_empty" + os.path.splitext(empty_tile)[1]
    shutil.copy(empty_tile, new_empty_tile)
    try:
        empty_world=open(basename + "_empty.wld", 'w+')
    except IOError:
        mssg=str().join(['Cannot open world file: ', basename + "_empty.wld"])
        log_sig_exit('ERROR', mssg, sigevent_url)
        
    xres = (float(xmax) - float(xmin)) / 512
    yres = ((float(ymax) - float(ymin)) / 512) * -1
    xul = float(xmin) + (xres/2)
    yul = float(ymax) + (yres/2)
    world_lines = "%s\n0.000000000000\n0.000000000000\n%s\n%s\n%s" % (xres,yres,xul,yul)
    empty_world.write(world_lines)
    empty_world.close()
    
    # generate VRT with new empty tile
    empty_vrt_filename = basename + "_empty.vrt"
    log_info_mssg("Generating empty VRT as input " + empty_vrt_filename)
    gdalbuildvrt_command_list=['gdalbuildvrt', '-te', xmin, ymin, xmax, ymax,'-a_srs', epsg, empty_vrt_filename, new_empty_tile]
    log_the_command(gdalbuildvrt_command_list)
    gdalbuildvrt_stderr_filename=str().join([basename, '_gdalbuildvrt_empty_stderr.txt'])
    gdalbuildvrt_stderr_file=open(gdalbuildvrt_stderr_filename, 'w')
    subprocess.call(gdalbuildvrt_command_list, stderr=gdalbuildvrt_stderr_file)
    
    # remove empty tile from vrt
    try:
        empty_vrt=open(empty_vrt_filename, 'r+')
    except IOError:
        mssg=str().join(['Cannot open empty vrt: ', empty_vrt_filename])
        log_sig_exit('ERROR', mssg, sigevent_url)
        
    dom = xml.dom.minidom.parse(empty_vrt)
    bands = dom.getElementsByTagName("VRTRasterBand")
    for band in bands:
        for i, node in enumerate(band.childNodes):
            if node.nodeName == "SimpleSource":
                band.removeChild(band.childNodes[i])
    empty_vrt.seek(0)
    empty_vrt.truncate()
    dom.writexml(empty_vrt)
    empty_vrt.close()
    
    # cleanup
    remove_file(new_empty_tile)
    remove_file(basename + "_empty.wld")
    remove_file(gdalbuildvrt_stderr_filename)

    return empty_vrt_filename


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

# Get current time, which is written to a file as the previous cycle time.  
# Time format is "yyyymmdd.hhmmss.f".  Do this first to avoid any gap where tiles 
# may get passed over because they were created while this script is running.
current_cycle_time = datetime.datetime.now().strftime("%Y%m%d.%H%M%S.%f")

errors = 0

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

    # Define output basename for log, txt, vrt, .mrf, .idx and .ppg or .pjg
    # Files get date_of_date added, links do not.
    basename=str().join([parameter_name, '_', date_of_data, '___', 'mrfgen_', current_cycle_time, '_', str(os.getpid())])    
    
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
        working_dir = add_trailing_slash(check_abs_path(working_dir))
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
        if input_files == '':
            raise ValueError('No input files provided')
    except:
        if input_dir == None:
            if mrf_empty_tile_filename != '':
                input_files = create_vrt(add_trailing_slash(check_abs_path(working_dir))+basename, mrf_empty_tile_filename, target_epsg, xmin, ymin, xmax, ymax)
            else:
                log_sig_exit('ERROR', "<input_files> or <input_dir> or <mrf_empty_tile_filename> is required", sigevent_url)
        else:
            input_files = ''
    # overview levels
    try:
        overview_levels       =get_dom_tag_value(dom, 'overview_levels').split(' ')
        for level in overview_levels:
            if level.isdigit() == False:
                log_sig_exit("ERROR", "'" + level + "' is not a valid overview value.", sigevent_url)
        if len(overview_levels>1):
            overview = overview_levels[1]/overview_levels[0]
        else:
            overview = 2
    except:
        overview_levels = ''
        overview = 2
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
    # quality/precision
    try:
        quality_prec = get_dom_tag_value(dom, 'quality_prec')
    except:
        if mrf_compression_type.lower() == 'lerc':
            quality_prec = '0.001' # default to standard floating point precision if LERC
        else:
            quality_prec = '80' # default to 80 quality for everything else
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
    # nocopy, defaults to True if not global
    try:
        if get_dom_tag_value(dom, 'mrf_nocopy') == "false":
            nocopy = False
        else:
            nocopy = True
    except:
        nocopy = None
    # blend, defaults to False
    try:
        if get_dom_tag_value(dom, 'mrf_merge') == "false":
            blend = False
        else:
            blend = True
    except:
        blend = False
    # mrf data
    try:
        mrf_data_scale = get_dom_tag_value(dom, 'mrf_data_scale')
    except:
        mrf_data_scale = '' 
    try:
        mrf_data_offset = get_dom_tag_value(dom, 'mrf_data_offset')
    except:
        mrf_data_offset = '' 
    if mrf_data_scale != '' and mrf_data_offset == '':
        log_sig_exit('ERROR', "<mrf_data_offset> is required if <mrf_data_scale> is set", sigevent_url)
    if (mrf_data_scale == '' and mrf_data_offset != ''):
        log_sig_exit('ERROR', "<mrf_data_scale> is required if <mrf_data_offset> is set", sigevent_url)
    try:
        mrf_data_units = get_dom_tag_value(dom, 'mrf_data_units')
    except:
        mrf_data_units = ''
    try:
        source_url = get_dom_tag_value(dom, 'source_url')
    except:
        if len(dom.getElementsByTagName('source_url')) > 0:
            source_url = "NONE"
        else:
            source_url = ''    
    # Close file.
    config_file.close()

# Make certain each directory exists and has a trailing slash.
if input_dir != None:
    input_dir = add_trailing_slash(check_abs_path(input_dir))
output_dir = add_trailing_slash(check_abs_path(output_dir))
logfile_dir = add_trailing_slash(check_abs_path(logfile_dir))

# Save script_dir
script_dir = add_trailing_slash(os.path.dirname(os.path.abspath(__file__)))

# Ensure that mrf_compression_type is uppercase.
mrf_compression_type=string.upper(mrf_compression_type)

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

# Make certain color map can be found
if colormap != '' and '://' not in colormap:
     colormap = check_abs_path(colormap)

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
log_info_mssg(str().join(['config quality_prec:            ', quality_prec]))
log_info_mssg(str().join(['config mrf_nocopy:              ', str(nocopy)]))
log_info_mssg(str().join(['config mrf_merge:               ', str(blend)]))
log_info_mssg(str().join(['config mrf_z_levels:            ', zlevels]))
log_info_mssg(str().join(['config mrf_z_key:               ', zkey]))
log_info_mssg(str().join(['config mrf_data_scale:          ', mrf_data_scale]))
log_info_mssg(str().join(['config mrf_data_offset:         ', mrf_data_offset]))
log_info_mssg(str().join(['config mrf_data_units:          ', mrf_data_units]))
log_info_mssg(str().join(['config source_url:              ', source_url]))
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
    if mrf_empty_tile_what != 'png' and mrf_empty_tile_what != 'jpeg' and mrf_empty_tile_what != 'tiff' and mrf_empty_tile_what != 'lerc':
        mssg='Empty tile image format must be either png, jpeg, tiff, or lerc.'
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

# Declare scale, offset, and units
scale = None
offset = None
units = None

# Get list of all tile filenames.
alltiles = []
if input_files != '':
    input_files = input_files.strip()
    alltiles = input_files.split(',')
if input_dir != None:
    if mrf_compression_type.lower() == 'jpeg' or mrf_compression_type.lower() == 'jpg':
        alltiles = alltiles + glob.glob(str().join([input_dir, '*.jpg']))
    else:
        alltiles = alltiles + glob.glob(str().join([input_dir, '*.png']))
    # check for tiffs
    alltiles = alltiles + glob.glob(str().join([input_dir, '*.tif']))
    alltiles = alltiles + glob.glob(str().join([input_dir, '*.tiff']))

striptiles = []
for tile in alltiles:
    striptiles.append(tile.strip())
alltiles = striptiles

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
        if ".mrf" in tile or ".vrt" in tile: # ignore MRF and VRT
            goodtiles.append(tile)
        else:
            # Execute identify.
            try:
                identify_process = subprocess.Popen(identify_command_list, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                identify_process.wait()
                if 'DirectClass' in identify_process.stdout.readlines()[0]:
                    goodtiles.append(tile)
                else:
                    errors += 1
                    log_sig_err('Bad JPEG tile detected: ' + tile, sigevent_url)
            except OSError:
                if i==0:
                    log_sig_warn('identify command not found, unable to detect bad JPEG tiles', sigevent_url)
                goodtiles.append(tile)
            except IndexError:
                log_sig_exit('ERROR', 'Invalid input files', sigevent_url)
    alltiles = goodtiles       

# Convert RGBA PNGs to indexed paletted PNGs if requested
if mrf_compression_type == 'PPNG' and colormap != '':
    for i, tile in enumerate(alltiles):
        temp_tile = None
        tile_path = os.path.dirname(tile)
        tile_basename, tile_extension = os.path.splitext(os.path.basename(tile))
        
        # Check input PNGs/TIFFs if RGBA, then convert       
        if tile.lower().endswith(('.png', '.tif', '.tiff')):
            
            # Run the gdal_info on tile.
            gdalinfo_command_list=['gdalinfo', tile]
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            # Read gdal_info output
            if "ColorInterp=Palette" not in gdalinfo.stdout.read():
                if '.tif' in tile.lower():
                    # Convert TIFF files to PNG
                    log_info_mssg("Converting TIFF file " + tile + " to " + tiff_compress)
                       
                    # Create the gdal_translate command.
                    gdal_translate_command_list=['gdal_translate', '-q', '-of', tiff_compress, '-co', 'WORLDFILE=YES',
                                                 tile, working_dir+tile_basename+'.'+str(tiff_compress).lower()]
                    # Log the gdal_translate command.
                    log_the_command(gdal_translate_command_list)
               
                    # Execute gdal_translate.
                    subprocess.call(gdal_translate_command_list, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
                       
                    # Replace with new tiles
                    tile = working_dir+tile_basename+'.'+str(tiff_compress).lower()
                    temp_tile = tile
                
                log_info_mssg("Converting RGBA PNG to indexed paletted PNG")
                
                output_tile = working_dir + tile_basename+'_indexed.png'
                output_tile_path = os.path.dirname(output_tile)
                output_tile_basename, output_tile_extension = os.path.splitext(os.path.basename(output_tile))
                
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
                        mssg = str(RGBApng2Palpng.stderr.readlines()[-1])
                        log_sig_err("RGBApng2Palpng: " + mssg, sigevent_url)
                    errors += RGBApng2Palpng.returncode
                
                if os.path.isfile(output_tile):
                    mssg = output_tile + " created"
                    try:
                        log_info_mssg(mssg)
                        sigevent('INFO', mssg, sigevent_url)
                    except urllib2.URLError:
                        print 'sigevent service is unavailable'
                    # Replace with new tiles
                    alltiles[i] = output_tile
                else:
                    errors += 1
                    log_sig_err("RGBApng2Palpng failed to create " + output_tile, sigevent_url)
                
                # Make a copy of world file
                try:
                    if os.path.isfile(tile_path+'/'+tile_basename+'.pgw'):
                        shutil.copy(tile_path+'/'+tile_basename+'.pgw', output_tile_path+'/'+output_tile_basename+'.pgw')
                    elif os.path.isfile(working_dir+'/'+tile_basename+'.wld'):
                        shutil.copy(working_dir+'/'+tile_basename+'.wld', output_tile_path+'/'+output_tile_basename+'.pgw')
                    else:
                        log_info_mssg("World file does not exist for tile: " + tile)
                except:
                    errors += 1
                    log_sig_err("ERROR: " + mssg, sigevent_url)
                    
                # add transparency flag for custom color map
                add_transparency = True
            else:
                log_info_mssg("Paletted image verified")

        # remove tif temp tiles
        if temp_tile != None:
            remove_file(temp_tile)
            remove_file(temp_tile+'.aux.xml')
            remove_file(temp_tile.split('.')[0]+'.wld')     

# Create an encoded PNG from GeoTIFF
if mrf_compression_type == 'EPNG':
    scale = 0
    offset = 0
    units = mrf_data_units
    for i, tile in enumerate(alltiles):
        tile_path = os.path.dirname(tile)
        tile_basename, tile_extension = os.path.splitext(os.path.basename(tile))
        output_tile = working_dir+tile_basename+'.png'
        # Check if input is TIFF      
        if tile.lower().endswith(('.tif', '.tiff')):
            # Get Scale and Offset from gdalinfo
            gdalinfo_command_list = ['gdalinfo', tile]    
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            gdalinfo_out = gdalinfo.stdout.readlines()
            if "Color Table" in ''.join(gdalinfo_out):
                log_sig_warn(tile + " contains a palette", sigevent_url)
                mrf_compression_type = 'PPNG'
            if "Offset:" in ''.join(gdalinfo_out) and "Scale:" in ''.join(gdalinfo_out):
                log_info_mssg(tile + " is already an encoded TIFF")
            else: # Encode the TIFF file
                encoded_tile = working_dir+tile_basename+'_encoded.tif'
                log_info_mssg(tile + " will be encoded as " + encoded_tile)
                if mrf_data_scale != '' and mrf_data_offset != '':
                    scale_offset = [float(mrf_data_scale), float(mrf_data_offset)]
                else:
                    scale_offset = None
                pack(tile, encoded_tile, False, True, None, None, scale_offset, False)
                tile = encoded_tile
                gdalinfo_command_list = ['gdalinfo', tile]    
                log_the_command(gdalinfo_command_list)
                gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                gdalinfo_out = gdalinfo.stdout.readlines()
            log_info_mssg("Reading scale and offset from bands")
            for line in gdalinfo_out:
                if "Offset:" in line and "Scale:" in line:
                    offset,scale = line.strip().replace("Offset: ","").replace("Scale:","").split(",")
                    log_info_mssg("Offset: " + offset + ", Scale: " + scale)
                    scale = int(scale)
                    offset = int(offset)
            gdalinfo_stderr = gdalinfo.stderr.read()
            if len(gdalinfo_stderr) > 0:
                log_sig_err(gdalinfo_stderr, sigevent_url)
                        
            # Convert the tile to PNG
            gdal_translate_command_list = ['gdal_translate', '-of', 'PNG', tile, output_tile]    
            log_the_command(gdal_translate_command_list)
            gdal_translate = subprocess.Popen(gdal_translate_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            gdal_translate_stderr = gdal_translate.stderr.read()
            if len(gdal_translate_stderr) > 0:
                log_sig_err(gdal_translate_stderr, sigevent_url)
            alltiles[i] = output_tile  

# sort
alltiles.sort()

# check for different resolutions
diff_res, res = diff_resolution(alltiles)

# determine if nocopy should be used if not set
if nocopy == None:
    if len(alltiles) == 1 and alltiles[0].endswith('.vrt') == False:
        if is_global_image(alltiles[0],xmin, ymin, xmax, ymax) == True:
            # Don't do inserts if we have a single global image
            nocopy = False
        else:
            nocopy = True
    elif len(alltiles) == 1 and alltiles[0].endswith('empty.vrt') == True: #empty VRT, use nocopy
        nocopy = True
    else:
        if (res*8) < (float(mrf_blocksize)/float(target_x)):
            # Avoid inserts if the target MRF resolution is too low
            nocopy = False
        elif source_epsg != target_epsg:
            # Avoid inserts if reprojecting
            nocopy = False
        else:
            nocopy = True
    log_info_mssg("Setting MRF nocopy to " + str(nocopy)) 

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

# The image component of MRF is .pjg, .ppg, .ptf, or lrc depending on compression type.
if mrf_compression_type == 'PNG' or mrf_compression_type == 'PPNG' or mrf_compression_type == 'EPNG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ppg'])
elif mrf_compression_type == 'JPG' or mrf_compression_type == 'JPEG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.pjg'])
elif mrf_compression_type == 'TIF' or mrf_compression_type == 'TIFF':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ptf'])
elif mrf_compression_type == 'LERC':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.lrc'])
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
if overview_resampling[:4].lower() == 'near':
    insert_method = 'NearNb'
else:
    insert_method = 'Avg'
for tile in list(alltiles):
    if '.mrf' in tile.lower():
        mrf_list.append(tile)
        alltiles.remove(tile)
if len(mrf_list) == 0 and input_files == '':
    mrf_list = glob.glob(str().join([input_dir, '*.mrf']))
# Should only be one MRF, so use that one
if len(mrf_list) > 0:
    mrf = mrf_list[0]
    timeout = time.time() + 30 # 30 second timeout if MRF is still being generated
    while os.path.isfile(mrf) == False:
        mssg=str().join([mrf, ' does not exist'])
        if time.time() > timeout:
            log_sig_exit('ERROR', mssg, sigevent_url)
            break
        log_sig_warn(mssg + ", waiting 5 seconds...", sigevent_url)
        time.sleep(5)
        
    # Check if zdb is used
    if zlevels != '':
        mrf, z, zdb_out, con = insert_zdb(mrf, zlevels, zkey, source_url, scale, offset, units)
        if con:
            con.commit()
            con.close()
            log_info_mssg("Successfully committed record to " + zdb_out)
        else:
            log_info_mssg("No ZDB record created")
    else:
        con = None
        
    errors += run_mrf_insert(mrf, alltiles, insert_method, resize_resampling, target_x, target_y, mrf_blocksize, [xmin, ymin, xmax, ymax], [target_xmin, target_ymin, target_xmax, target_ymax], source_epsg, target_epsg, vrtnodata, blend, working_dir)
    
    # Clean up
    remove_file(all_tiles_filename)

    # Exit here since we don't need to build an MRF from scratch
    mssg=str().join(['MRF updated:  ', mrf])
    try:
        log_info_mssg(mssg)
        sigevent('INFO', mssg, sigevent_url)
    except urllib2.URLError:
        None
    sys.exit(errors)
    
  
# Use zdb index if z-levels are defined
if zlevels != '':
    mrf_filename, idx_filename, out_filename, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data, time_of_data)
    mrf_filename = output_dir + mrf_filename
    idx_filename = output_dir + idx_filename
    out_filename = output_dir + out_filename
    gdal_mrf_filename, z, zdb_out, con = insert_zdb(mrf_filename, zlevels, zkey, source_url, scale, offset, units)
    # Commit database if successful
    if con:
        con.commit()
        con.close()
        log_info_mssg("Successfully committed record to " + zdb_out)
    else:
        log_info_mssg("No ZDB record created")
else:
    con = None
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
if diff_res == True and target_x != '':
    xres = repr(abs((float(xmax)-float(xmin))/float(target_x)))
    if target_y != '':
        yres = repr(abs((float(ymin)-float(ymax))/float(target_y)))
    else:
        yres = xres
    log_info_mssg("x resolution: " + xres + ", y resolution: " + yres)
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
    gdalbuildvrt_command_list.append('-srcnodata')
    gdalbuildvrt_command_list.append(vrtnodata)
    
# add VRT filename at the end        
gdalbuildvrt_command_list.append(vrt_filename)
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
        target_y = str(int(target_x)/2)
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
if mrf_compression_type == 'PNG' or mrf_compression_type == 'EPNG':
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
elif mrf_compression_type == 'LERC':
    compress=str('COMPRESS=LERC')
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
    log_info_mssg(colormap2vrt_stderr)
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
    if target_y == '':
        target_y=str(int(float(target_x)*(float(y_size)/float(x_size))))
        log_info_mssg('Calculating target_y ' + target_y)
    if resize_resampling == '':
        log_sig_warn('Target size (' + target_x + 'x' + target_y + ') differs from input size (' + x_size + 'x' + y_size + ')' + ', but <resize_resampling> flag has not been set.', sigevent_url)
else: #don't bother calculating y
    if target_y == '':
        target_y=y_size
        log_info_mssg('Setting target_y from VRT to ' + target_y)
    elif target_y != y_size:
        log_sig_warn('Target y size (' + target_y +') differs from raster y size (' + y_size + ')', sigevent_url)
    
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
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('QUALITY='+quality_prec)
if compress == "COMPRESS=LERC":
    # Default to V1 for Javascript decoding
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('OPTIONS="LERC_PREC=' + quality_prec + ' V1=ON DEFLATE=ON"')
if zlevels != '':
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('ZSIZE='+str(zlevels))
if nocopy == True:
    gdal_translate_command_list.append('-co')
    gdal_translate_command_list.append('NOCOPY=true')
    if len(alltiles) <= 1: # use UNIFORM_SCALE if empty MRF or single input
        gdal_translate_command_list.append('-co')
        gdal_translate_command_list.append('UNIFORM_SCALE='+str(overview))
        
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
    mrf_file=open(mrf_filename, 'r+')
except IOError:
    mssg=str().join(['Cannot read:  ', mrf_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
else:
    try:
        dom=xml.dom.minidom.parse(mrf_file)
    except:
        mssg=str().join(['Cannot parse:  ', mrf_filename])
        log_sig_exit('ERROR', mssg, sigevent_url)
    # Raster
    size_elements=dom.getElementsByTagName('Size')
    sizeX=size_elements[0].getAttribute('x') #width
    sizeY=size_elements[0].getAttribute('y') #height
    sizeC=size_elements[0].getAttribute('c') #bands
    sizeZ=size_elements[0].getAttribute('z') #bands
    # Send to log.
    log_info_mssg(str().join(['size of MRF:  ', sizeX, ' x ', sizeY]))
    
    # Add mp_safe to Raster if using z levels
    if zlevels != '':
        mrf_file.seek(0)
        lines = mrf_file.readlines()
        for idx in range(0, len(lines)):
            if '<Raster>' in lines[idx]:
                lines[idx] = lines[idx].replace('<Raster>','<Raster mp_safe="on">')
                log_info_mssg("Set MRF mp_safe on")
        mrf_file.seek(0)
        mrf_file.truncate()
        mrf_file.writelines(lines)
    
    # Close file.
    mrf_file.close()
    # Get largest dimension, usually X.
    actual_size=max([int(sizeX), int(sizeY)])

# Run gdaladdo by default
run_addo = True

# Insert into nocopy
if nocopy==True:
    errors += run_mrf_insert(gdal_mrf_filename, alltiles, insert_method, resize_resampling, target_x, target_y, mrf_blocksize, [xmin, ymin, xmax, ymax], [target_xmin, target_ymin, target_xmax, target_ymax], source_epsg, target_epsg, vrtnodata, blend, working_dir)
    if len(alltiles) <= 1:
        run_addo = False # don't run gdaladdo if UNIFORM_SCALE has been set

# Create pyramid only if idx (MRF index file) was successfully created.
idxf=get_modification_time(idx_filename)
compare_time=time.strftime('%Y%m%d.%H%M%S', time.localtime())
old_stats=os.stat(idx_filename)
if idxf >= vrtf:
    remove_file(gdal_translate_stderr_filename)
    
    if run_addo == True and (overview_levels == '' or int(overview_levels[0])>1):
        # Create the gdaladdo command.
        gdaladdo_command_list=['gdaladdo', '-r', overview_resampling,
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
        gdaladdo_process = subprocess.Popen(gdaladdo_command_list, stdout=subprocess.PIPE, stderr=gdaladdo_stderr_file)
        out, err = gdaladdo_process.communicate()
        log_info_mssg(out)            
        #-------------------------------------------------------------------

        # Close stderr file.
        gdaladdo_stderr_file.close()

        # Update previous cycle time only if gdaladdo was successful.
        addf=get_modification_time(idx_filename)
        new_stats=os.stat(idx_filename)

        # Check for gdaladdo success by checking time stamp and file size.
        if gdaladdo_process.returncode == -11:
            log_sig_exit('ERROR', 'Unsuccessful:  gdaladdo   Segmentation fault', sigevent_url)
        elif (addf >= compare_time) or (new_stats.st_size >= old_stats.st_size):
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
            mssg=str().join(['Unsuccessful:  gdaladdo   Errors: ', str(err)])
            log_sig_exit('ERROR', mssg, sigevent_url)
else:
    log_info_mssg(str().join(['idxf = ',str(idxf)]))
    log_info_mssg(str().join(['vrtf = ',str(vrtf)]))
    log_info_mssg('idxf should be >= vrtf')
    if nocopy==True:
        mssg = mrf_filename + ' already exists'
    else:
        mssg=str().join(['Unsuccessful:  gdal_translate   ',
                         'Check the gdal mrf driver plugin.  ',
                         'Check stderr file: ',
                         gdal_translate_stderr_filename])
    log_sig_exit('ERROR', mssg, sigevent_url)
    
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

# Remove temp tiles
for tilename in (alltiles):
    if working_dir in tilename:
        remove_file(tilename)
        if tiff_compress != None:
            remove_file(tilename+'.aux.xml')
        if '_indexed.' in tilename:
            remove_file(tilename.rsplit('.',1)[0]+'.pgw')

# Send to log.
mssg=str().join(['MRF created:  ', out_filename])
try:
    log_info_mssg(mssg)
    sigevent('INFO', mssg, sigevent_url)
except urllib2.URLError:
    None
sys.exit(errors)
