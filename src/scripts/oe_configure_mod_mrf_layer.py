#!/bin/env python

# Copyright (c) 2002-2017, California Institute of Technology.
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

"""
This script creates mod_mrf Apache configurations using a layer config file.
"""

import sys
from lxml import etree
from oe_utils import log_sig_exit, log_sig_err, log_sig_warn, log_info_mssg, run_command
import requests
import math
import functools
import os
import re
import shutil
from optparse import OptionParser
from osgeo import osr
import png
from io import BytesIO

COMPRESSION_TO_MIME_AND_EXTENSION = {
    'PNG': ('image/png', '.ppg'),
    'JPEG': ('image/jpeg', '.pjg'),
    'TIF': ('image/tiff', '.ptf'),
    'LERC': ('image/lerc', '.lerc'),
    'PBF': ('application/x-protobuf;type=mapbox-vector', '.pvt'),
    'MVT': ('application/vnd.mapbox-vector-tile', '.pvt')
}


def build_mod_mrf_config(layer_config_path, tilematrixsets_config_path, archive_config_path, wmts=True, twms=True, create_gc=True, sigevent_url=None, debug=False, base_wmts_gc=None,
                            base_twms_gc=None, base_twms_get_tile_service=None):

    # Parse the config XML
    try:
        config_xml = etree.parse(layer_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open mod_mrf layer config file: {0}".format(layer_config_path), sigevent_url)
        return False
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse mod_mrf layer config file: {0}".format(layer_config_path), sigevent_url)
        return False

    # Parse the header if specified
    header_file_path = config_xml.findtext('HeaderFileName')
    header_xml = None
    if header_file_path:
        try:
            header_xml = etree.parse(header_file_path)
        except IOError:
            log_sig_exit('ERROR', "Can't open specified header file: {0}".format(header_file_path), sigevent_url)
            return False
        except etree.XMLSyntaxError:
            log_sig_exit('ERROR', "Can't parse specified header file: {0}".format(header_file_path), sigevent_url)
            return False

    # Get layer-specific stuff we need
    identifier = config_xml.findtext('Identifier')
    if not identifier:
        log_sig_warn('no <Identifier> present for layer config file, skipping: ' + layer_config_path, sigevent_url)
        return False
    if debug:
        print 'Configuring layer: ' + identifier

    mrf_size_element = config_xml.find('Size') or header_xml.find('Raster').find('Size')
    pagesize_element = config_xml.find('PageSize') or header_xml.find('Raster').find('PageSize')
    tilematrixset = config_xml.findtext('TileMatrixSet')
    empty_tile = config_xml.findtext('EmptyTile')
    empty_tile_size_element = config_xml.find('EmptyTileSize')
    if empty_tile_size_element is not None:
        empty_tile_size = empty_tile_size_element.text
        empty_tile_offset = empty_tile_size_element.attrib.get('offset') or 0

    # Get archive location
    archive_location_element = config_xml.find('ArchiveLocation')

    layer_static = False
    if archive_location_element.attrib.get('static') == 'true':
        layer_static = True
    layer_year = False
    if archive_location_element.attrib.get('year') == 'true':
        layer_year = True
    layer_root = archive_location_element.attrib.get('root')
    if not layer_root:
        log_sig_exit('ERROR', "No 'root' attribute specified in <ArchiveLocation> for layer {0}".format(identifier), sigevent_url)
        return False
    archive_location = archive_location_element.text
    if not archive_location:
        log_sig_exit('ERROR', "No <ArchiveLocation> specified for : {0}".format(identifier), sigevent_url)
        return False

    # Read archive path from archive config
    try:
        archive_xml = etree.parse(archive_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open archive location file: {0}".format(archive_config_path), sigevent_url)
        return False
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse specified header file: {0}".format(archive_config_path), sigevent_url)
        return False

    archive_path = archive_xml.xpath("/ArchiveConfiguration/Archive[@id='{0}']/Location/text()".format(layer_root))[0]
    if not archive_path:
        log_sig_exit('ERROR', "Can't find <ArchiveLocation> for root {0} in {1}".format(layer_root, archive_config_path), sigevent_url)
        return False

    filename_prefix = config_xml.findtext('FileNamePrefix') or identifier
    datafile_base_path = os.path.join(archive_path, archive_location)
    datafile_path_prefix = os.path.join(datafile_base_path, filename_prefix)

    compression = config_xml.findtext('Compression') or header_xml.find('Raster').find('Compression')
    if not compression:
        log_sig_exit('ERROR', "Can't find <Compression> in layer config: {0}".format(layer_config_path), sigevent_url)
        return False
    try:
        mime_type = COMPRESSION_TO_MIME_AND_EXTENSION[compression][0]
        datafile_extension = COMPRESSION_TO_MIME_AND_EXTENSION[compression][1]
    except KeyError:
        log_sig_exit('ERROR', "<Compression> type {0} is not recognized".format(compression), sigevent_url)

    if layer_static:
        datafile_path = datafile_path_prefix + datafile_extension
    else:
        if layer_year:
            datafile_path = datafile_base_path + '/%Y/' + filename_prefix + '_%Y%j' + datafile_extension
        else:
            datafile_path = datafile_base_path + filename_prefix + '_%Y%j' + datafile_extension

    # Parse the tilematrixsets definition file
    try:
        tilematrixset_defs_xml = etree.parse(tilematrixsets_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open tile matrix sets config file: {0}".format(tilematrixsets_config_path), sigevent_url)
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse tile matrix sets config file: {0}".format(tilematrixsets_config_path), sigevent_url)

    # Parse the environment config and get required info
    environment_config_path = config_xml.findtext('EnvironmentConfig')
    if not environment_config_path:
        log_sig_exit('ERROR', "No environment configuration file specified: " + layer_config_path, sigevent_url)
    try:
        environment_xml = etree.parse(environment_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open environment config file: {0}".format(environment_config_path), sigevent_url)
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse environment config file: {0}".format(environment_config_path), sigevent_url)
     
    wmts_staging_location = next(elem.text for elem in environment_xml.findall('StagingLocation') if elem.get('service') == 'wmts')
    if not wmts_staging_location:
        log_sig_warn('no wmts staging location specified', sigevent_url)

    twms_staging_location = next(elem.text for elem in environment_xml.findall('StagingLocation') if elem.get('service') == 'twms')
    if not twms_staging_location:
        log_sig_warn('no twms staging location specified', sigevent_url)

    wmts_service_url = next(elem.text for elem in environment_xml.findall('ServiceURL') if elem.get('service') == 'wmts')
    if not wmts_service_url:
        log_sig_warn('no wmts service URL specified', sigevent_url)

    wmts_base_endpoint = next(elem.text for elem in environment_xml.findall('GetCapabilitiesLocation') if elem.get('service') == 'wmts')
    if not wmts_base_endpoint:
        log_sig_warn('no wmts GC URL specified', sigevent_url)

    if len(environment_xml.findall('ApacheConfigLocation')) > 1:
        wmts_apache_config_location_elem = next(elem for elem in environment_xml.findall('ApacheConfigLocation') if elem.get('service') == 'wmts')
        twms_apache_config_location_elem = next(elem for elem in environment_xml.findall('ApacheConfigLocation') if elem.get('service') == 'twms')
    else:
        log_sig_exit('ERROR', 'ApacheConfigLocation missing in ' + environment_config_path, sigevent_url)
    wmts_apache_config_location = wmts_apache_config_location_elem.text
    if not wmts_apache_config_location:
        log_sig_warn('no wmts Apache config location specified', sigevent_url)
    wmts_apache_config_basename = wmts_apache_config_location_elem.get('basename')
    if not wmts_apache_config_basename:
        log_sig_warn('no wmts Apache config basename specified', sigevent_url)

    if len(environment_xml.findall('ApacheConfigHeaderLocation')) > 1:
        wmts_apache_config_header_location_elem = next(elem for elem in environment_xml.findall('ApacheConfigHeaderLocation') if elem.get('service') == 'wmts')
        twms_apache_config_header_location_elem = next(elem for elem in environment_xml.findall('ApacheConfigHeaderLocation') if elem.get('service') == 'twms')
    else:
        log_sig_exit('ERROR', 'ApacheConfigHeaderLocation missing in ' + environment_config_path, sigevent_url)
    wmts_apache_config_header_location = wmts_apache_config_header_location_elem.text
    if not wmts_apache_config_header_location:
        log_sig_warn('no wmts Apache header location specified', sigevent_url)
    wmts_apache_config_header_basename = wmts_apache_config_header_location_elem.get('basename')
    if not wmts_apache_config_header_basename:
        log_sig_warn('no wmts Apache header basename specified', sigevent_url)

    twms_base_endpoint = next(elem.text for elem in environment_xml.findall('GetCapabilitiesLocation') if elem.get('service') == 'twms')
    if not twms_base_endpoint:
        log_sig_warn('no twms GC URL specified', sigevent_url)
    if os.path.split(os.path.dirname(twms_base_endpoint))[1] == '.lib':
        twms_base_endpoint = os.path.split(os.path.dirname(twms_base_endpoint))[0]

    twms_apache_config_location = twms_apache_config_location_elem.text
    if not twms_apache_config_location:
        log_sig_warn('no twms Apache config location specified', sigevent_url)
    twms_apache_config_basename = twms_apache_config_location_elem.get('basename')
    if not twms_apache_config_basename:
        log_sig_warn('no twms Apache config basename specified', sigevent_url)

    twms_apache_config_header_location = twms_apache_config_header_location_elem.text
    if not twms_apache_config_header_location:
        log_sig_warn('no twms Apache header location specified', sigevent_url)
    twms_apache_config_header_basename = twms_apache_config_header_location_elem.get('basename')
    if not twms_apache_config_header_basename:
        log_sig_warn('no twms Apache header basename specified', sigevent_url)

    wmts_service_url = next(elem.text for elem in environment_xml.findall('ServiceURL') if elem.get('service') == 'wmts')
    if not wmts_service_url and create_gc:
        log_sig_warn('no WMTS ServiceURL specified', sigevent_url)

    twms_service_url = next(elem.text for elem in environment_xml.findall('ServiceURL') if elem.get('service') == 'twms')
    if not twms_service_url and create_gc:
        log_sig_warn('no TWMS ServiceURL specified', sigevent_url)

    if wmts:
        if mrf_size_element is None:
            log_sig_exit('ERROR', '<Size> element not present in layer config or header file for layer ' + identifier, sigevent_url)
            return False
        mrf_size_x = mrf_size_element.attrib.get('x')
        if not mrf_size_x:
            log_sig_exit('ERROR', '<Size> element is missing "x" attribute for layer ' + identifier, sigevent_url)
            return False
        mrf_size_y = mrf_size_element.attrib.get('y')
        if not mrf_size_y:
            log_sig_exit('ERROR', '<Size> element is missing "y" attribute for layer ' + identifier, sigevent_url)
            return False
        mrf_size_z = mrf_size_element.attrib.get('z') or ''
        mrf_size_c = ''
        if mrf_size_z:
            mrf_size_c = mrf_size_element.attrib.get('c') or ''

        if pagesize_element is None:
            log_sig_exit('ERROR', '<PageSize> element not present in layer config or header file for layer ' + identifier, sigevent_url)
            return False
        pagesize_x = pagesize_element.attrib.get('x')
        if not pagesize_x:
            log_sig_exit('ERROR', '<PageSize> element is missing "x" attribute for layer ' + identifier, sigevent_url)
            return False
        pagesize_y = pagesize_element.attrib.get('y')
        if not pagesize_y:
            log_sig_exit('ERROR', '<PageSize> element is missing "y" attribute for layer ' + identifier, sigevent_url)
            return False
        pagesize_z = pagesize_element.attrib.get('z') or ''
        pagesize_c = ''
        if pagesize_z:
            pagesize_c = pagesize_element.attrib.get('c') or ''

        if not tilematrixset:
            log_sig_exit('ERROR', '<TileMatrixSet> element not present in layer config for layer' + identifier, sigevent_url)
            return False

        layer_endpoint = os.path.join(wmts_base_endpoint, identifier)
        layer_style_endpoint = os.path.join(layer_endpoint, 'default')

        empty_tile_str = None
        if empty_tile:
            try:
                offset = os.path.getsize(empty_tile)
                empty_tile_str = '{0} {1} {2}'.format(offset, 0, empty_tile)
            except os.error:
                log_sig_warn("Can't read empty tile specified: " + empty_tile, sigevent_url)
        elif empty_tile_size_element is not None:
            empty_tile_str = '{0} {1}'.format(empty_tile_size, empty_tile_offset)

        # Write the source and reproject (output) configuration files
        wmts_staging_layer_path = os.path.join(wmts_staging_location, identifier)
        wmts_staging_style_path = os.path.join(wmts_staging_layer_path, "default")
        wmts_staging_path = os.path.join(wmts_staging_style_path, tilematrixset)

        if layer_static:
            regexp_str = tilematrixset + '/' + identifier + datafile_extension
        else:
            regexp_str = tilematrixset + '/\d{1,2}/\d{1,3}/\d{1,3}/' + identifier + datafile_extension

        try:
            os.makedirs(wmts_staging_path)
        except OSError:
            if not os.path.exists(wmts_staging_path):
                log_sig_exit('ERROR', 'WMTS staging location: ' + wmts_staging_path + ' cannot be created.', sigevent_url)
            pass

        cfg_filename = identifier + '.config'
        cfg_path = os.path.join(wmts_staging_path, cfg_filename)
        try:
            with open(cfg_path, 'w+') as src_cfg:
                src_cfg.write('Size {0} {1} {2} {3}\n'.format(mrf_size_x, mrf_size_y, mrf_size_z, mrf_size_c))
                src_cfg.write('DataFile {0}\n'.format(datafile_path))
                src_cfg.write('RegExp {0}\n'.format(regexp_str))
                src_cfg.write('PageSize {0} {1} {2} {3}\n'.format(pagesize_x, pagesize_y, pagesize_z, pagesize_c))
                src_cfg.write('SkippedLevels 1\n')
                src_cfg.write('EmptyTile {0}\n'.format(empty_tile_str))
                src_cfg.write('MimeType {0}\n'.format(mime_type))
        except IOError:
            log_sig_exit('ERROR', 'Cannot write layer mod_mrf config file: ' + cfg_path, sigevent_url)
            return False

        # Write Apache config snippet for TMS
        tms_path = os.path.join(layer_style_endpoint, tilematrixset)
        layer_apache_config_filename = identifier + '.conf'
        layer_apache_config_path = os.path.join(wmts_staging_location, layer_apache_config_filename)
        try:
            with open(layer_apache_config_path, 'w+') as apache_cfg:
                apache_cfg.write('<Directory {0}>\n'.format(layer_endpoint))
                apache_cfg.write('\tWMTSWrapperRole layer\n')
                if not layer_static:
                    apache_cfg.write('\tWMTSWrapperEnableTime on\n')
                apache_cfg.write('</Directory>\n')
                apache_cfg.write('<Directory {0}>\n'.format(layer_style_endpoint))
                apache_cfg.write('\tWMTSWrapperRole style\n')
                apache_cfg.write('</Directory>\n')
                apache_cfg.write('<Directory {0}>\n'.format(tms_path))
                apache_cfg.write('\tWMTSWrapperRole tilematrixset\n')
                apache_cfg.write('\tMRF On\n')
                apache_cfg.write('\tMRF_ConfigurationFile {0}\n'.format(os.path.join(tms_path, cfg_filename)))
                apache_cfg.write('</Directory>\n')
        except IOError:
            log_sig_exit('ERROR', 'Cannot write layer Apache config file: ' + layer_apache_config_path, sigevent_url)
            return False

        # Create final Apache configs (WMTS)
        endpoint_apache_config = '<Directory {0}>\n'.format(wmts_base_endpoint)
        endpoint_apache_config += '\tWMTSWrapperRole root\n'
        endpoint_apache_config += '</Directory>\n'
        apache_staging_conf_path = os.path.join(wmts_staging_location, wmts_apache_config_basename + '.conf')
        try:
            with open(apache_staging_conf_path, 'w+') as wmts_apache_config_file:
                # Write header to Apache config
                wmts_apache_header_path = os.path.join(wmts_apache_config_header_location, wmts_apache_config_header_basename + '.conf')
                try:
                    with open(wmts_apache_header_path, 'r') as header:
                        wmts_apache_config_file.write(header.read())
                except IOError:
                    log_sig_warn("Can't open WMTS reproject Apache header file: " + wmts_apache_header_path, sigevent_url)

                # Write endpoint Apache stuff
                wmts_apache_config_file.write(endpoint_apache_config)

                # Write individual layer chunks
                layer_snippets = [os.path.join(wmts_staging_location, sfile)
                          for sfile in sorted(os.listdir(wmts_staging_location), key=str.lower)
                          if sfile.endswith('.conf') and not sfile.startswith(wmts_apache_config_basename)]
                for layer_path in layer_snippets:
                    with open(layer_path, 'r') as f:
                        wmts_apache_config_file.write(f.read())
        except IOError:
            log_sig_exit('ERROR', "Can't write mod_mrf staging apache config: " + apache_staging_conf_path, sigevent_url)
            return False

        return True

        # if twms:
        #     try:
        #         twms_gc_staging_snippet = os.path.join(twms_staging_location, identifier + '_gc.xml')
        #         # Open layer XML file
        #         twms_gc_xml = open(twms_gc_staging_snippet, 'w+')
        #     except IOError:
        #         mssg=str().join(['Cannot read layer XML file:  ', 
        #                          twms_gc_staging_snippet])
        #         log_sig_exit('ERROR', mssg, sigevent_url)

        #     twms_gc_layer_template = """<Layer queryable=\"0\">
        #     <Name>$Identifier</Name>
        #     <Title xml:lang=\"en\">$Title</Title>
        #     <Abstract xml:lang=\"en\">$Abstract</Abstract>
        #     <LatLonBoundingBox minx=\"$minx\" miny=\"$miny\" maxx=\"$maxx\" maxy=\"$maxy\"/>
        #     <Style>
        #         <Name>default</Name> <Title xml:lang=\"en\">(default) Default style</Title>
        #     </Style>
        #     <ScaleHint min=\"10\" max=\"100\"/> <MinScaleDenominator>100</MinScaleDenominator>
        #     </Layer>"""

        #     layer_output = ""
        #     lines = twms_gc_layer_template.splitlines(True)
        #     for line in lines:
        #         # replace lines in template
        #         if '</Layer>' in line:
        #             line = ' '+line+'\n'  
        #         if '$Identifier' in line:
        #             line = line.replace("$Identifier",identifier)              
        #         if '$Title' in line:
        #             line = line.replace("$Title", src_title)
        #         # if '$Abstract' in line:
        #         #     line = line.replace("$Abstract", abstract)
        #         if '$minx' in line:
        #             line = line.replace("$minx", str(-dest_top_left_corner[0]))
        #         if '$miny' in line:
        #             line = line.replace("$miny", str(-dest_top_left_corner[0]))
        #         if '$maxx' in line:
        #             line = line.replace("$maxx", str(dest_top_left_corner[0]))
        #         if '$maxy' in line:
        #             line = line.replace("$maxy", str(dest_top_left_corner[0]))
        #         layer_output = layer_output + line
        #     twms_gc_xml.writelines(layer_output)
        #     twms_gc_xml.close()

        #     twms_gts_layer_template = """<TiledGroup>
        #     <Name>$TiledGroupName</Name>
        #     <Title xml:lang=\"en\">$Title</Title>
        #     <Abstract xml:lang=\"en\">$Abstract</Abstract>
        #     <Projection>$Projection</Projection>
        #     <Pad>0</Pad>
        #     <Bands>$Bands</Bands>
        #     <LatLonBoundingBox minx=\"$minx\" miny=\"$miny\" maxx=\"$maxx\" maxy=\"$maxy\" />
        #     <Key>${time}</Key>
        #     $Patterns</TiledGroup>"""
        
        #     try:
        #         twms_gts_staging_snippet = os.path.join(twms_staging_location, identifier + '_gts.xml')
        #         # Open layer XML file
        #         twms_gts_xml = open(twms_gts_staging_snippet, 'w+')
        #     except IOError:
        #         mssg=str().join(['Cannot read layer XML file:  ', 
        #                          twms_gts_staging_snippet])
        #         log_sig_exit('ERROR', mssg, sigevent_url)

        #     proj = osr.SpatialReference()
        #     proj.ImportFromEPSG(3857)

        #     layer_output = ""
        #     lines = twms_gts_layer_template.splitlines(True)
        #     for line in lines:
        #         # replace lines in template 
        #         if '</TiledGroup>' in line:
        #             line = ' '+line+'\n'              
        #         if '$TiledGroupName' in line:
        #             line = line.replace('$TiledGroupName', identifier + 'tileset')
        #         if '$Title' in line:
        #             line = line.replace("$Title", src_title)
        #         if '$Abstract' in line:
        #             # line = line.replace("$Abstract",abstract)
        #             line = line.replace("$Abstract", '')
        #         if '$Projection' in line:
        #             line = line.replace("$Projection", proj.ExportToWkt())
        #         if '$Bands' in line:
        #             if src_format == 'image/png':
        #                 line = line.replace("$Bands","4") # GDAL wants 4 for PNGs
        #             else:
        #                 line = line.replace("$Bands","3")
        #         if '$minx' in line:
        #             line = line.replace("$minx", str(-dest_top_left_corner[0]))
        #         if '$miny' in line:
        #             line = line.replace("$miny", str(-dest_top_left_corner[0]))
        #         if '$maxx' in line:
        #             line = line.replace("$maxx", str(dest_top_left_corner[0]))
        #         if '$maxy' in line:
        #             line = line.replace("$maxy", str(dest_top_left_corner[0]))
        #         if '$Patterns' in line:
        #             patterns = ""
        #         #     cmd = depth + '/oe_create_cache_config -p ' + twms_mrf_filename
        #         #     try:
        #         #         print '\nRunning command: ' + cmd
        #         #         process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #         #         process.wait()
        #         #         for output in process.stdout:
        #         #             patterns = patterns + output
        #         #     except:
        #         #         log_sig_err("Error running command " + cmd, sigevent_url)
        #             line = line.replace("$Patterns",patterns)
        #         layer_output = layer_output + line
        #     twms_gts_xml.writelines(layer_output)
        #     twms_gts_xml.close()

    # # Final routines (after all layers have been processed)
    # if wmts:
    #     # Copy all the WMTS config files to the endpoint
    #     layer_dirs = [subdir for subdir in os.listdir(wmts_staging_location) if os.path.isdir(os.path.join(wmts_staging_location, subdir))]
    #     for layer_dir in layer_dirs:
    #         layer_endpoint = os.path.join(wmts_base_endpoint, layer_dir)
    #         if os.path.exists(layer_endpoint):
    #             shutil.rmtree(layer_endpoint)
    #         layer_staging_path = os.path.join(wmts_staging_location, layer_dir)
    #         print '\nCopying reprojected WMTS layer directories: {0} -> {1} '.format(layer_staging_path, layer_endpoint)
    #         shutil.copytree(layer_staging_path, layer_endpoint)

    #     # Copy the WMTS Apache config to the specified directory (like conf.d)
    #     apache_conf_path = os.path.join(wmts_apache_config_location, wmts_apache_config_basename + '.conf')
    #     print '\nCopying reprojected WMTS layer Apache config {0} -> {1}'.format(apache_staging_conf_path, apache_conf_path)
    #     try:
    #         shutil.copyfile(apache_staging_conf_path, apache_conf_path)
    #     except IOError, e: # Try with sudo if permission denied
    #         if 'Permission denied' in str(e):
    #             cmd = ['sudo', 'cp', apache_staging_conf_path, apache_conf_path]
    #             try:
    #                 run_command(cmd, sigevent_url)
    #             except Exception, e:
    #                 log_sig_exit('ERROR', str(e), sigevent_url)

    #     # Configure GetCapabilties (routine copied from oe_configure_layer)
    #     try:
    #         # Copy and open base GetCapabilities.
    #         getCapabilities_file = os.path.join(wmts_staging_location, 'getCapabilities.xml')
    #         if not base_wmts_gc:
    #             log_sig_exit('ERROR', 'WMTS GetCapabilities creation selected but no base GC file specified.', sigevent_url)
    #         shutil.copyfile(base_wmts_gc, getCapabilities_file)
    #         getCapabilities_base = open(getCapabilities_file, 'r+')
    #     except IOError:
    #         log_sig_exit('ERROR', 'Cannot read getcapabilities_base_wmts.xml file: ' + base_wmts_gc, sigevent_url)
    #     else:
    #         lines = getCapabilities_base.readlines()
    #         for idx in range(0, len(lines)):
    #             if '<ows:Get' in lines[idx]:
    #                 spaces = lines[idx].index('<')
    #                 getUrlLine = lines[idx].replace('ows:Get','Get xmlns:xlink="http://www.w3.org/1999/xlink"').replace('>','/>')
    #                 getUrl = etree.fromstring(getUrlLine)
    #                 if '1.0.0/WMTSCapabilities.xml' in lines[idx]:
    #                     getUrl.attrib[xlink + 'href'] = wmts_service_url + '1.0.0/WMTSCapabilities.xml'
    #                 elif 'wmts.cgi?' in lines[idx]:
    #                     getUrl.attrib[xlink + 'href'] = wmts_service_url + 'wmts.cgi?'
    #                 else:
    #                     getUrl.attrib[xlink + 'href'] = wmts_service_url
    #                 lines[idx] = (' '*spaces) + etree.tostring(getUrl, pretty_print=True).replace('Get','ows:Get').replace(' xmlns:xlink="http://www.w3.org/1999/xlink"','').replace('/>','>')
    #             if 'ServiceMetadataURL' in lines[idx]:
    #                 spaces = lines[idx].index('<')
    #                 serviceMetadataUrlLine = lines[idx].replace('ServiceMetadataURL','ServiceMetadataURL xmlns:xlink="http://www.w3.org/1999/xlink"')
    #                 serviceMetadataUrl = etree.fromstring(serviceMetadataUrlLine)
    #                 serviceMetadataUrl.attrib[xlink + 'href'] = wmts_service_url + '1.0.0/WMTSCapabilities.xml'
    #                 lines[idx] = (' '*spaces) + etree.tostring(serviceMetadataUrl, pretty_print=True).replace(' xmlns:xlink="http://www.w3.org/1999/xlink"','')
    #         getCapabilities_base.seek(0)
    #         getCapabilities_base.truncate()
    #         getCapabilities_base.writelines(lines)
    #         getCapabilities_base.close()   

    # if twms:
    #     # Create final Apache configs (TWMS)
    #     twms_apache_conf_path_template = os.path.join(twms_base_endpoint, '${layer}/twms.config')
    #     twms_endpoint_apache_config = '<Directory {0}>\n'.format(twms_base_endpoint)
    #     twms_endpoint_apache_config += '\ttWMS_RegExp twms.cgi\n'
    #     twms_endpoint_apache_config += '\ttWMS_ConfigurationFile {0}\n'.format(twms_apache_conf_path_template)
    #     twms_endpoint_apache_config += '</Directory>\n'
    #     twms_apache_staging_conf_path = os.path.join(twms_staging_location, twms_apache_config_basename + '.conf')
    #     try:
    #         with open(twms_apache_staging_conf_path, 'w+') as twms_apache_config_file:
    #             # Write header to Apache config
    #             try:
    #                 with open(os.path.join(twms_apache_config_header_location, twms_apache_config_header_basename + '.conf'), 'r') as header:
    #                     twms_apache_config_file.write(header.read())
    #             except IOError:
    #                 log_sig_warn("Can't find TWMS reproject Apache header file: " + twms_apache_staging_conf_path)

    #             # Write endpoint Apache stuff
    #             twms_apache_config_file.write(twms_endpoint_apache_config)

    #     except IOError:
    #         log_sig_exit('ERROR', "Can't write TWMS staging apache conf: " + twms_apache_staging_conf_path, sigevent_url)

    #     # Copy all the TWMS config files to the endpoint
    #     layer_dirs = [subdir for subdir in os.listdir(twms_staging_location) if os.path.isdir(os.path.join(twms_staging_location, subdir))]
    #     for layer_dir in layer_dirs:
    #         layer_endpoint = os.path.join(twms_base_endpoint, layer_dir)
    #         if os.path.exists(layer_endpoint):
    #             shutil.rmtree(layer_endpoint)
    #         layer_staging_path = os.path.join(twms_staging_location, layer_dir)
    #         print '\nCopying reprojected TWMS layer directories: {0} -> {1} '.format(layer_staging_path, layer_endpoint)
    #         shutil.copytree(layer_staging_path, layer_endpoint)

    #     # Copy the TWMS Apache config to the specified directory (like conf.d)
    #     twms_apache_conf_path = os.path.join(twms_apache_config_location, twms_apache_config_basename + '.conf')
    #     print '\nCopying reprojected TWMS layer Apache config {0} -> {1}'.format(twms_apache_staging_conf_path, twms_apache_conf_path)
    #     try:
    #         shutil.copyfile(twms_apache_staging_conf_path, twms_apache_conf_path)
    #     except IOError, e: # Try with sudo if permission denied
    #         if 'Permission denied' in str(e):
    #             cmd = ['sudo', 'cp', twms_apache_staging_conf_path, twms_apache_conf_path]
    #             try:
    #                 run_command(cmd, sigevent_url)
    #             except Exception, e:
    #                 log_sig_exit('ERROR', str(e), sigevent_url)

    #     # Configure base GC file for TWMS
    #     if create_gc:
    #         try:
    #             # Copy and open base GetCapabilities.
    #             getCapabilities_file = os.path.join(twms_staging_location, 'getCapabilities.xml')
    #             if not base_twms_gc:
    #                 log_sig_exit('ERROR', 'TWMS GetCapabilities creation selected but no base GC file specified.', sigevent_url)
    #             shutil.copyfile(base_twms_gc, getCapabilities_file)
    #             getCapabilities_base = open(getCapabilities_file, 'r+')
    #         except IOError:
    #             log_sig_exit('ERROR', 'Cannot read getcapabilities_base_twms.xml file: ' + base_twms_gc, sigevent_url)
    #         else:
    #             lines = getCapabilities_base.readlines()
    #             for idx in range(0, len(lines)):
    #                 if '<SRS></SRS>' in lines[idx]:
    #                     lines[idx] =  lines[idx].replace('<SRS></SRS>', '<SRS>EPSG:3857</SRS>')
    #                 if '<CRS></CRS>' in lines[idx]:
    #                     lines[idx] =  lines[idx].replace('<CRS></CRS>', '<CRS>EPSG:3857</CRS>')
    #                 if 'OnlineResource' in lines[idx]:
    #                     spaces = lines[idx].index('<')
    #                     onlineResource = etree.fromstring(lines[idx])
    #                     if 'KeywordList' in lines[idx - 1]:
    #                         onlineResource.attrib[xlink + 'href'] = twms_service_url  # don't include the cgi portion
    #                     else:
    #                         onlineResource.attrib[xlink + 'href'] = twms_service_url + "twms.cgi?"
    #                     lines[idx] = (' '*spaces) + etree.tostring(onlineResource, pretty_print=True)
    #             getCapabilities_base.seek(0)
    #             getCapabilities_base.truncate()
    #             getCapabilities_base.writelines(lines)
    #             getCapabilities_base.close()

    #         try:
    #             # Copy and open base GetTileService.
    #             getTileService_file = os.path.join(twms_staging_location, 'getTileService.xml')
    #             if not base_twms_get_tile_service:
    #                 log_sig_exit('ERROR', 'TWMS GetTileService creation selected but no base GetTileService file specified.', sigevent_url)
    #             shutil.copyfile(base_twms_get_tile_service, getTileService_file)
    #             getTileService_base = open(getTileService_file, 'r+')
    #         except IOError:
    #             log_sig_exit('ERROR', 'Cannot read gettileservice_base.xml file: ' + getTileService_file, sigevent_url)
    #         else:
    #             lines = getTileService_base.readlines()
    #             for idx in range(0, len(lines)):
    #                 if 'BoundingBox' in lines[idx]:
    #                     lines[idx] = lines[idx].replace("BoundingBox","LatLonBoundingBox").replace("{minx}", '-20037508.34278925').replace("{miny}", '-20037508.34278925').replace("{maxx}", '20037508.34278925').replace("{maxy}", '20037508.34278925')
    #                 if 'OnlineResource' in lines[idx]:
    #                     spaces = lines[idx].index('<')
    #                     onlineResource = etree.fromstring(lines[idx])
    #                     if 'KeywordList' in lines[idx-1]:
    #                         onlineResource.attrib[xlink + 'href'] = twms_service_url  # don't include the cgi portion
    #                     else:
    #                         onlineResource.attrib[xlink + 'href'] = twms_service_url + "twms.cgi?"
    #                     lines[idx] = (' '*spaces) + etree.tostring(onlineResource, pretty_print=True)
    #             getTileService_base.seek(0)
    #             getTileService_base.truncate()
    #             getTileService_base.writelines(lines)
    #             getTileService_base.close()
    # return

# Main routine to be run in CLI mode
if __name__ == '__main__':
    print 'OnEarth Reproject layer config tool (for use with mod_reproject)'

    if 'LCDIR' not in os.environ:
        print 'LCDIR environment variable not set.\nLCDIR should point to your OnEarth layer_config directory.\n'
        lcdir = os.path.abspath(os.path.dirname(__file__) + '/..')
    else:
        lcdir = os.environ['LCDIR']

    usageText = 'oe_configure_layer.py --conf_file [layer_configuration_file.xml] --lcdir [$LCDIR] --no_xml --sigevent_url [url] --no_twms --no_wmts'

    # Define command line options and args.
    parser = OptionParser(usage=usageText)
    parser.add_option('-c', '--conf_file',
                      action='store', type='string', dest='layer_config_path',
                      help='Full path of layer configuration filename.')
    parser.add_option('-l', '--lcdir',
                      action='store', type='string', dest='lcdir',
                      default=lcdir,
                      help='Full path of the OnEarth Layer Configurator (layer_config) directory.  Default: $LCDIR')
    parser.add_option('-m', '--tilematrixset_config',
                      action='store', type='string', dest='tilematrixsets_config_path',
                      help='Full path of TileMatrixSet configuration file.  Default: $LCDIR/conf/tilematrixsets.xml')
    parser.add_option("-n", "--no_twms",
                      action="store_true", dest="no_twms",
                      default=False, help="Do not use configurations for Tiled-WMS")
    parser.add_option('-s', '--sigevent_url',
                      action='store', type='string', dest='sigevent_url',
                      default='http://localhost:8100/sigevent/events/create',
                      help='Default:  http://localhost:8100/sigevent/events/create')
    parser.add_option("-w", "--no_wmts",
                      action="store_true", dest="no_wmts",
                      default=False, help="Do not use configurations for WMTS.")
    parser.add_option("-x", "--no_xml",
                      action="store_true", dest="no_xml",
                      default=False, help="Do not generate getCapabilities and getTileService XML.")
    parser.add_option("--debug",
                      action="store_true", dest="debug",
                      default=False, help="Produce verbose debug messages")
    parser.add_option("--archive_config",
                      action="store", dest="archive_config_path",
                      default=False, help='Full path of archive configuration file.  Default: $LCDIR/conf/archive.xml')


    # Read command line args.
    (options, args) = parser.parse_args()
    # Command line set LCDIR.
    lcdir = options.lcdir
    # No XML configurations (getCapabilities, getTileService)
    xml = not options.no_xml
    # No Tiled-WMS configuration.
    twms = not options.no_twms
    # No WMTS configuration.
    wmts = not options.no_wmts
    # TileMatrixSet configurations
    if options.tilematrixsets_config_path:
        tilematrixsets_config_path = options.tilematrixsets_config_path
    else:
        tilematrixsets_config_path = lcdir + '/conf/tilematrixsets.xml'
    
    if options.archive_config_path:
        archive_config_path = options.archive_config_path
    else:
        archive_config_path = lcdir + '/conf/archive.xml'

    layer_config_path = options.layer_config_path
    if not layer_config_path:
        print 'No layer config XML specified'
        sys.exit()

    # Sigevent URL.
    sigevent_url = options.sigevent_url

    base_twms_gc = os.path.join(lcdir, '/conf/getcapabilities_base_twms.xml')
    base_twms_get_tile_service = os.path.join(lcdir, '/conf/gettileservice_base.xml')
    base_wmts_gc = os.path.join(lcdir, '/conf/getcapabilities_base_wmts.xml')
      
    print 'Using ' + lcdir + ' as $LCDIR.'

    if not xml:
        log_info_mssg("no_xml specified, getCapabilities and getTileService files will be staged only")

    build_mod_mrf_config(layer_config_path, tilematrixsets_config_path, archive_config_path, base_wmts_gc=base_wmts_gc, base_twms_gc=base_twms_gc,
                            base_twms_get_tile_service=base_twms_get_tile_service, wmts=wmts, twms=twms, create_gc=xml, sigevent_url=sigevent_url, debug=options.debug)