#!/usr/bin/env python3

# Copyright (c) 2002-2022, California Institute of Technology.
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

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Pipeline for converting georeferenced tiles to MRF for OnEarth.
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
#  <mrf_noaddo>false</mrf_noaddo>
#  <mrf_merge>false</mrf_merge>
#  <mrf_parallel>false</mrf_parallel>
#  <mrf_cores>4</mrf_cores>
#  <mrf_clean>true</mrf_clean>
# </mrfgen_configuration>
#

from optparse import OptionParser
import glob
import logging
import os
import subprocess
import sys
import time
import urllib.parse
import xml.dom.minidom
import shutil
import imghdr
import sqlite3
import math
import oe_utils
import json
import re
from overtiffpacker import pack
from decimal import *
from osgeo import gdal
from oe_utils import basename, sigevent, log_sig_exit, log_sig_err, log_sig_warn, log_info_mssg, log_info_mssg_with_timestamp, log_the_command, get_modification_time, get_dom_tag_value, remove_file, check_abs_path, add_trailing_slash, verify_directory_path_exists, get_input_files, get_doy_string

import multiprocessing
import datetime
from contextlib import contextmanager  # used to build context pool
import functools
import random

versionNumber = os.environ.get('ONEARTH_VERSION')
oe_utils.basename = None
errors = 0


def lookupEmptyTile(empty_tile):
    """
    Lookup predefined empty tiles form config file
    """
    script_dir = os.path.dirname(__file__)
    if script_dir == '/usr/bin':
        script_dir = '/usr/share/onearth/mrfgen'  # use default directory if in bin
    try:
        empty_config_file = open(script_dir+"/empty_config", 'r')
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
        mrf_date = datetime.datetime.strptime(str(date_of_data)+str(time_of_data), "%Y%m%d%H%M%S")
    else:
        mrf_date = datetime.datetime.strptime(date_of_data, "%Y%m%d")
    mrf = mrf_name.replace('{$parameter_name}', parameter_name)
    time_params = []
    for i, char in enumerate(mrf):
        if char == '%':
            time_params.append(char+mrf[i+1])
    for time_param in time_params:
        mrf = mrf.replace(time_param, datetime.datetime.strftime(mrf_date, time_param))
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
    res = None
    for tile in tiles:
        gdalinfo_command_list = ['gdalinfo', '-json', tile]
        log_the_command(gdalinfo_command_list)
        gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        """
        returncode = gdalinfo.wait()
        if returncode != 0:
            log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
            return(False, next_x)
        tileInfo = json.loads(gdalinfo.stdout.read())
        """
        try:
            outs, errs = gdalinfo.communicate(timeout=90)
            if len(errs) > 0:
                log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
            tileInfo = json.loads(outs)

            tile_res_x = float(tileInfo["geoTransform"][1])
            tile_res_y = float(tileInfo["geoTransform"][5])

            if not res:
                log_info_mssg("Input tile pixel size is: " + str(tile_res_x) + ", " + str(tile_res_y))
                res = tile_res_x
                res_x = tile_res_x
                res_y = tile_res_y
            else:
                next_x = tile_res_x
                next_y = tile_res_y
                if res_x != next_x and res_y != next_y:
                    log_info_mssg("Different tile resolutions detected")
                    return (True, next_x)
        except subprocess.TimeoutExpired:
            gdalinfo.kill()
            log_sig_err('gdalinfo timed out', sigevent_url)

    return (False, next_x)


def is_global_image(tile, xmin, ymin, xmax, ymax):
    """
    Test if input tile fills entire extent (+/- 10 deg lat)
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

    gdalinfo_command_list = ['gdalinfo', '-json', tile]
    log_the_command(gdalinfo_command_list)
    gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    """
    returncode = gdalinfo.wait()
    if returncode != 0:
        log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
        return False
    tileInfo = json.loads(gdalinfo.stdout.read())
    """
    try:
        outs, errs = gdalinfo.communicate(timeout=90)
        if len(errs) > 0:
            log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
        tileInfo = json.loads(outs)

        in_xmin = str(tileInfo["cornerCoordinates"]["upperLeft"][0])
        in_ymax = str(tileInfo["cornerCoordinates"]["upperLeft"][1])
        in_xmax = str(tileInfo["cornerCoordinates"]["lowerRight"][0])
        in_ymin = str(tileInfo["cornerCoordinates"]["lowerRight"][1])

        if (int(round(float(in_xmin))) <= int(round(float(xmin))) and
                int(round(float(in_ymax))) >= int(round(float(ymax)-10))):
            upper_left = True
        if (int(round(float(in_xmax))) >= int(round(float(xmax))) and
                int(round(float(in_ymin))) <= int(round(float(ymin)+10))):
            lower_right = True
    except subprocess.TimeoutExpired:
        gdalinfo.kill()
        log_sig_err('gdalinfo timed out', sigevent_url)

    if upper_left and lower_right:
        log_info_mssg(tile + " is a global image")
        return True
    else:
        return False


def get_image_epsg(tile):
    """
    Get image EPSG code
    Argument:
        tile -- Tile to test
    """
    log_info_mssg("Getting image epsg")

    gdalinfo_command_list = ['gdalinfo', '-json', tile]
    log_the_command(gdalinfo_command_list)
    gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    """
    returncode = gdalinfo.wait()
    if returncode != 0:
        log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
        return None
    tileInfo = json.loads(gdalinfo.stdout.read())
    """
    epsg = None
    try:
        outs, errs = gdalinfo.communicate(timeout=90)
        if len(errs) > 0:
            log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
        tileInfo = json.loads(outs)

        wkt = tileInfo["coordinateSystem"]["wkt"]

        if wkt != "":
            lastAuth = wkt.rfind("AUTHORITY")
            if lastAuth != -1:
                m = re.search(".*EPSG.*([0-9]{4}).*", wkt[lastAuth:])
                if m:
                    epsg = "EPSG:" + m.group(1)
    except subprocess.TimeoutExpired:
        gdalinfo.kill()
        log_sig_err('gdalinfo timed out', sigevent_url)

    return epsg


def get_image_extents(tile):
    """
    Get image extents
    Argument:
        tile -- Tile to test
    """
    log_info_mssg("Getting image extents")

    gdalinfo_command_list = ['gdalinfo', '-json', tile]
    log_the_command(gdalinfo_command_list)

    gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    """
    returncode = gdalinfo.wait()
    if returncode != 0:
        log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
    try:
        tileInfo = json.loads(gdalinfo.stdout.read())
    """
    try:
        outs, errs = gdalinfo.communicate(timeout=90)
        if len(errs) > 0:
            log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
        tileInfo = json.loads(outs)

        ulx = str(tileInfo["cornerCoordinates"]["upperLeft"][0])
        uly = str(tileInfo["cornerCoordinates"]["upperLeft"][1])
        lrx = str(tileInfo["cornerCoordinates"]["lowerRight"][0])
        lry = str(tileInfo["cornerCoordinates"]["lowerRight"][1])

        return [ulx, uly, lrx, lry]

    except subprocess.TimeoutExpired:
        gdalinfo.kill()
        log_sig_err('gdalinfo timed out', sigevent_url)
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

    gdalinfo_command_list = ['gdalinfo', '-json', tile]
    log_the_command(gdalinfo_command_list)
    gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    """
    returncode = gdalinfo.wait()
    if returncode != 0:
        log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
        return False
    tileInfo = json.loads(gdalinfo.stdout.read())
    """
    try:
        outs, errs = gdalinfo.communicate(timeout=90)
        if len(errs) > 0:
            log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
        tileInfo = json.loads(outs)

        for band in tileInfo["bands"]:
            has_color_table |= "colorTable" in band

    except subprocess.TimeoutExpired:
        gdalinfo.kill()
        log_sig_err('gdalinfo timed out', sigevent_url)

    log_info_mssg(("No color table found", "Color table found in image")[has_color_table])
    return has_color_table


def mrf_block_align(extents, xmin, ymin, xmax, ymax, target_x, target_y, mrf_blocksize):
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
    log_info_mssg("x-res: " + str(x_res) + ", y-res: " + str(y_res) + ", x-size: " + str(x_size) + ", y-size: " + str(y_size))

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
        lrx = Decimal(xmax)
    if lry < Decimal(ymin):
        lry = Decimal(ymin)

    return (str(ulx), str(uly), str(lrx), str(lry))


def gdalmerge(mrf, tile, extents, target_x, target_y, mrf_blocksize, xmin, ymin, xmax, ymax, nodata,
              resize_resampling, working_dir, target_epsg):
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
        resize_resampling = "average"  # use average as default for RGBA
    ulx, uly, lrx, lry = mrf_block_align(extents, xmin, ymin, xmax, ymax, target_x, target_y, mrf_blocksize)
    new_tile = working_dir + os.path.basename(tile)+".merge.tif"

    if has_color_table(tile) is True:
        gdal_merge_command_list = ['gdal_merge.py', '-ul_lr', ulx, uly, lrx, lry, '-ps',
                                   str((Decimal(xmax)-Decimal(xmin))/Decimal(target_x)),
                                   str((Decimal(ymin)-Decimal(ymax))/Decimal(target_y)),
                                   '-o', new_tile, '-of', 'GTiff', '-pct']
        if nodata != "":
            gdal_merge_command_list.append('-n')
            gdal_merge_command_list.append(nodata)
            gdal_merge_command_list.append('-a_nodata')
            gdal_merge_command_list.append(nodata)
        gdal_merge_command_list.append(mrf)
        gdal_merge_command_list.append(tile)

    else:  # use gdalbuildvrt/gdalwarp/gdal_translate for RGBA imagery

        # Build a VRT, adding SRS to the input. Technically, if this is a TIF we wouldn't have to do that
        vrt_tile = working_dir + os.path.basename(tile) + ".vrt"
        gdal_vrt_command_list = ['gdalbuildvrt', '-a_srs', target_epsg, vrt_tile, tile]
        log_the_command(gdal_vrt_command_list)
        gdal_vrt = subprocess.Popen(gdal_vrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        insert_message = gdal_vrt.stdout.readlines()
        for message in insert_message:
            if 'ERROR' in str(message).upper():
                log_sig_err("{0} in merging image (gdalbuildvrt) while processing {1}".format(message, tile), sigevent_url)
            else:
                log_info_mssg(str(message).strip())
        returncode = gdal_vrt.wait()
        if returncode != 0:
            log_sig_err('gdalbuildvrt return code {0}'.format(returncode), sigevent_url)
            return None

        # Warp the input image VRT to have the right resolution
        warp_vrt_tile = working_dir + os.path.basename(tile) + ".warp.vrt"
        gdal_warp_command_list = ['gdalwarp', '-overwrite', '-of', 'VRT', '-tr',
                                  str((Decimal(xmax)-Decimal(xmin))/Decimal(target_x)),
                                  str((Decimal(ymin)-Decimal(ymax))/Decimal(target_y)),
                                  vrt_tile, warp_vrt_tile]
        log_the_command(gdal_warp_command_list)
        gdal_warp = subprocess.Popen(gdal_warp_command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        insert_message = gdal_warp.stdout.readlines()
        for message in insert_message:
            if 'ERROR' in str(message).upper():
                log_sig_err("{0} in merging image (gdalwarp) while processing {1}".format(message, tile), sigevent_url)
            else:
                log_info_mssg(str(message).strip())
        returncode = gdal_warp.wait()
        if returncode != 0:
            log_sig_err('gdalwarp return code {0}'.format(returncode), sigevent_url)
            return None

        # Now build a combined VRT for both the input VRT and the MRF
        combined_vrt_tile = working_dir + os.path.basename(tile) + ".combined.vrt"
        gdal_vrt_command_list2 = ['gdalbuildvrt']
        if nodata != "":
            gdal_vrt_command_list2.extend(['-vrtnodata', nodata, '-srcnodata', nodata])
        gdal_vrt_command_list2.extend([combined_vrt_tile, mrf, warp_vrt_tile])

        log_the_command(gdal_vrt_command_list2)
        gdal_vrt2 = subprocess.Popen(gdal_vrt_command_list2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        insert_message = gdal_vrt2.stdout.readlines()
        for message in insert_message:
            if 'ERROR' in str(message).upper():
                log_sig_err("{0} in merging image (gdalbuildvrt - 2) while processing {1}".format(message, tile), sigevent_url)
            else:
                log_info_mssg(str(message).strip())
        returncode = gdal_vrt2.wait()
        if returncode != 0:
            log_sig_err('gdalbuildvrt return code {0}'.format(returncode), sigevent_url)
            return None

        # Create a merged VRT containing only the portion of the combined VRT we will insert back into the MRF
        new_tile = working_dir + os.path.basename(tile)+".merge.vrt"
        gdal_merge_command_list = ['gdal_translate', '-outsize',
                                   str(int(round((Decimal(lrx)-Decimal(ulx))/((Decimal(xmax)-Decimal(xmin))/Decimal(target_x))))),
                                   str(int(round((Decimal(lry)-Decimal(uly))/((Decimal(ymin)-Decimal(ymax))/Decimal(target_y))))),
                                   '-projwin', ulx, uly, lrx, lry, '-of', 'VRT', combined_vrt_tile, new_tile]

    # Execute the merge
    log_the_command(gdal_merge_command_list)
    gdal_merge = subprocess.Popen(gdal_merge_command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    insert_message = gdal_merge.stdout.readlines()
    for message in insert_message:
        if 'ERROR' in str(message).upper():
            log_sig_err("{0} in merging image while processing {1}".format(message, tile), sigevent_url)
        else:
            log_info_mssg(str(message).strip())
    returncode = gdal_merge.wait()
    if returncode != 0: 
        log_sig_err('gdal_translate return code {0}'.format(returncode), sigevent_url)
        return None
    return new_tile


def split_across_antimeridian(tile, source_extents, antimeridian, xres, yres, working_dir):
    """
    Splits up a tile that crosses the antimeridian
    Arguments:
        tile -- Tile to insert
        source_extents -- spatial extents as ulx, uly, lrx, lry
        antimeridian -- The antimeridian for the projection
        xres -- output x resolution
        yres -- output y resolution
        working_dir -- Directory to use for temporary files
    """
    temp_tile = working_dir + os.path.basename(tile) + '.temp.vrt'
    log_info_mssg("Splitting across antimeridian with " + temp_tile)
    ulx, uly, lrx, lry = source_extents
    if Decimal(lrx) <= Decimal(antimeridian):
        # create a new lrx on the other side of the antimeridian
        new_lrx = str(Decimal(lrx)+Decimal(antimeridian)*2)
    else:
        # just use the original lrx for the right cut (left cut uses this for the ulx)
        new_lrx = lrx
        # this is the output lrx for the right cut
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
    gdalbuildvrt_command_list = ['gdalwarp', '-overwrite', '-of', 'VRT', '-tr', xres, yres, tile, temp_tile]
    log_the_command(gdalbuildvrt_command_list)
    gdalbuildvrt = subprocess.Popen(gdalbuildvrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    insert_message = gdalbuildvrt.stdout.readlines()
    err = False
    for message in insert_message:
        if 'ERROR' in str(message).upper():
            log_sig_err("{0} in building VRT (gdalwarp) while processing {1}".format(message, tile), sigevent_url)
            err = True
        else:
            log_info_mssg(str(message).strip())
    returncode = gdalbuildvrt.wait()
    if returncode != 0: 
        log_sig_err('gdalwarp return code {0}'.format(returncode), sigevent_url)
    if returncode != 0 or err:
        return (None, None)
    tile = temp_tile
    tile_left = tile + ".left_cut.vrt"
    tile_right = tile + ".right_cut.vrt"

    if Decimal(source_extents[2]) <= Decimal(antimeridian):
        # modify input into >180 space if not already
        gdal_edit_command_list = ['gdal_edit.py', tile, '-a_ullr', new_lrx, uly, ulx, lry]
        log_the_command(gdal_edit_command_list)
        gdal_edit = subprocess.Popen(gdal_edit_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = gdal_edit.wait()
        if returncode != 0: 
            log_sig_err('gdal_edit.py return code {0}'.format(returncode), sigevent_url)

    # Cut the input at the antimeridian into left and right halves

    # Make sure that when we cut the image, there will be at least one pixel on the left
    if (Decimal(antimeridian) - Decimal(ulx)) < Decimal(xres):
        log_info_mssg("Skipping left_cut for granule because the resulting image would be < 1 pixel wide")
        tile_left = None
    else:
        left_cut_command_list = ['gdalwarp', '-overwrite', '-of', 'VRT', '-crop_to_cutline', '-cutline', cutline_left, tile, tile_left]

        log_the_command(left_cut_command_list)
        left_cut = subprocess.Popen(left_cut_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = left_cut.wait()
        left_cut_stderr = left_cut.stderr.read()

        if len(left_cut_stderr) > 0:
            log_sig_err(left_cut_stderr, sigevent_url)
        if returncode != 0:
            log_sig_err('left_cut (gdalwarp) return code {0}'.format(returncode), sigevent_url)

    if tile_right.count('.right_cut.vrt') > 1:
        # Something is wrong here; prevent going into a loop
        log_sig_err("Image right_cut has already been queued for insert: {0}".format(tile_right), sigevent_url)
        tile_right = None
    elif (Decimal(new_lrx) - Decimal(antimeridian)) < Decimal(xres):
        # Make sure that when we make the right cut that there will be at least one pixel
        log_info_mssg("Skipping right_cut for granule because the resulting image would be < 1 pixel wide")
        tile_right = None
    else:
        right_cut_command_list = ['gdalwarp', '-overwrite', '-of', 'VRT', '-crop_to_cutline', '-cutline', cutline_right,
                                  tile, tile_right]
        log_the_command(right_cut_command_list)
        right_cut = subprocess.Popen(right_cut_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = right_cut.wait()
        right_cut_stderr = right_cut.stderr.read()
        if len(right_cut_stderr) > 0:
            log_sig_err(right_cut_stderr, sigevent_url)
        if returncode != 0:
            log_sig_err('right_cut (gdalwarp) return code {0}'.format(returncode), sigevent_url)

        # flip the origin longitude of the right half
        gdal_edit_command_list = ['gdal_edit.py', tile_right, '-a_ullr', str(Decimal(antimeridian) * -1), uly, lrx, lry]
        log_the_command(gdal_edit_command_list)
        gdal_edit = subprocess.Popen(gdal_edit_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = gdal_edit.wait()
        if returncode != 0:
            log_sig_err('gdal_edit.py return code {0}'.format(returncode), sigevent_url)
        print("Cut and edited tile_right extents: " + ",".join(get_image_extents(tile_right)))

    return (tile_left, tile_right)


def crop_to_extents(tile, tile_extents, projection_extents, working_dir):
    """
    Crops a tile to be within projection extents
    Arguments:
        tile -- Tile to crop
        tile_extents -- The spatial extents of the tile as ulx, uly, lrx, lry
        projection_extents -- The spatial extents of the projection as xmin, ymin, xmax, ymax
        working_dir -- Directory to use for temporary files
    """
    ulx, uly, lrx, lry     = tile_extents
    xmin, ymin, xmax, ymax = projection_extents
    if float(ulx) < float(xmin):
        ulx = xmin
    if float(uly) > float(ymax):
        uly = ymax
    if float(lrx) > float(xmax):
        lrx = xmax
    if float(lry) < float(ymin):
        lry = ymin
    cut_tile = working_dir + os.path.basename(tile) + '._cut.vrt'
    gdalwarp_command_list = ['gdalwarp', '-overwrite', '-of', 'VRT', '-te', ulx, lry, lrx, uly, tile, cut_tile]
    log_the_command(gdalwarp_command_list)
    subprocess.call(gdalwarp_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return cut_tile


@contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


class rw_lock:
    def __init__(self):
        self.counter = multiprocessing.Value('i', 0)
        self.cond = multiprocessing.Condition(lock=self.counter.get_lock())

    def down_read(self):
        self.cond.acquire()
        self.counter.value += 1

        self.cond.release()

    def up_read(self):
        self.cond.acquire()
        self.counter.value -= 1

        if self.counter.value == 0:
            self.cond.notify()

        self.cond.release()

    def down_write(self):
        self.cond.acquire()

        while self.counter.value != 0:
            self.cond.wait()

    def up_write(self):
        self.cond.notify()
        self.cond.release()


lock = rw_lock()  # used to ensure that gdal_merge doesn't happen at the same time as a parallel insert


def parallel_mrf_insert(tiles, mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                        target_extents, target_epsg, nodata, merge, working_dir, no_cpus):
    """
    Launches multiple workers each handling a fraction of the tiles to be merged into the final mrf file.
    Also sets the mrf to be mp_safe to allow for simultaneous access. Generally 2-4 workers is ideal.
    There can be some degredation in performance for large numbers of workers. We use the rw_lock to
    synchronize access between the processes, since gdal_merge must be performed while no other process is running
    mrf_insert. If mrf_maxsize is None, will run mrf_insert with max_size max(2 * total size of input tiles, 50GB).
    Otherwise uses mrf_maxsize.

    Arguments:
        tiles ... working_dir: Same as mrf_insert
        no_cpus (int) -- Number of CPUs to run mrf_insert in parallel
    """

    log_info_mssg("parallel_mrf_insert with mrf {}".format(mrf))

    no_pools = min(multiprocessing.cpu_count() - 1, len(tiles), no_cpus)
    log_info_mssg("no_pools for parallel mrf_insert is {} for mrf {}".format(no_pools, mrf))

    if len(tiles) == 1 or no_pools == 1:
        log_info_mssg("making serial call since not enough tiles or cores")
        errors = run_mrf_insert(tiles, mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                                target_extents, target_epsg, nodata, merge, working_dir, max_size=mrf_maxsize)
    else:
        if mrf_maxsize is None:
            total_size = sum([os.stat(tile).st_size for tile in tiles])
            max_size = max(2 * total_size, 50E9)
        else:
            max_size = mrf_maxsize

        log_info_mssg("making parallel call with length of tiles is {}, mrf is {}, max_size is {} bytes\n".format(len(tiles), mrf, max_size))

        func = functools.partial(run_mrf_insert, mrf=mrf, insert_method = insert_method, \
                                 resize_resampling = resize_resampling, target_x = target_x, target_y = target_y, \
                                 mrf_blocksize = mrf_blocksize, target_extents = target_extents, target_epsg = target_epsg, \
                                 nodata = nodata, merge = merge, working_dir = working_dir, mp_safe=True, max_size=max_size)

        with open(mrf) as f: # make mp_safe
            data = f.read()
            data = data.replace("<Raster>", "<Raster mp_safe=\"on\">")

        with open(mrf, "w") as f: # overwrite mrf
            f.write(data)

        log_info_mssg("Splitting list of length {} into chunks of size {}".format(len(tiles), len(tiles) // no_pools))

        def chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i+n]

        random.shuffle(tiles) # shuffle tiles to avoid overlaps as much as possible
        partition = chunks(tiles, len(tiles) // no_pools)

        with poolcontext(processes=no_pools) as pool:
            results = pool.map(func, partition, 1)

        log_info_mssg("mrf {} map finished, results are type {}, {}".format(mrf, type(results), results))

        errors = sum(results)

    log_info_mssg("Errors {}, mrf {}".format(errors, mrf))

    return errors


def clean_mrf(data_filename): # cleans mrf files in place.
    def index_name(mrf_name):
        bname, ext = os.path.splitext(mrf_name)
        return bname + os.extsep + "idx"

    bname, ext = os.path.splitext(data_filename)
    target_path = bname + os.extsep + "tmp" + ext

    mrf_status = subprocess.Popen(["mrf_clean.py", data_filename, target_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = mrf_status.communicate()

    log_info_mssg(out)

    if mrf_status.returncode != 0:
        log_info_mssg("mrf_clean returned with status code {}".format(mrf_status.returncode))

    os.rename(target_path, data_filename)
    os.rename(index_name(target_path), index_name(data_filename))


def run_mrf_insert(tiles, mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                   target_extents, target_epsg, nodata, merge, working_dir, mp_safe=False, max_size=None):
    """
    Inserts a list of tiles into an existing MRF
    Arguments:
        tiles -- List of tiles to insert
        mrf -- An existing MRF file
        insert_method -- The resampling method to use {Avg, NNb}
        resize_resampling -- The resampling method to use for gdalwarp
        target_x -- The target resolution for x
        target_y -- The target resolution for y
        mrf_blocksize -- The block size of MRF tiles
        target_extents -- Full extents of the target imagery
        target_epsg -- The target EPSG code
        nodata -- nodata value
        merge -- Merge over transparent regions of imagery
        working_dir -- Directory to use for temporary files
        mp_safe -- mrf_insert should be mp_safe (default False)
        max_size -- run clean_mrf on target mrf when this size is reached (in bytes)
    """
    errors = 0
    t_xmin, t_ymin, t_xmax, t_ymax  = target_extents
    print("Target extents: " + ",".join([t_xmin, t_ymin, t_xmax, t_ymax]))

    if target_y == '':
        target_y = float(int(target_x)/2)
    log_info_mssg("Inserting new tiles into " + mrf)
    mrf_insert_command_list = ['mrf_insert', '-r', insert_method]

    should_lock = mp_safe

    if should_lock:
        global lock

    def data_name(mrf_name):
        bname, ext = os.path.splitext(mrf_name)
        return bname + os.extsep + get_extension(mrf_compression_type)

    for i, tile in enumerate(tiles):
        if should_lock:
            lock.down_read()

        s_xmin, s_ymax, s_xmax, s_ymin = get_image_extents(tile)
        print("Source extents: " + ",".join([s_xmin, s_ymax, s_xmax, s_ymin]))

        # Commenting this out because I am not aware of anywhere that we are _not_ invoking this method with the exact
        # set of tiles that we want to insert...
        '''
        if os.path.splitext(tile)[1] == ".vrt" and not ("_cut." in tile or "_reproject." in tile):
            # ignore temp VRTs unless it's an antimeridian cut or reprojected source image
            log_info_mssg("Skipping insert of " + tile)
            if should_lock:
                lock.up_read()
            continue
        '''

        # check if image fits within extents
        if target_epsg in ['EPSG:3031','EPSG:3413','EPSG:3857'] and \
            ((float(s_xmin) < float(t_xmin)) or \
            (float(s_ymax) > float(t_ymax)) or \
            (float(s_xmax) > float(t_xmax)) or \
            (float(s_ymin) < float(t_ymin))):
            log_info_mssg(tile + " falls outside of extents for " + target_epsg)
            cut_tile = crop_to_extents(tile, [s_xmin, s_ymax, s_xmax, s_ymin], target_extents, working_dir)
            if should_lock:
                lock.up_read()

            errors += run_mrf_insert([cut_tile], mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                                     target_extents, target_epsg, nodata, True, working_dir)
            continue

        elif target_epsg in ['EPSG:4326','EPSG:3857'] and ((float(s_xmin) > float(s_xmax)) or
                                                           (float(s_xmax) > float(t_xmax)) or
                                                           (float(s_xmin) < float(t_xmin))):
            log_info_mssg(tile + " crosses antimeridian")
            left_half, right_half = split_across_antimeridian(tile, [s_xmin, s_ymax, s_xmax, s_ymin], t_xmax,
                                                              str((Decimal(t_xmax)-Decimal(t_xmin))/Decimal(target_x)),
                                                              str((Decimal(t_ymin)-Decimal(t_ymax))/Decimal(target_y)),
                                                              working_dir)
            if should_lock:
                lock.up_read()

            insert_tiles = []

            # The left half of the split could be None if there wasn't a full pixel beyond the antimeridian
            if left_half:
                log_info_mssg('Will insert left half ' + left_half)
                insert_tiles.append(left_half)

            # The right half of the split could be None if there wasn't a full pixel beyond the antimeridian
            if right_half:
                log_info_mssg('Will insert right half ' + right_half)
                insert_tiles.append(right_half)

            if len(insert_tiles) > 0:
                errors += run_mrf_insert(insert_tiles, mrf, insert_method, resize_resampling, target_x, target_y,
                                         mrf_blocksize, target_extents, target_epsg, nodata, True, working_dir)
            else:
                log_sig_err("No tiles to insert after splitting across antimeridian", sigevent_url)
            continue

        if merge: # merge tile with existing imagery if true
            if should_lock:
                lock.up_read()
                lock.down_write()

            tile = gdalmerge(mrf, tile, [s_xmin, s_ymax, s_xmax, s_ymin], target_x, target_y, mrf_blocksize,
                             t_xmin, t_ymin, t_xmax, t_ymax, nodata, resize_resampling, working_dir, target_epsg)
            
            if tile is None:
                errors += 1
                return errors

            if should_lock:
                lock.up_write()
                lock.down_read()

        vrt_tile = working_dir + os.path.basename(tile)+".vrt"

        diff_res, ps = diff_resolution([tile, mrf])

        if diff_res:
            # convert tile to matching resolution
            if resize_resampling == '':
                resize_resampling = "near" # use nearest neighbor as default

            tile_vrt_command_list = ['gdalwarp', '-of', 'VRT', '-r', resize_resampling, '-overwrite', '-tr',
                                     str((Decimal(t_xmax)-Decimal(t_xmin))/Decimal(target_x)),
                                     str((Decimal(t_ymin)-Decimal(t_ymax))/Decimal(target_y))]

            # build the vrt for the entire projection if we have one image that covers the entire projection
            # TODO ... not sure this is needed actually...
            if is_global_image(tile, t_xmin, t_ymin, t_xmax, t_ymax) and len(tiles) == 1:
                tile_vrt_command_list.append('-te')
                tile_vrt_command_list.append(t_xmin)
                tile_vrt_command_list.append(t_ymin)
                tile_vrt_command_list.append(t_xmax)
                tile_vrt_command_list.append(t_ymax)

            tile_vrt_command_list.append(tile)
            tile_vrt_command_list.append(vrt_tile)
            log_the_command(tile_vrt_command_list)
            tile_vrt = subprocess.Popen(tile_vrt_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            returncode = tile_vrt.wait()
            if returncode != 0:
                log_sig_err('build tile VRT (gdalwarp) return code {0}'.format(returncode), sigevent_url)

            if merge: # merge tile with existing imagery
                if should_lock:
                    lock.up_read()
                    lock.down_write()

                s_xmin, s_ymax, s_xmax, s_ymin = get_image_extents(vrt_tile) # get new extents
                log_info_mssg("Image extents " + str(extents))
                tile = gdalmerge(mrf, vrt_tile, [s_xmin, s_ymax, s_xmax, s_ymin], target_x, target_y, mrf_blocksize,
                                 t_xmin, t_ymin, t_xmax, t_ymax, nodata, resize_resampling, working_dir, target_epsg)
                if tile is None:
                    errors += 1
                    return errors
                mrf_insert_command_list.append(tile)

                if should_lock:
                    lock.up_write()
                    lock.down_read()

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
            if 'Access window out of range' in str(message):
                log_sig_warn(str(message), sigevent_url)
            elif 'ERROR' in str(message):
                errors += 1
                log_sig_err("mrf_insert {0}".format(message), sigevent_url)
            else:
                log_info_mssg(str(message).strip())
        returncode = mrf_insert.wait()
        if returncode != 0:
            log_sig_err('mrf_insert return code {0}'.format(returncode), sigevent_url)

        # Remove temporary merged files (if created)
        if ".merge." in tile:
            remove_file(tile)

        # Remove the temporary (if created) vrt tile used to sort out differing resolutions of the tile and MRF
        remove_file(vrt_tile)

        # Commenting this out because I am not aware of any lingering VRT files that must be removed... and this causes
        # some issues if the input tile list had VRTs in it
        '''
        temp_vrt_files = glob.glob(working_dir + os.path.basename(tile) + "*vrt*")
        for vrt in temp_vrt_files:
            remove_file(vrt)
        '''

        if should_lock:
            lock.up_read()

        if max_size is not None:
            if os.stat(data_name(mrf)).st_size > max_size:
                if should_lock:
                    lock.down_write()
                if os.stat(data_name(mrf)).st_size > max_size:
                    log_info_mssg_with_timestamp("cleaning data file {} with size {}".
                                                 format(data_name(mrf), os.stat(data_name(mrf)).st_size))
                    clean_mrf(data_name(mrf))
                    log_info_mssg_with_timestamp("done cleaning data file {}. now has size {}".
                                                 format(data_name(mrf), os.stat(data_name(mrf)).st_size))
                if should_lock:
                    lock.up_write()

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
            except sqlite3.Error as e:
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
                    except sqlite3.Error as e: # if 0 index has already been taken
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

    except sqlite3.Error as e:
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


# call oe_utils' log_sig_err and keep track of errors if count_err is True
def log_sig_err(mssg, sigevent_url, count_err=True):
    global errors
    oe_utils.log_sig_err(mssg, sigevent_url)
    if count_err:
        errors += 1


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
parser.add_option("-s", "--send_email", action="store_true", dest="send_email",
                  default=False, help="Send email notification for errors and warnings.")
parser.add_option('--email_server', action='store', type='string', dest='email_server',
                  default='', help='The server where email is sent from (overrides configuration file value)')
parser.add_option('--email_recipient', action='store', type='string', dest='email_recipient',
                  default='', help='The recipient address for email notifications (overrides configuration file value)')
parser.add_option('--email_sender', action='store', type='string', dest='email_sender',
                  default='', help='The sender for email notifications (overrides configuration file value)')
parser.add_option('--email_logging_level', action='store', type='string', dest='email_logging_level',
                  default='ERROR', help='Logging level for email notifications: ERROR, WARN, or INFO.  Default: ERROR')

# Read command line args.
(options, args) = parser.parse_args()
# Configuration filename.
configuration_filename=options.configuration_filename
# Send email.
send_email=options.send_email
# Email server.
email_server=options.email_server
# Email recipient
email_recipient=options.email_recipient
# Email sender.
email_sender=options.email_sender
# Data only.
data_only = options.data_only
# Email logging level
logging_level = options.email_logging_level.upper()

# Email metadata replaces sigevent_url
if send_email:
    sigevent_url = (email_server, email_recipient, email_sender, logging_level)
else:
    sigevent_url = ''

# Get current time, which is written to a file as the previous cycle time.
# Time format is "yyyymmdd.hhmmss.f".  Do this first to avoid any gap where tiles
# may get passed over because they were created while this script is running.
current_cycle_time = datetime.datetime.now().strftime("%Y%m%d.%H%M%S.%f")


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
    oe_utils.basename = basename = str().join([parameter_name, '_', date_of_data, '___', 'mrfgen_', current_cycle_time, '_', str(os.getpid())])

    # Get default email server and recipient if not override
    if email_server == '':
        try:
            email_server = get_dom_tag_value(dom, 'email_server')
        except:
            email_server = ''
    if email_recipient == '':
        try:
            email_recipient = get_dom_tag_value(dom, 'email_recipient')
        except:
            email_recipient = ''
    if email_sender == '':
        try:
            email_sender = get_dom_tag_value(dom, 'email_sender')
        except:
            email_sender = ''
    if send_email:
        sigevent_url = (email_server, email_recipient, email_sender, logging_level)
        if email_recipient == '':
            log_sig_err("No email recipient provided for notifications.", sigevent_url)

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
    output_dir = get_dom_tag_value(dom, 'output_dir')
    try:
        working_dir            =get_dom_tag_value(dom, 'working_dir')
        working_dir = add_trailing_slash(check_abs_path(working_dir))
    except: # use /tmp/ as default
        working_dir            ='/tmp/'
    try:
        logfile_dir = get_dom_tag_value(dom, 'logfile_dir')
    except: #use working_dir if not specified
        logfile_dir = working_dir
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
            target_x = get_dom_tag_value(dom, 'target_x')
        except:
            target_x = '' # if no target_x then use rasterXSize and rasterYSize from VRT file
        try:
            target_y = get_dom_tag_value(dom, 'target_y')
        except:
            target_y = ''
    # EPSG code projection.
    try:
        target_epsg = 'EPSG:' + str(get_dom_tag_value(dom, 'target_epsg'))
    except:
        target_epsg = 'EPSG:4326' # default to geographic
    try:
        if get_dom_tag_value(dom, 'source_epsg') == "detect":
            source_epsg = "detect"
        else:
            source_epsg = 'EPSG:' + str(get_dom_tag_value(dom, 'source_epsg'))
    except:
        source_epsg = 'EPSG:4326' # default to geographic

    # Source extents.
    try:
        extents = get_dom_tag_value(dom, 'extents')
    except:
        extents = '-180,-90,180,90' # default to geographic
    source_xmin, source_ymin, source_xmax, source_ymax = extents.split(',')

    # Target extents.
    try:
        target_extents = get_dom_tag_value(dom, 'target_extents')
    except:
        if target_epsg == 'EPSG:3857':
            target_extents = '-20037508.34,-20037508.34,20037508.34,20037508.34'
        elif target_epsg in ['EPSG:3413','EPSG:3031']:
            target_extents = '-4194304,-4194304,4194304,4194304'
        else:
            target_extents = '-180,-90,180,90'
    target_xmin, target_ymin, target_xmax, target_ymax = target_extents.split(',')

    # Input files.
    try:
        input_files = get_input_files(dom)
        empty_vrt = None
        if input_files == '':
            raise ValueError('No input files provided')
    except:
        if input_dir is None:
            if mrf_empty_tile_filename != '':
                input_files = None
                empty_vrt = create_vrt(add_trailing_slash(check_abs_path(working_dir))+basename, mrf_empty_tile_filename,
                                       target_epsg, target_xmin, target_ymin, target_xmax, target_ymax)
            else:
                log_sig_exit('ERROR', "<input_files> or <input_dir> or <mrf_empty_tile_filename> is required", sigevent_url)
        else:
            input_files = None
            empty_vrt = None
    # overview levels
    try:
        overview_levels = get_dom_tag_value(dom, 'overview_levels').split(' ')
        for level in overview_levels:
            if level.isdigit() == False:
                log_sig_exit("ERROR", "'" + level + "' is not a valid overview value.", sigevent_url)
        if len(overview_levels) > 1:
            overview = int(overview_levels[1]) / int(overview_levels[0])
        else:
            overview = 2
    except:
        overview_levels = ''
        overview = 2
    # resampling method
    try:
        overview_resampling = get_dom_tag_value(dom, 'overview_resampling')
    except:
        overview_resampling = 'nearest'
        # gdalwarp resampling method for resizing
    try:
        resize_resampling = get_dom_tag_value(dom, 'resize_resampling')
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
    # nocopy
    try:
        if get_dom_tag_value(dom, 'mrf_nocopy') == "true":
            nocopy = True
        else:
            nocopy = False
    except:
        nocopy = None
    # noaddo
    try:
        if get_dom_tag_value(dom, 'mrf_noaddo') == "false":
            noaddo = False
        else:
            noaddo = True
    except:
        noaddo = None

    # mrf_cores (max number of cpu cores to run on if mrf_parallel is set, defaults to 4
    try:
        mrf_cores = int(get_dom_tag_value(dom, 'mrf_cores'))
    except:
        mrf_cores = 4 # multiprocessing.cpu_count()

    # mrf_parallel (run mrf_insert in parallel), defaults to False
    try:
        if get_dom_tag_value(dom, 'mrf_parallel') == "true":
            mrf_parallel = True
        else:
            mrf_parallel = False
    except:
        mrf_parallel = False

    # run the mrf_clean utility to reduce the size of the generated MRFs, defaults to mrf_parallel.
    try:
        if get_dom_tag_value(dom, 'mrf_clean') == "true":
            mrf_clean = True
        else:
            mrf_clean = False
    except:
        if mrf_parallel:
            mrf_clean = True
        else:
            mrf_clean = False

    # set a maximum size for the mrf before running mrf_clean. used to manage MRF sizes for mrf_parallel and mrf_noaddo
    try:
        mrf_maxsize = int(get_dom_tag_value(dom, 'mrf_maxsize'))
    except:
        mrf_maxsize = None

    # merge, defaults to False
    try:
        if get_dom_tag_value(dom, 'mrf_merge') == "false":
            merge = False
        else:
            merge = True
    except:
        merge = False
    # strict_palette, defaults to False
    try:
        if get_dom_tag_value(dom, 'mrf_strict_palette') == "false":
            strict_palette = False
        else:
            strict_palette = True
    except:
        strict_palette = False
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
mrf_compression_type=mrf_compression_type.upper()

# Verify logfile_dir first so that the log can be started.
verify_directory_path_exists(logfile_dir, 'logfile_dir', sigevent_url)
# Initialize log file.
log_filename=str().join([logfile_dir, basename, '.log'])
logging.basicConfig(filename=log_filename, level=logging.INFO)

# Verify remaining directory paths.
if input_dir != None:
    verify_directory_path_exists(input_dir, 'input_dir', sigevent_url)
verify_directory_path_exists(output_dir, 'output_dir', sigevent_url)
verify_directory_path_exists(working_dir, 'working_dir', sigevent_url)

# Make certain color map can be found
if colormap != '' and '://' not in colormap:
    colormap = check_abs_path(colormap)

# Log all of the configuration information.
log_info_mssg_with_timestamp(str().join(['config XML file:  ', configuration_filename]))
                                      
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
if input_files is not None:
    log_info_mssg(str().join(['config input_files:             ', input_files]))
if input_dir is not None:
    log_info_mssg(str().join(['config input_dir:               ', input_dir]))
if empty_vrt is not None:
    log_info_mssg(str().join(['config empty_vrt:               ', empty_vrt]))
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
log_info_mssg(str().join(['config mrf_noaddo:              ', str(noaddo)]))
log_info_mssg(str().join(['config mrf_merge:               ', str(merge)]))
log_info_mssg(str().join(['config mrf_parallel:            ', str(mrf_parallel)]))
log_info_mssg(str().join(['config mrf_cores:               ', str(mrf_cores)]))
log_info_mssg(str().join(['config mrf_clean:               ', str(mrf_clean)]))
log_info_mssg(str().join(['config mrf_maxsize:             ', str(mrf_maxsize)]))
log_info_mssg(str().join(['config mrf_strict_palette:      ', str(strict_palette)]))
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
        # Check the last 3 characters in case of PNG or PPNG or JPNG.
        if mrf_compression_type[-3:len(mrf_compression_type)] != 'PNG':
            mssg='Empty tile format does not match MRF compression type.'
            log_sig_exit('ERROR', mssg, sigevent_url)

    if mrf_empty_tile_what == 'jpeg':
        # Check the first 2 characters in case of JPG or JPEG.
        if mrf_compression_type.lower() not in ['jpeg', 'jpg', 'zen']:
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
if input_files is not None:
    input_files = input_files.strip()
    alltiles = input_files.split(',')

if input_dir is not None:
    if mrf_compression_type.lower() in ['jpeg', 'jpg', 'zen']:
        alltiles = alltiles + glob.glob(str().join([input_dir, '*.jpg']))
    if mrf_compression_type.lower() in ['png', 'ppng', 'zen']:
        alltiles = alltiles + glob.glob(str().join([input_dir, '*.png']))
    # check for tiffs
    alltiles = alltiles + glob.glob(str().join([input_dir, '*.tif']))
    alltiles = alltiles + glob.glob(str().join([input_dir, '*.tiff']))
    # check for mrfs
    alltiles = alltiles + glob.glob(str().join([input_dir, '*.mrf']))

# Sanitize input in case there were extra spaces
striptiles = []
for tile in alltiles:
    striptiles.append(tile.strip())
alltiles = striptiles

# Set compression type in case of TIFF
if mrf_compression_type.lower() in ['jpeg', 'jpg', 'zen']:
    tiff_compress = "JPEG"
else: # Default to png
    tiff_compress = "PNG"

# Set the blocksize for gdal_translate (-co NAME=VALUE).
blocksize=str().join(['BLOCKSIZE=', mrf_blocksize])

# Sanity check to make sure all of the input files exist
for i, tile in enumerate(alltiles):

    if tile.startswith("/vsi"):
        try:
            img = gdal.Open(tile)
            img = None
        except:
            log_info_mssg("Missing input file: " + tile)
            log_sig_exit('ERROR', 'Invalid input files', sigevent_url)

    elif not os.path.exists(tile):
        log_info_mssg("Missing input file: " + tile)
        log_sig_exit('ERROR', 'Invalid input files', sigevent_url)


# Filter out bad JPEGs
goodtiles = []
if mrf_compression_type.lower() in ['jpeg', 'jpg', 'zen']:
    for i, tile in enumerate(alltiles):
        if ".mrf" in tile or ".vrt" in tile:  # ignore MRFs and VRTs
            goodtiles.append(tile)
            continue

        try:
            img = gdal.Open(tile)

            if img is None:
                log_sig_err("Bad JPEG tile detected: {0}".format(tile), sigevent_url)
                continue
        except RuntimeError as e:
            log_sig_exit('ERROR', 'Failed to execute gdal.Open', sigevent_url)

        if img.RasterCount == 1:
            log_sig_err("Bad JPEG tile detected: {0}".format(tile), sigevent_url)
            img = None
            continue

        img = None

        goodtiles.append(tile)

    alltiles = goodtiles

# Convert RGBA PNGs to indexed paletted PNGs if requested
if mrf_compression_type == 'PPNG' and colormap != '':
    for i, tile in enumerate(alltiles):
        temp_tile = None
        tile_path = os.path.dirname(tile)
        tile_basename, tile_extension = os.path.splitext(os.path.basename(tile))

        # Check input PNGs/TIFFs if RGBA, then convert       
        if tile.lower().endswith(('.png', '.tif', '.tiff')):
 
            gdalinfo_command_list = ['gdalinfo', '-json', tile]
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            """
            returncode = gdalinfo.wait()
            if returncode != 0:
                log_sig_err('gdalinfo return code {0}'.format(returncode), sigevent_url)
            tileInfo = json.loads(gdalinfo.stdout.read())
            """
            has_palette = False
            try:
                outs, errs = gdalinfo.communicate(timeout=90)
                if len(errs) > 0:
                    log_sig_err('gdalinfo errors: {0}'.format(errs), sigevent_url)
                tileInfo = json.loads(outs)           
                for band in tileInfo["bands"]:
                    has_palette |= (band["colorInterpretation"] == "Palette")
            except subprocess.TimeoutExpired:
                gdalinfo.kill()
                log_sig_err('gdalinfo timed out', sigevent_url)

            # Read gdal_info output
            if not has_palette:

                # Download tile locally for RgbPngToPalPng script
                if tile.startswith("/vsi"):
                    log_info_mssg("Downloading remote file " + tile)

                    # Create the gdal_translate command.
                    gdal_translate_command_list=['gdal_translate', '-q', '-co', 'WORLDFILE=YES',
                                                 tile, working_dir+os.path.basename(tile)]

                    # Log the gdal_translate command.
                    log_the_command(gdal_translate_command_list)

                    # Execute gdal_translate.
                    subprocess.call(gdal_translate_command_list, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

                    # Replace with new tiles
                    tile = working_dir+os.path.basename(tile)

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

                # Create the RgbPngToPalPng command.
                if vrtnodata == "":
                    fill = 0
                else:
                    fill = vrtnodata
                RgbPngToPalPng_command_list=['python3 ' + script_dir + 'RgbPngToPalPng.py -v -c ' + colormap +
                                             ' -f ' + str(fill) + ' -o ' + output_tile + ' -i ' + tile]

                # Log the RgbPngToPalPng command.
                log_the_command(RgbPngToPalPng_command_list)

                # Execute RgbPngToPalPng.
                try:
                    RgbPngToPalPng = subprocess.Popen(RgbPngToPalPng_command_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except OSError:
                    log_sig_exit('ERROR', "RgbPngToPalPng tool cannot be found.", sigevent_url)

                RgbPngToPalPng.wait()
                if RgbPngToPalPng.returncode != None:
                    if  0 < RgbPngToPalPng.returncode < 255:
                        mssg = "RgbPngToPalPng: " + str(RgbPngToPalPng.returncode) + " colors in image not found in color table"
                        log_sig_warn(mssg, sigevent_url)
                    if RgbPngToPalPng.returncode == 255:
                        mssg = str(RgbPngToPalPng.stderr.readlines()[-1])
                        log_sig_err("RgbPngToPalPng: " + mssg, sigevent_url, count_err=False)
                    errors += RgbPngToPalPng.returncode

                if os.path.isfile(output_tile):
                    mssg = output_tile + " created"
                    try:
                        log_info_mssg(mssg)
                        # sigevent('INFO', mssg, sigevent_url)
                    except urllib.error.URLError:
                        print('sigevent service is unavailable')
                    # Replace with new tiles
                    alltiles[i] = output_tile
                else:
                    log_sig_err("RgbPngToPalPng failed to create {0}".format(output_tile), sigevent_url)

                # Make a copy of world file
                try:
                    if os.path.isfile(tile_path+'/'+tile_basename+'.pgw'):
                        shutil.copy(tile_path+'/'+tile_basename+'.pgw', output_tile_path+'/'+output_tile_basename+'.pgw')
                    elif os.path.isfile(working_dir+'/'+tile_basename+'.wld'):
                        shutil.copy(working_dir+'/'+tile_basename+'.wld', output_tile_path+'/'+output_tile_basename+'.pgw')
                    else:
                        log_info_mssg("World file does not exist for tile: {0}".format(tile))
                except:
                    log_sig_err("ERROR: " + mssg, sigevent_url)


                # Save projection information for EPSG detection
                try:
                    if os.path.isfile(working_dir+'/'+tile_basename+'.png.aux.xml'):
                        shutil.copy(working_dir+'/'+tile_basename+'.png.aux.xml', output_tile_path+'/'+output_tile_basename+'.png.aux.xml')
                    else:
                        log_info_mssg("Geolocation file does not exist for tile: " + tile)
                except:
                    log_sig_err("ERROR: " + mssg, sigevent_url)

                # add transparency flag for custom color map
                add_transparency = True
            else:
                log_info_mssg("Paletted image found for PPNG output, no palettization required")

            # ONEARTH-348 - Validate the palette, but don't do anything about it yet
            # For now, we won't enforce any issues, but will log issues validating imagery
            if strict_palette:
                oe_validate_palette_command_list=[script_dir + 'oe_validate_palette.py', '-v', '-c', colormap, '-i', alltiles[i]]

                # Log the oe_validate_palette.py command.
                log_the_command(oe_validate_palette_command_list)

                # Execute oe_validate_palette.py
                try:
                    oeValidatePalette = subprocess.Popen(oe_validate_palette_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    oeValidatePalette.wait()

                    if oeValidatePalette.returncode != None:
                        if  oeValidatePalette.returncode != 0:
                            mssg = "oe_validate_palette.py: Mismatching palette entries between the image and colormap; Resulting image may be invalid"
                            log_sig_warn(mssg, sigevent_url)

                except OSError:
                    log_sig_warn("Error executing oe_validate_palette.py", sigevent_url)


        # remove tif temp tiles
        if temp_tile != None:
            remove_file(temp_tile)
            remove_file(temp_tile+'.aux.xml')
            remove_file(temp_tile.split('.')[0]+'.wld')

# Create VRTs with the target EPSG for input images if the source EPSG is different or is to be detected:
if source_epsg == "detect" or source_epsg != target_epsg:
    log_info_mssg("source EPSG != target EPSG or source EPSG is to be detected; Creating VRTs for each input tile in target EPSG")

    for i, tile in enumerate(alltiles):
        temp_tile = None
        tile_path = os.path.dirname(tile)
        tile_basename, tile_extension = os.path.splitext(os.path.basename(tile))
        tile_vrt = os.path.join(working_dir, tile_basename + "_reproject.vrt")

        if source_epsg == "detect":
            s_epsg = get_image_epsg(tile)
        else:
            s_epsg = source_epsg

        if not s_epsg:
            # if EPSG can't be determined, remove the tile
            log_sig_warn(tile + " has undetectable EPSG", sigevent_url)
            del alltiles[i]
        elif s_epsg != target_epsg:
            log_info_mssg("Creating VRT for input tile: " + tile)

            # if the source and target EPSGs are not the same, create a VRT

            gdalwarp_command_list = ['gdalwarp', '-q', '-overwrite', '-of', 'vrt', '-s_srs', s_epsg, '-t_srs', target_epsg, tile, tile_vrt]

            # Log the gdalbuildvrt command.
            log_the_command(gdalwarp_command_list)

            # Capture stderr to record skipped .png files that are not valid PNG+World.
            gdalwarp_stderr_filename = str().join([working_dir, basename, '_gdalwarp_stderr.txt'])
            # Open stderr file for write.
            gdalwarp_stderr_file = open(gdalwarp_stderr_filename, 'w+')

            # ---------------------------------------------------------------------------
            # Execute gdalwarp.
            subprocess.call(gdalwarp_command_list, stderr=gdalwarp_stderr_file)
            # ---------------------------------------------------------------------------

            gdalwarp_stderr_file.seek(0)
            gdalwarp_stderr = gdalwarp_stderr_file.read()
            if "Error" in gdalwarp_stderr:
                log_info_mssg(gdalwarp_stderr)
                log_sig_err('ERROR', "Error creating VRT for input image", sigevent_url)
                gdalwarp_stderr_file.close()
                del alltiles[i]
                continue

            # If we made it this far, the VRT was created successfully, so replace it in the input list
            alltiles[i] = tile_vrt

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
            # NOTE: Did not convert to JSON parsing because of a lack of test data
            # Get Scale and Offset from gdalinfo
            gdalinfo_command_list = ['gdalinfo', tile]
            log_the_command(gdalinfo_command_list)
            gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            returncode = gdalinfo.wait()
            if returncode != 0:
                log_sig_err("gdalinfo return code {0}".format(returncode), sigevent_url)
            gdalinfo_out = gdalinfo.stdout.readlines()
            if "Color Table" in ''.join(gdalinfo_out):
                log_sig_warn("{0} contains a palette".format(tile), sigevent_url)
                mrf_compression_type = 'PPNG'
            if "Offset:" in ''.join(gdalinfo_out) and "Scale:" in ''.join(gdalinfo_out):
                log_info_mssg("{0} is already an encoded TIFF".format(tile))
            else: # Encode the TIFF file
                encoded_tile = working_dir+tile_basename+'_encoded.tif'
                log_info_mssg("{0} will be encoded as {1}".format(tile, encoded_tile))
                if mrf_data_scale != '' and mrf_data_offset != '':
                    scale_offset = [float(mrf_data_scale), float(mrf_data_offset)]
                else:
                    scale_offset = None
                pack(tile, encoded_tile, False, True, None, None, scale_offset, False)
                tile = encoded_tile
                gdalinfo_command_list = ['gdalinfo', tile]
                log_the_command(gdalinfo_command_list)
                gdalinfo = subprocess.Popen(gdalinfo_command_list,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                returncode = gdalinfo.wait()
                if returncode != 0:
                    log_sig_err("gdalinfo return code {0}".format(returncode), sigevent_url)
                gdalinfo_out = gdalinfo.stdout.readlines()
            log_info_mssg("Reading scale and offset from bands")
            for line in gdalinfo_out:
                if "Offset:" in str(line) and "Scale:" in str(line):
                    offset,scale = str(line).strip().replace("Offset: ","").replace("Scale:","").split(",")
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
            returncode = gdal_translate.wait()
            gdal_translate_stderr = gdal_translate.stderr.read()
            if len(gdal_translate_stderr) > 0:
                log_sig_err(gdal_translate_stderr, sigevent_url)
            if returncode != 0:
                log_sig_err("gdal_translate return code {0}".format(returncode), sigevent_url)
            alltiles[i] = output_tile

#Look for ZenJPEG Output
if mrf_compression_type.lower() == 'zen':
    # mrf_insert doesn't convert tiles automatically to ZenJPEG
    # so we first convert each input tile individually into smaller "input" MRFs
    # and then insert and transform them later just like normal tiles
    for i, tile in enumerate(alltiles):
        tile_path = os.path.dirname(tile)
        tile_basename, tile_extension = os.path.splitext(os.path.basename(tile))
        tile_mrf = os.path.join(working_dir, tile_basename + "_zen.mrf")

        # Do the MRF creation from the input tile
        gdal_translate_command_list=['gdal_translate', '-q', '-b', '1', '-b', '2', '-b', '3', '-mask', '4', '-of', 'MRF', '-co', 'compress=JPEG', '-co', blocksize]    
        gdal_translate_command_list.append('-co')
        gdal_translate_command_list.append('QUALITY='+quality_prec)
        gdal_translate_command_list.append(tile)
        gdal_translate_command_list.append(tile_mrf)

        # Log and execute gdal_translate to generate "input" ZenJPEG MRFs
        log_the_command(gdal_translate_command_list)
        gdal_translate_stderr_filename=str().join([working_dir, basename, '_gdal_translate_zen_stderr.txt'])
        gdal_translate_stderr_file=open(gdal_translate_stderr_filename, 'w')
        subprocess.call(gdal_translate_command_list, stderr=gdal_translate_stderr_file)
        gdal_translate_stderr_file.close()
        if os.path.getsize(gdal_translate_stderr_filename) == 0:
            remove_file(gdal_translate_stderr_filename)

        alltiles[i] = tile_mrf

# sort
alltiles.sort()

# check for different resolutions
diff_res, res = diff_resolution(alltiles)

# determine if nocopy should be used if not set
if nocopy is None:
    if len(alltiles) == 1 and alltiles[0].endswith('.vrt') == False:
        if is_global_image(alltiles[0],source_xmin, source_ymin, source_xmax, source_ymax) == True:
            # Don't do inserts if we have a single global image
            nocopy = False
        else:
            nocopy = True
    elif len(alltiles) == 1 and alltiles[0].endswith('empty.vrt') == True: #empty VRT, use nocopy
        nocopy = True
    else:
        if source_epsg != target_epsg:
            # Avoid inserts if reprojecting
            nocopy = False
        else:
            nocopy = True
    log_info_mssg("Setting MRF nocopy to " + str(nocopy))

# determine if noaddo should be used if not set
if noaddo is None:
    # nocopy implies mrf_insert is used, which already builds overviews
    noaddo = nocopy

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
    if len(alltiles) > 0:
        for ndx in range(len(alltiles)):
            alltilesfile.write(str().join([alltiles[ndx], '\n']))
    elif empty_vrt is not None:
        # Create a VRT for an empty input
        alltilesfile.write("{0}\n".format(empty_vrt))
    else:
        mssg='No input tiles or empty VRT to process'
        log_sig_exit('ERROR', mssg, sigevent_url)

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

def get_extension(compression_type):
    if compression_type in ['PNG', 'PPNG', 'EPNG', 'JPNG']:
        return "ppg"
    elif compression_type in ['JPG', 'JPEG']:
        return "pjg"
    elif compression_type in ['TIF', 'TIFF']:
        return "ptf"
    elif compression_type == 'LERC':
        return "lrc"
    else:
        return None

if mrf_compression_type in ['PNG', 'PPNG', 'EPNG']:
    # Output filename.
    out_filename=str().join([output_dir, basename, '.ppg'])
elif mrf_compression_type == 'JPNG':
    # Output filename.
    out_filename=str().join([output_dir, basename, '.pjp'])
elif mrf_compression_type in ['JPG', 'JPEG', 'ZEN']:
    # Output filename.
    out_filename=str().join([output_dir, basename, '.pjg'])
elif mrf_compression_type in ['TIF', 'TIFF']:
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
if overview_resampling[:4].lower() == 'near' or overview_resampling.lower() == 'nnb':
    insert_method = 'NearNB'
else:
    insert_method = 'Avg'

for tile in list(alltiles):
    if '.mrf' in tile.lower() and '_zen.' not in tile:
        mrf_list.append(tile)
        alltiles.remove(tile)

# If more than one MRF, expected behavior is unknown... so exit
if len(mrf_list) > 1:
    log_sig_exit('ERROR', "Multiple MRFs found in input list, expected behavior unknown", sigevent_url)
# Only be one MRF, so use that one
elif len(mrf_list) == 1:
    mrf = mrf_list[0]
    timeout = time.time() + 30 # 30 second timeout if MRF is still being generated

    # Bail if a remote MRF is included in the input list.  Just can't handle this yet.
    if mrf.startswith("/vsi"):
        mssg='Cannot support a remote (i.e. /vsi...) MRF input'
        log_sig_exit('ERROR', mssg, sigevent_url)

    while not os.path.isfile(mrf):
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

    if mrf_parallel:
        parallel_mrf_insert(alltiles, mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                             [target_xmin, target_ymin, target_xmax, target_ymax], target_epsg, vrtnodata, merge, working_dir, mrf_cores)
    else:
        run_mrf_insert(alltiles, mrf, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                             [target_xmin, target_ymin, target_xmax, target_ymax], target_epsg, vrtnodata, merge, working_dir, max_size=mrf_maxsize)
    
    # Clean up
    remove_file(all_tiles_filename)

    # Exit here since we don't need to build an MRF from scratch
    mssg=str().join(['MRF updated:  ', mrf])
    log_info_mssg(mssg)

    # Exit mrfgen because we are done
    if errors > 0:
        print("{0} errors encountered".format(errors))
        sys.exit(1)
    else:
        sys.exit(0)

# Else, no MRF so continue on with the rest of the processing...


# Use zdb index if z-levels are defined
if zlevels != '':
    mrf_filename, idx_filename, out_filename, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name,
                                                                                     parameter_name, date_of_data,
                                                                                     time_of_data)
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


gdalbuildvrt_command_list=['gdalbuildvrt', '-q', '-input_file_list', all_tiles_filename]

# all tiles are now in the target_epsg because:
#   a) source_epsg == target_epsg
#       OR
#   b) source_epsg != target_epsg and we've fixed that by replacing the tile with a VRT

# Set the extents and EPSG based on the target since we know that that the EPSG of all tiles is the target EPSG
gdalbuildvrt_command_list.extend(['-te', target_xmin, target_ymin, target_xmax, target_ymax])
gdalbuildvrt_command_list.append('-a_srs')
gdalbuildvrt_command_list.append(target_epsg)

if target_x != '':
    # set the output resolution if a target size has been provided
    xres = repr(abs((float(target_xmax)-float(target_xmin))/float(target_x)))
    if target_y != '':
        yres = repr(abs((float(target_ymin)-float(target_ymax))/float(target_y)))
    else:
        yres = xres
    log_info_mssg("x resolution: " + xres + ", y resolution: " + yres)
    gdalbuildvrt_command_list.append('-resolution')
    gdalbuildvrt_command_list.append('user')
    gdalbuildvrt_command_list.append('-tr')
    gdalbuildvrt_command_list.append(xres)
    gdalbuildvrt_command_list.append(yres)

if vrtnodata != "":
    # set the nodata values if provided
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

# use gdalwarp if resize with resampling method is declared
if resize_resampling != '':
    if target_y == '':
        target_y = str(int(target_x)/2)
    gdal_warp_command_list = ['gdalwarp', '-of', 'VRT' ,'-r', resize_resampling, '-ts', str(target_x), str(target_y),
                              '-te', target_xmin, target_ymin, target_xmax, target_ymax, '-overwrite', vrt_filename,
                              vrt_filename.replace('.vrt','_resample.vrt')]
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
        skipped=str(gdalbuildvrt_stderr[ndx]).find('Warning')
        # If a line (including line 0) was found.
        if skipped >= 0:
            mssg=str().join(['gdalbuildvrt ', str(gdalbuildvrt_stderr[ndx])])
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
elif mrf_compression_type == 'JPNG':
    # JPNG Blended Format
    compress=str('COMPRESS=JPNG')
elif mrf_compression_type == 'JPG':
    compress=str('COMPRESS=JPEG')
elif mrf_compression_type == 'JPEG':
    compress=str('COMPRESS=JPEG')
elif mrf_compression_type == 'ZEN':
    compress=str('COMPRESS=JPEG')
elif mrf_compression_type == 'TIFF' or mrf_compression_type == 'TIF':
    compress=str('COMPRESS=TIF')
elif mrf_compression_type == 'LERC':
    compress=str('COMPRESS=LERC')
else:
    mssg='Unrecognized compression type for MRF.'
    log_sig_exit('ERROR', mssg, sigevent_url)

# Insert color map into VRT if provided
# TODO This could be problematic if we're overwriting with a different palette than what is in the imagery.
if colormap != '':
    new_vrt_filename = vrt_filename.replace('.vrt','_newcolormap.vrt')
    colormap2vrt_command_list=[script_dir+'colormap2vrt.py','--colormap',colormap,'--output',new_vrt_filename,'--merge',vrt_filename]
    if add_transparency == True:
        colormap2vrt_command_list.append('--transparent')
    if send_email == True:
        colormap2vrt_command_list.append('--send_email')
    if email_server != '':
        colormap2vrt_command_list.append('--email_server')
        colormap2vrt_command_list.append(email_server)
    if email_recipient != '':
        colormap2vrt_command_list.append('--email_recipient')
        colormap2vrt_command_list.append(email_recipient)
    if email_sender != '':
        colormap2vrt_command_list.append('--email_sender')
        colormap2vrt_command_list.append(email_sender)
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

# Get input size.
dom=xml.dom.minidom.parse(vrt_filename)
rastersize_elements=dom.getElementsByTagName('VRTDataset')
x_size=rastersize_elements[0].getAttribute('rasterXSize') #width
y_size=rastersize_elements[0].getAttribute('rasterYSize') #height

if target_x == '':
    log_info_mssg('x size and y size from VRT ' + x_size + "," + y_size)
    exp=11 #minimum outsize 20480 for EPSG4326_2km
    while int(10*(2**exp)) < int(x_size):
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
        log_sig_warn("Target size ({0}x{1}) differs from input size ({2}x{3}), but <resize_resampling> flag has not been set.".
                     format(target_x, target_y, x_size, y_size), sigevent_url)
else: #don't bother calculating y
    if target_y == '':
        target_y=y_size
        log_info_mssg("Setting target_y from VRT to {0}".format(target_y))
    elif target_y != y_size:
        log_sig_warn("Target y size ({0}) differs from raster y size ({1})".format(target_y, y_size), sigevent_url)


#-----------------------------------------------------------------------
# Seed the MRF data file (.ppg or .pjg) with a copy of the empty tile.
if mrf_empty_tile_filename != '' and (z is None or z == 0):
    log_info_mssg('Seed the MRF data file with a copy of the empty tile.' )
    log_info_mssg(str().join(['Copy ', mrf_empty_tile_filename,' to ', out_filename]))
    shutil.copy(mrf_empty_tile_filename, out_filename)
#-----------------------------------------------------------------------

# Create the gdal_translate command.
gdal_translate_command_list=['gdal_translate', '-q', '-of', 'MRF', '-co', compress, '-co', blocksize,'-outsize', target_x, target_y]    
if compress in ["COMPRESS=JPEG", "COMPRESS=PNG", "COMPRESS=JPNG"]:
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
    if noaddo or len(alltiles) <= 1: # use UNIFORM_SCALE if empty MRF, single input, or noaddo
        gdal_translate_command_list.append('-co')
        gdal_translate_command_list.append('UNIFORM_SCALE='+str(int(overview)))
        
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
if not data_only:
    shutil.copy(vrt_filename, str().join([output_dir, basename, '.vrt']))

# Clean up temporary VRT files
for vrt in [v for v in glob.glob(str().join([working_dir, basename, '*.vrt'])) if (v not in alltiles)]:
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
            if '<Raster>' in str(lines[idx]):
                lines[idx] = str(lines[idx]).replace('<Raster>','<Raster mp_safe="on">')
                log_info_mssg("Set MRF mp_safe on")
        mrf_file.seek(0)
        mrf_file.truncate()
        mrf_file.writelines(lines)

    # Close file.
    mrf_file.close()
    # Get largest dimension, usually X.
    actual_size=max([int(sizeX), int(sizeY)])

# Insert if there are input tiles to process
if len(alltiles) > 0 and nocopy==True:
    if mrf_parallel:
        parallel_mrf_insert(alltiles, gdal_mrf_filename, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                             [target_xmin, target_ymin, target_xmax, target_ymax], target_epsg, vrtnodata, merge, working_dir, mrf_cores)
    else:
        run_mrf_insert(alltiles, gdal_mrf_filename, insert_method, resize_resampling, target_x, target_y, mrf_blocksize,
                             [target_xmin, target_ymin, target_xmax, target_ymax], target_epsg, vrtnodata, merge, working_dir, max_size=mrf_maxsize)


# Create pyramid only if idx (MRF index file) was successfully created.
idxf=get_modification_time(idx_filename)
compare_time=time.strftime('%Y%m%d.%H%M%S', time.localtime())
old_stats=os.stat(idx_filename)
if idxf >= vrtf:
    remove_file(gdal_translate_stderr_filename)

    # Run gdaladdo if noaddo==False or if we have no overviews
    if (not noaddo) or (overview_levels == '' or int(overview_levels[0]) == 0):
        # Create the gdaladdo command.
        gdaladdo_command_list=['gdaladdo', '-r', overview_resampling,
                               str(gdal_mrf_filename)]
        # Build out the list of gdaladdo pyramid levels (a.k.a. overviews).
        if overview_levels == '':
            overview=2
            gdaladdo_command_list.append(str(overview))
            exp=2
            while (overview*int(mrf_blocksize)) < actual_size:
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
        if gdaladdo_process.returncode != 0:
            log_sig_err("gdaladdo return code {0}".format(gdaladdo_process.returncode), sigevent_url)
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
    mssg = mrf_filename + ' already exists'
    log_sig_exit('ERROR', mssg, sigevent_url)

if mrf_clean:
    log_info_mssg("running mrf_clean on data file {}".format(out_filename))
    clean_mrf(out_filename)

# Rename MRFs
if mrf_name != '':
    output_mrf, output_idx, output_data, output_aux, output_vrt = get_mrf_names(out_filename, mrf_name, parameter_name, date_of_data, time_of_data)
    if (output_dir+output_mrf) != mrf_filename:
        log_info_mssg(str().join(['Moving ',mrf_filename, ' to ', output_dir+output_mrf]))
        shutil.move(mrf_filename, output_dir+output_mrf)
    if (output_dir+output_data) != out_filename:
        log_info_mssg(str().join(['Moving ',out_filename, ' to ', output_dir+output_data]))
        shutil.move(out_filename, output_dir+output_data)
    if (output_dir+output_idx) != idx_filename:
        log_info_mssg(str().join(['Moving ',idx_filename, ' to ', output_dir+output_idx]))
        shutil.move(idx_filename, output_dir+output_idx)
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
if data_only:
    remove_file(log_filename)
    remove_file(output_dir+"/"+basename+".mrf.aux.xml")
    remove_file(working_dir+"/"+basename+".configuration_file.xml")

# Remove temp tiles
working_dir_files = glob.glob(working_dir+"/*")
for tilename in (alltiles):
    if os.path.normpath(tilename) in working_dir_files:
        if tiff_compress != None:
            remove_file(tilename+'.aux.xml')
        if '_indexed.' in tilename:
            remove_file(tilename.rsplit('.',1)[0]+'.pgw')
        # Remove intermediary zen MRF files
        if mrf_compression_type.lower() == 'zen':
            if '_zen.' in tilename:
                for zen_file in glob.iglob(os.path.splitext(tilename)[0]+'*'):
                    remove_file(zen_file)

# Send to log.
mssg=str().join(['MRF created:  ', out_filename])
try:
    log_info_mssg(mssg)
    # sigevent('INFO', mssg, sigevent_url)
except urllib.error.URLError:
    None
if errors > 0:
    print("{0} errors encountered".format(errors))
    sys.exit(1)
else:
    sys.exit(0)
