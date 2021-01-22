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
This script creates mod_reproject Apache configurations using a remote GetCapabilities file. It can be used on its own or
with oe_configure_layer.
"""

import sys
from lxml import etree
from oe_utils import add_trailing_slash, log_sig_exit, log_sig_err, log_sig_warn, log_info_mssg, run_command, bulk_replace
import requests
import math
import functools
import os
import re
import shutil
from optparse import OptionParser
from osgeo import osr, ogr
import png
from io import BytesIO
from time import asctime
import cgi
import hashlib
from decimal import Decimal
import copy

reload(sys)
sys.setdefaultencoding('utf8')

EARTH_RADIUS = 6378137.0
MIME_TO_EXTENSION = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tiff',
    'image/lerc': '.lerc',
    'application/vnd.mapbox-vector-tile': '.mvt'
}

TILE_LEVELS = {
    '4326': {'16km': '2', '8km': '3', '4km': '4', '2km': '5', '1km': '6', '500m': '7', '250m': '8',
                  '125m': '9', '62.5m': '10', '31.25m': '11', '15.625m': '12'},
    '3413': {'1km': '3', '500m': '4', '250m': '5', '125m': '6', '62.5m': '7', '31.25m': '8', '15.625m': '9'},
    '3031': {'1km': '3', '500m': '4', '250m': '5', '125m': '6', '62.5m': '7', '31.25m': '8', '15.625m': '9'}
}


MAPFILE_TEMPLATE = """LAYER
        NAME    "{layer_name}"
        TYPE    RASTER
        STATUS  ON
        METADATA
                "wms_title"             "{layer_title}"
                "wms_srs"               "EPSG:{target_epsg}"
                "wms_extent"            "{target_bbox}"
                {wms_layer_group_info}
                {dimension_info}
                {style_info}
        END
        DATA    '{data_xml}'
        PROJECTION
                "init=epsg:{src_epsg}"
        END
        {validation_info}
END
"""

WMS_LAYER_GROUP_TEMPLATE = """"wms_layer_group" "{wms_layer_group}"
"""

DIMENSION_TEMPLATE = """"wms_timeextent" "{periods}"
                "wms_timeitem" "TIME"
                "wms_timedefault" "{default}"
                "wms_timeformat" "YYYY-MM-DD, YYYY-MM-DDTHH:MM:SSZ"
"""

STYLE_TEMPLATE = """"wms_style" "default"
                "wms_style_default_legendurl_width" "{width}"
                "wms_style_default_legendurl_height" "{height}"
                "wms_style_default_legendurl_format" "image/png"
                "wms_style_default_legendurl_href" "{href}"
"""

VALIDATION_TEMPLATE = """
        VALIDATION
            "time"                  "^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z|[0-9]{4}-[0-9]{2}-[0-9]{2})|(default)$"
            "default_time"          "{default}"
        END
"""


versionNumber = '1.3.8'

def get_epsg_code_for_proj_string(proj_string):
    # For some reason OSR can't parse this version of the 3857 CRS.
    if proj_string == 'urn:ogc:def:crs:EPSG:6.18:3:3857':
        return '3857'
    proj = osr.SpatialReference()
    proj.SetFromUserInput(proj_string)
    return proj.GetAuthorityCode(None)


# Returns [llx, lly, urx, ury]
def get_bbox_for_proj_string(proj_string, use_oe_tms=False, get_in_map_units=False):
    epsg_code = get_epsg_code_for_proj_string(proj_string)

    if epsg_code == '4326':
        if use_oe_tms:
            return [-180, -198, 396.0, 90]
        else:
            return [-180, -90, 180, 90]
    bbox = get_proj_bbox(epsg_code)
    if not get_in_map_units:
        return bbox

    src_proj = osr.SpatialReference()
    src_proj.SetFromUserInput('EPSG:4326')
    target_proj = osr.SpatialReference()
    target_proj.ImportFromEPSG(int(epsg_code))
    transform = osr.CoordinateTransformation(src_proj, target_proj)

    point_coords = [(bbox[0], bbox[3]), (bbox[2], bbox[1])]
    new_bbox = []
    for coords in point_coords:
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(coords[0], coords[1])
        point.Transform(transform)
        new_bbox.append(point.GetX())
        new_bbox.append(point.GetY())
    return [new_bbox[0], new_bbox[3], new_bbox[1], new_bbox[2]]


# Returns [llx, lly, urx, ury]
def get_proj_bbox(epsg_code):
    if epsg_code == '4326':
        return [-180.0, -90.0, 180.0, 90.0]
    elif epsg_code == '3857':
        return [-180, -85.06, 180.0, 85.06]
    elif epsg_code == '3413':
        return [-4194304.0, -4194304.0, 4194304.0, 4194304.0]
    elif epsg_code == '3031':
        return [-4194304.0, -4194304.0, 4194304.0, 4194304.0]
    else:
        print "WARNING: unsupported <TargetEpsgCode> specified ({0}). Only 4326, 3857, 3413, and 3031 are supported.".format(epsg_code)
        return None


def make_gdal_tms_xml(layer, bands, src_epsg, **kwargs):

    bbox = map(str, get_bbox_for_proj_string(
        'EPSG:' + src_epsg, use_oe_tms=True, get_in_map_units=(src_epsg not in ['4326','3413','3031'])))

    if "tms" in kwargs:
        tms = kwargs["tms"]
    else:
        tms = layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')

    if "template_string" in kwargs:
        template_string = kwargs["template_string"]
    else:
        template_string = None
        for resource_url in layer.findall('{*}ResourceURL'):
            template = resource_url.get('template')

            # If we've found the Resource URL with {Time} take it and be done
            if "{Time}" in template:
                template_string = template
                break
            # Else if this is the first item in the list, keep it for now
            elif template_string is None:
                template_string = template
            # Else if we found the "default/{TileMatrixSet}" Resource URL; Choose that over the other
            elif "default/{TileMatrixSet}" in template:
                template_string = template

    out_root = etree.Element('GDAL_WMS')

    service_element = etree.SubElement(out_root, 'Service')
    service_element.set('name', 'TMS')
    etree.SubElement(service_element, 'ServerUrl').text = bulk_replace(template_string, [
        ('{TileMatrixSet}', tms), ('{Time}', '%time%'), ('{TileMatrix}','${z}'), ('{TileRow}', '${y}'), ('{TileCol}', '${x}')])

    data_window_element = etree.SubElement(out_root, 'DataWindow')
    etree.SubElement(data_window_element, 'UpperLeftX').text = bbox[0]
    etree.SubElement(data_window_element, 'UpperLeftY').text = bbox[3]
    etree.SubElement(data_window_element, 'LowerRightX').text = bbox[2]
    etree.SubElement(data_window_element, 'LowerRightY').text = bbox[1]
    if src_epsg == '3857':
        tile_levels = tms.split('GoogleMapsCompatible_Level')[1]
    else:
        try:
            tile_levels = TILE_LEVELS[src_epsg][tms]
        except KeyError:
            print("ERROR:" + tms + " is not a valid TileMatrixSet for EPSG:" + src_epsg)
            exit

    etree.SubElement(data_window_element, 'TileLevel').text = tile_levels
    etree.SubElement(data_window_element, 'TileCountX').text = '2' if src_epsg in ['4326','3413','3031'] else '1'
    etree.SubElement(data_window_element, 'TileCountY').text = '2' if src_epsg in ['3413','3031'] else '1'
    etree.SubElement(data_window_element, 'YOrigin').text = 'top'

    etree.SubElement(out_root, 'Projection').text = 'EPSG:' + src_epsg
    tile_size = '512' if src_epsg in ['4326','3413','3031'] else '256'
    etree.SubElement(out_root, 'BlockSizeX').text = tile_size
    etree.SubElement(out_root, 'BlockSizeY').text = tile_size
    etree.SubElement(out_root, 'BandsCount').text = str(bands)

    etree.SubElement(out_root, 'Cache')
    etree.SubElement(out_root, 'ZeroBlockHttpCodes').text = '404,400'
    etree.SubElement(out_root, 'ZeroBlockOnServerException').text = 'true'

    return etree.tostring(out_root)


def sort_tilematrixset(tilematrixset):
    return sorted([elem for elem in tilematrixset.findall('{*}TileMatrix')], key=lambda matrix: float(matrix.findtext('{*}ScaleDenominator')))


def get_ext_for_file_type(file_type):
    try:
        return MIME_TO_EXTENSION[file_type]
    except KeyError:
        return None


def scale_denominator_reduce(previous, current, src_scale_denominator):
    current_scale_denominator = get_max_scale_dem(current)
    if previous is None:
        if current_scale_denominator > src_scale_denominator:
            return current
        else:
            return None
    previous_scale_denominator = get_max_scale_dem(previous)
    if current_scale_denominator < src_scale_denominator or current_scale_denominator > previous_scale_denominator:
        return previous
    return current


def get_max_scale_dem(tilematrixset):
    return float(sort_tilematrixset(tilematrixset)[0].findtext('{*}ScaleDenominator'))


def build_reproject_configs(layer_config_path, tilematrixsets_config_path, wmts=True, twms=True, create_gc=True, sigevent_url=None, stage_only=False, debug=False, base_wmts_gc=None,
                            base_twms_gc=None, base_twms_get_tile_service=None, create_mapfile=False):
    # Track errors and warnings
    warnings = []
    errors = []

    # Parse the config XML
    try:
        config_xml = etree.parse(layer_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open reproject layer config file: {0}".format(
            layer_config_path), sigevent_url)
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse reproject layer config file: {0}".format(
            layer_config_path), sigevent_url)

    src_locations = config_xml.findall('SrcLocationRewrite')
    gc_uri = config_xml.findtext('SrcWMTSGetCapabilitiesURI')
    if not gc_uri:
        log_sig_exit('ERROR:', '<SrcWMTSGetCapabilitiesURI> not present in reprojection config file: {0}'.format(
            layer_config_path), sigevent_url)
    layer_exclude_list = [
        name.text for name in config_xml.findall('ExcludeLayer')]
    layer_include_list = [
        name.text for name in config_xml.findall('IncludeLayer')]
    target_epsg = config_xml.findtext('TargetEpsgCode')
    if target_epsg and target_epsg.startswith('EPSG:'):
        target_epsg = target_epsg.split(':')[1]

    # Parse the tilematrixsets definition file
    try:
        tilematrixset_defs_xml = etree.parse(tilematrixsets_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open tile matrix sets config file: {0}".format(
            tilematrixsets_config_path), sigevent_url)
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse tile matrix sets config file: {0}".format(
            tilematrixsets_config_path), sigevent_url)

    # Parse the environment config and get required info
    environment_config_path = config_xml.findtext('EnvironmentConfig')
    if not environment_config_path:
        log_sig_exit('ERROR', "No environment configuration file specified: " +
                     layer_config_path, sigevent_url)
    try:
        environment_xml = etree.parse(environment_config_path)
    except IOError:
        log_sig_exit('ERROR', "Can't open environment config file: {0}".format(
            environment_config_path), sigevent_url)
    except etree.XMLSyntaxError:
        log_sig_exit('ERROR', "Can't parse environment config file: {0}".format(
            environment_config_path), sigevent_url)

    wmts_staging_location = next(elem.text for elem in environment_xml.findall(
        'StagingLocation') if elem.get('service') == 'wmts')
    if not wmts_staging_location:
        mssg = 'no wmts staging location specified'
        warnings.append(asctime() + " " + mssg)
        log_sig_warn(mssg, sigevent_url)

    twms_staging_location = next(elem.text for elem in environment_xml.findall(
        'StagingLocation') if elem.get('service') == 'twms')
    if not twms_staging_location:
        mssg = 'no twms staging location specified'
        warnings.append(asctime() + " " + mssg)
        log_sig_warn(mssg, sigevent_url)

    if len(environment_xml.findall('ReprojectEndpoint')) > 0:
        try:
            wmts_reproject_endpoint = next(elem.text for elem in environment_xml.findall(
                'ReprojectEndpoint') if elem.get('service') == 'wmts')
            if not wmts_reproject_endpoint.startswith('/'):
                wmts_reproject_endpoint = '/' + wmts_reproject_endpoint
        except StopIteration:
            wmts_reproject_endpoint = None
        try:
            twms_reproject_endpoint = next(elem.text for elem in environment_xml.findall(
                'ReprojectEndpoint') if elem.get('service') == 'twms')
            if not twms_reproject_endpoint.startswith('/'):
                twms_reproject_endpoint = '/' + twms_reproject_endpoint
        except StopIteration:
            twms_reproject_endpoint = None
        if not wmts_reproject_endpoint:
            mssg = 'no wmts reproject endpoint specified in ' + environment_config_path
            errors.append(asctime() + " " + mssg)
            if twms:  # TWMS requires the WMTS reproject endpoint to be defined
                log_sig_exit('ERROR', mssg, sigevent_url)
            else:
                log_sig_err(mssg, sigevent_url)
        if not twms_reproject_endpoint:
            mssg = 'no twms reproject endpoint specified in ' + environment_config_path
            errors.append(asctime() + " " + mssg)
            log_sig_err(mssg, sigevent_url)
    elif wmts or twms:
        log_sig_exit('ERROR', 'no ReprojectEndpoint specified in ' +
                     environment_config_path, sigevent_url)

    if wmts:
        wmts_service_url = next(elem.text for elem in environment_xml.findall(
            'ServiceURL') if elem.get('service') == 'wmts')
        if not wmts_service_url:
            mssg = 'no wmts service URL specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        wmts_base_endpoint = next(elem.text for elem in environment_xml.findall(
            'ReprojectLayerConfigLocation') if elem.get('service') == 'wmts')
        if not wmts_base_endpoint:
            mssg = 'no wmts GC URL specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        if len(environment_xml.findall('ReprojectApacheConfigLocation')) > 1:
            wmts_apache_config_location_elem = next(elem for elem in environment_xml.findall(
                'ReprojectApacheConfigLocation') if elem.get('service') == 'wmts')
        else:
            log_sig_exit('ERROR', 'ReprojectApacheConfigLocation missing in ' +
                         environment_config_path, sigevent_url)

        wmts_apache_config_location = wmts_apache_config_location_elem.text
        if not wmts_apache_config_location:
            mssg = 'no wmts Apache config location specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)
        wmts_apache_config_basename = wmts_apache_config_location_elem.get(
            'basename')
        if not wmts_apache_config_basename:
            mssg = 'no wmts Apache config basename specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        wmts_service_url = next(elem.text for elem in environment_xml.findall(
            'ServiceURL') if elem.get('service') == 'wmts')
        if not wmts_service_url and create_gc:
            mssg = 'no WMTS ServiceURL specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

    if twms:
        twms_base_endpoint = next(elem.text for elem in environment_xml.findall(
            'ReprojectLayerConfigLocation') if elem.get('service') == 'twms')
        if not twms_base_endpoint:
            mssg = 'no twms GC URL specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)
        if twms_base_endpoint and os.path.split(os.path.dirname(twms_base_endpoint))[1] == '.lib':
            twms_base_endpoint = os.path.split(
                os.path.dirname(twms_base_endpoint))[0]

        if len(environment_xml.findall('ReprojectApacheConfigLocation')) > 1:
            twms_apache_config_location_elem = next(elem for elem in environment_xml.findall(
                'ReprojectApacheConfigLocation') if elem.get('service') == 'twms')
        else:
            log_sig_exit('ERROR', 'ReprojectApacheConfigLocation missing in ' +
                         environment_config_path, sigevent_url)

        twms_apache_config_location = twms_apache_config_location_elem.text
        if not twms_apache_config_location:
            mssg = 'no twms Apache config location specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)
        twms_apache_config_basename = twms_apache_config_location_elem.get(
            'basename')
        if not twms_apache_config_basename:
            mssg = 'no twms Apache config basename specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        twms_service_url = next(elem.text for elem in environment_xml.findall(
            'ServiceURL') if elem.get('service') == 'twms')
        if not twms_service_url and create_gc:
            mssg = 'no TWMS ServiceURL specified'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

    if create_mapfile:
        # Check for all required config info
        mapfile_location = environment_xml.findtext('{*}MapfileLocation')
        if not mapfile_location:
            mssg = 'mapfile creation chosen but no <MapfileLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_location_basename = environment_xml.find(
            '{*}MapfileConfigLocation').get('basename')
        if not mapfile_location_basename:
            mssg = 'mapfile creation chosen but no "basename" attribute found for <MapfileLocation>'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_staging_location = environment_xml.findtext(
            '{*}MapfileStagingLocation')
        if not mapfile_staging_location:
            mssg = 'mapfile creation chosen but no <MapfileStagingLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_config_location = environment_xml.findtext(
            '{*}MapfileConfigLocation')
        if not mapfile_config_location:
            mssg = 'mapfile creation chosen but no <MapfileConfigLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_config_basename = environment_xml.find(
            '{*}MapfileConfigLocation').get('basename')
        if not mapfile_config_basename:
            mssg = 'mapfile creation chosen but no "basename" attribute found for <MapfileConfigLocation>'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

    # Get all the TMSs for this projection
    available_tilematrixsets = []
    for tms_list in [elem.findall('{*}TileMatrixSet') for elem in tilematrixset_defs_xml.findall('{*}Projection') if elem.get('id') == 'EPSG:3857']:
        for tms in tms_list:
            available_tilematrixsets.append(tms)

    # Download and parse GC file from endpoint
    try:
        r = requests.get(gc_uri)
        if r.status_code != 200:
            log_sig_exit(
                'ERROR', 'Can\'t download GetCapabilities from URL: ' + gc_uri, sigevent_url)
    except:
        log_sig_exit(
            'ERROR', 'Can\'t download GetCapabilities from URL: ' + gc_uri, sigevent_url)

    # Get the layers and source TMSs from the source GC file
    try:
        gc_xml = etree.fromstring(r.content)
    except etree.XMLSyntaxError:
        log_sig_exit(
            'ERROR', "Can't parse GetCapabilities file (invalid syntax): " + gc_uri, sigevent_url)
    gc_layers = gc_xml.find('{*}Contents').findall('{*}Layer')
    tilematrixsets = gc_xml.find('{*}Contents').findall('{*}TileMatrixSet')
    ows = '{' + gc_xml.nsmap['ows'] + '}'
    xlink = '{http://www.w3.org/1999/xlink}'
    apache_staging_conf_path = ""

    for layer in gc_layers:
        src_layer = copy.copy(layer)
        identifier = layer.findtext(ows + 'Identifier')
        if debug:
            print 'Configuring layer: ' + identifier
        if (identifier in layer_exclude_list) or (layer_include_list and identifier not in layer_include_list):
            if debug:
                print 'Skipping layer: ' + identifier
            continue
        layer_tms_apache_configs = []
        bands = 3

        # Get TMSs for this layer and build a config for each
        tms_list = [elem for elem in tilematrixsets if elem.findtext(
            ows + 'Identifier') == layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')]
        layer_tilematrixsets = sorted(tms_list, key=get_max_scale_dem)

        #HACK
        if len(layer_tilematrixsets) == 0:
           print("No layer_tilematrixsets. Skipping layer: " + identifier)
           continue

        out_tilematrixsets = []
        for tilematrixset in layer_tilematrixsets:
            # Start by getting the source info we need to configure this layer
            # -- right now we are assuming geographic source projection
            src_tilematrixset_name = tilematrixset.findtext(ows + 'Identifier')
            matrices = sort_tilematrixset(tilematrixset)
            src_scale_denominator = float(
                matrices[0].findtext('{*}ScaleDenominator'))
            src_width = int(round(2 * math.pi * EARTH_RADIUS /
                                  (src_scale_denominator * 0.28E-3)))
            src_height = src_width / 2
            src_levels = len(matrices)
            src_pagesize_width = matrices[0].findtext('{*}TileWidth')
            src_pagesize_height = matrices[0].findtext('{*}TileHeight')
            src_bbox_elem = layer.find(ows + 'WGS84BoundingBox')
            src_bbox = ','.join(src_bbox_elem.findtext(ows + 'LowerCorner').split(
                ' ')) + ',' + ','.join(src_bbox_elem.findtext(ows + 'UpperCorner').split(' '))
            src_format = layer.findtext('{*}Format')
            src_title = layer.findtext(ows + 'Title')

            # If it's a PNG, we need to grab a tile and check if it's paletted
            if 'image/png' in src_format:
                sample_tile_url = layer.find('{*}ResourceURL').get('template').replace('{Time}', 'default')\
                    .replace('{TileMatrixSet}', src_tilematrixset_name).replace('{TileMatrix}', '0').replace('{TileRow}', '0').replace('{TileCol}', '0')
                print 'Checking for palette for PNG layer: ' + identifier
                r = requests.get(sample_tile_url)
                if r.status_code != 200:
                    if "Invalid time format" in r.text:  # Try taking out TIME if server doesn't like the request
                        sample_tile_url = sample_tile_url.replace(
                            'default/default', 'default')
                        r = requests.get(sample_tile_url)
                        if r.status_code != 200:
                            mssg = 'Can\'t get sample PNG tile from URL: ' + sample_tile_url
                            errors.append(asctime() + " " + mssg)
                            log_sig_err(mssg, sigevent_url)
                            continue
                    else:
                        mssg = 'Can\'t get sample PNG tile from URL: ' + sample_tile_url
                        errors.append(asctime() + " " + mssg)
                        log_sig_err(mssg, sigevent_url)
                        continue
                sample_png = png.Reader(BytesIO(r.content))
                sample_png.read()
                try:
                    if sample_png.palette():
                        bands = 1
                        print identifier + ' contains palette'
                except png.FormatError:
                    # No palette, check for greyscale
                    if sample_png.asDirect()[3]['greyscale'] is True:
                        if sample_png.asDirect()[3]['alpha'] is True:
                            bands = 2
                            print identifier + ' is greyscale + alpha'
                        else:
                            bands = 1
                            print identifier + ' is greyscale'
                    else:  # Check for alpha
                        if sample_png.asDirect()[3]['alpha'] is True:
                            bands = 4
                            print identifier + ' is RGBA'
                        else:
                            bands = 3
                            print identifier + ' is RGB'

            # Now figure out the configuration for the destination layer.
            # Start by getting the output TileMatrixSet that most closely
            # matches the scale denominator of the source.
            dest_tilematrixset = reduce(functools.partial(
                scale_denominator_reduce, src_scale_denominator=src_scale_denominator), available_tilematrixsets, None)
            out_tilematrixsets.append(dest_tilematrixset)
            dest_tilematrixset_name = dest_tilematrixset.findtext(
                ows + 'Identifier')
            dest_scale_denominator = float(sort_tilematrixset(dest_tilematrixset)[
                0].findtext('{*}ScaleDenominator'))
            dest_width = dest_height = int(
                round(2 * math.pi * EARTH_RADIUS / (dest_scale_denominator * 0.28E-3)))
            dest_levels = len(dest_tilematrixset.findall('{*}TileMatrix'))
            dest_pagesize_width = sort_tilematrixset(dest_tilematrixset)[
                0].findtext('{*}TileWidth')
            dest_pagesize_height = sort_tilematrixset(dest_tilematrixset)[
                0].findtext('{*}TileHeight')
            dest_top_left_corner = [Decimal(value) for value in sort_tilematrixset(
                dest_tilematrixset)[0].findtext('{*}TopLeftCorner').split(' ')]
            dest_bbox = '{0},{1},{2},{3}'.format(dest_top_left_corner[0], dest_top_left_corner[
                0], -dest_top_left_corner[0], -dest_top_left_corner[0])
            dest_resource_url_elem = layer.find('{*}ResourceURL')
            dest_url = dest_resource_url_elem.get('template')
            for location in src_locations:
                dest_url = dest_url.replace(location.get(
                    'external'), location.get('internal')).replace('//', '/')
                if not dest_url.startswith('/'):
                    dest_url = '/' + dest_url
            dest_url = re.match('(.*default)', dest_url).group()
            dest_dim_elem = layer.find('{*}Dimension')
            if dest_dim_elem is not None and dest_dim_elem.findtext(ows + 'Identifier') == 'Time':
                static = False
                dest_url = '{0}/{1}/{2}'.format(dest_url,
                                                '${date}', src_tilematrixset_name)
            else:
                static = True
                dest_url = '{0}/{1}'.format(dest_url, src_tilematrixset_name)
            dest_file_type = dest_resource_url_elem.get('format')
            dest_file_ext = get_ext_for_file_type(dest_file_type)
            if dest_file_ext is None:
                mssg = identifier + " file type is not supported for OnEarth: " + dest_file_type
                warnings.append(asctime() + " " + mssg)
                log_sig_warn(mssg, sigevent_url)
                break
            if dest_file_ext in ['.tif', '.lerc', '.mvt']:
                mssg = identifier + " file type is not supported for reproject: " + dest_file_type
                print mssg
                break

            if wmts:
                layer_endpoint = os.path.join(wmts_base_endpoint, identifier)
                layer_style_endpoint = os.path.join(layer_endpoint, 'default')

                # Write the source and reproject (output) configuration files
                wmts_staging_layer_path = os.path.join(
                    wmts_staging_location, identifier)
                wmts_staging_style_path = os.path.join(
                    wmts_staging_layer_path, "default")
                wmts_staging_path = os.path.join(
                    wmts_staging_style_path, dest_tilematrixset_name)

                try:
                    os.makedirs(wmts_staging_path)
                except OSError:
                    if not os.path.exists(wmts_staging_path):
                        log_sig_exit('ERROR', 'WMTS staging location: ' +
                                     wmts_staging_path + ' cannot be created.', sigevent_url)
                    pass

                src_cfg_filename = identifier + '_source.config'
                hasher = hashlib.md5()
                with open(os.path.join(wmts_staging_path, src_cfg_filename), 'w+') as src_cfg:
                    if 'image/png' in src_format:
                        src_cfg.write('Size {0} {1} 1 {2}\n'.format(
                            src_width, src_height, bands))
                    else:
                        src_cfg.write('Size {0} {1}\n'.format(
                            src_width, src_height))
                    src_cfg.write('PageSize {0} {1}\n'.format(
                        src_pagesize_width, src_pagesize_height))
                    src_cfg.write('Projection {0}\n'.format('EPSG:4326'))
                    src_cfg.write('SkippedLevels 1\n')
                    src_cfg.write('BoundingBox {0}\n'.format(src_bbox))
                    src_cfg.seek(0)
                    hasher.update(src_cfg.read())

                dest_cfg_filename = identifier + '_reproject.config'
                with open(os.path.join(wmts_staging_path, dest_cfg_filename), 'w+') as dest_cfg:
                    if 'image/png' in src_format:
                        dest_cfg.write('Size {0} {1} 1 {2}\n'.format(
                            dest_width, dest_height, bands))
                        dest_cfg.write('Nearest On\n')
                    else:
                        dest_cfg.write('Size {0} {1}\n'.format(
                            dest_width, dest_height))
                    dest_cfg.write('PageSize {0} {1}\n'.format(
                        dest_pagesize_width, dest_pagesize_height))
                    dest_cfg.write('Projection {0}\n'.format('EPSG:3857'))
                    dest_cfg.write('BoundingBox {0}\n'.format(dest_bbox))
                    dest_cfg.write('SourcePath {0}\n'.format(dest_url))
                    dest_cfg.write('SourcePostfix {0}\n'.format(dest_file_ext))
                    dest_cfg.write('MimeType {0}\n'.format(src_format))
                    dest_cfg.write('Oversample On\n')
                    dest_cfg.write('ExtraLevels 3\n')
                    dest_cfg.seek(0)
                    hasher.update(dest_cfg.read())
                    dest_cfg.write('ETagSeed {0}\n'.format(hasher.hexdigest()))
                    # dest_cfg.write('SkippedLevels 1\n')

                # Build Apache config snippet for TMS
                tms_path = os.path.join(
                    layer_style_endpoint, dest_tilematrixset_name)
                tms_apache_config = '<Directory {0}>\n'.format(tms_path)
                tms_apache_config += '\tWMTSWrapperRole tilematrixset\n'
                tms_apache_config += '\tWMTSWrapperMimeType {0}\n'.format(
                    src_format)
                regexp_file_ext = dest_file_ext if dest_file_type != 'image/jpeg' else '.(jpg|jpeg)'
                regexp_str = dest_tilematrixset_name + \
                    '/\d{1,2}/\d{1,5}/\d{1,5}' + regexp_file_ext + '$'
                tms_apache_config += '\tReproject_RegExp {0}\n'.format(
                    regexp_str)
                tms_apache_config += '\tReproject_ConfigurationFiles {0} {1}\n'.format(
                    os.path.join(tms_path, src_cfg_filename), os.path.join(tms_path, dest_cfg_filename))
                tms_apache_config += '</Directory>\n'
                layer_tms_apache_configs.append(tms_apache_config)

            # Build a TWMS configuration for the highest available TMS for this
            # layer
            if twms and tilematrixset == layer_tilematrixsets[0]:
                reproj_twms_config_filename = 'twms.config'
                twms_staging_path = os.path.join(
                    twms_staging_location, identifier)

                try:
                    os.makedirs(twms_staging_path)
                except OSError:
                    if not os.path.exists(twms_staging_path):
                        log_sig_exit('ERROR', 'TWMS staging location: ' +
                                     twms_staging_path + ' cannot be created.', sigevent_url)
                    pass

                with open(os.path.join(twms_staging_path, reproj_twms_config_filename), 'w+') as twms_cfg:
                    twms_cfg.write('Size {0} {1} {2}\n'.format(
                        dest_width, dest_height, dest_levels))
                    twms_cfg.write('PageSize {0} {1}\n'.format(
                        dest_pagesize_width, dest_pagesize_height))
                    twms_cfg.write('BoundingBox {0}\n'.format(dest_bbox))

                    # Build endpoint path for WMTS source
                    twms_src_layer_path = os.path.join(
                        wmts_reproject_endpoint, identifier)
                    twms_src_style_path = os.path.join(
                        twms_src_layer_path, 'default')
                    if static:
                        twms_src_path = os.path.join(
                            twms_src_style_path, dest_tilematrixset_name)
                    else:
                        twms_src_time_path = os.path.join(
                            twms_src_style_path, '${date}')
                        twms_src_path = os.path.join(
                            twms_src_time_path, dest_tilematrixset_name)
                    twms_cfg.write('SourcePath {0}\n'.format(twms_src_path))
                    twms_cfg.write('SourcePostfix {0}'.format(dest_file_ext))

        if dest_file_ext is None:  # Skip layer if unsupported file type
            continue
        if dest_file_ext in ['.tif', '.lerc', '.mvt']:
            continue

        if wmts:
            # Finish building the layer Apache config
            if wmts_reproject_endpoint is not None:
                layer_apache_config = 'Alias {0}{1} {2}\n'.format(
                    add_trailing_slash(wmts_reproject_endpoint), identifier, layer_endpoint)
            else:
                layer_apache_config = ''
            layer_apache_config += '<Directory {0}>\n'.format(layer_endpoint)
            layer_apache_config += '\tWMTSWrapperRole layer\n'
            layer_apache_config += '\tWMTSWrapperEnableTime on\n'
            layer_apache_config += '</Directory>\n'
            layer_apache_config += '<Directory {0}>\n'.format(
                layer_style_endpoint)
            layer_apache_config += '\tWMTSWrapperRole style\n'
            layer_apache_config += '</Directory>\n'
            for layer_config in layer_tms_apache_configs:
                layer_apache_config += layer_config

            layer_apache_config_filename = identifier + '_reproject.conf'
            layer_apache_config_path = os.path.join(
                wmts_staging_location, layer_apache_config_filename)
            try:
                with open(layer_apache_config_path, 'w+') as f:
                    f.write(layer_apache_config)
            except IOError:
                log_sig_exit('ERROR', 'Cannot write layer config file: ' +
                             layer_apache_config_path, sigevent_url)

            # Create final Apache configs (WMTS)
            if wmts_reproject_endpoint is not None:
                endpoint_apache_config = 'Alias {0}wmts.cgi {1}wmts.cgi\n'.format(
                    add_trailing_slash(wmts_reproject_endpoint), add_trailing_slash(wmts_base_endpoint))
            else:
                endpoint_apache_config = ''
            endpoint_apache_config += '<Directory {0}>\n'.format(
                wmts_base_endpoint)
            endpoint_apache_config += '\tWMTSWrapperRole root\n'
            endpoint_apache_config += '</Directory>\n'
            apache_staging_conf_path = os.path.join(
                wmts_staging_location, wmts_apache_config_basename + '.conf')
            try:
                with open(apache_staging_conf_path, 'w+') as wmts_apache_config_file:

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
                log_sig_exit('ERROR', "Can't write WMTS staging apache config: " +
                             apache_staging_conf_path, sigevent_url)

            # Modify layer GC xml for webmercator projection
            # Insert additional bounding box for WebMercator
            layer.find(ows + 'WGS84BoundingBox').find(ows +
                                                      'LowerCorner').text = '-180 -85.051129'
            layer.find(ows + 'WGS84BoundingBox').find(ows +
                                                      'UpperCorner').text = '180 85.051129'
            bb_elem_idx = layer.index(layer.find(ows + 'WGS84BoundingBox')) + 1
            bbox_elem = etree.Element(
                ows + 'BoundingBox', crs='urn:ogc:def:crs:EPSG::3857')
            bbox_upper_corner_elem = etree.Element(ows + 'UpperCorner')
            bbox_upper_corner_elem.text = '{0} {1}'.format(
                -dest_top_left_corner[0], -dest_top_left_corner[0])
            bbox_lower_corner_elem = etree.Element(ows + 'LowerCorner')
            bbox_lower_corner_elem.text = '{0} {1}'.format(
                dest_top_left_corner[0], dest_top_left_corner[0])
            bbox_elem.append(bbox_lower_corner_elem)
            bbox_elem.append(bbox_upper_corner_elem)
            layer.insert(bb_elem_idx, bbox_elem)

            # Add the TMSs we are using (clearing the ones from the source GC)
            tms_link_elem = layer.find('{*}TileMatrixSetLink')
            tms_link_elem.clear()
            for tms in out_tilematrixsets:
                tms_elem = etree.Element('TileMatrixSet')
                tms_elem.text = tms.findtext('{*}Identifier')
                tms_link_elem.append(tms_elem)

            # Modify the ResourceURL template
            base_url = wmts_service_url + identifier
            if static:
                wmts_service_template = base_url + \
                    '/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}' + \
                    dest_file_ext
            else:
                wmts_service_template = base_url + \
                    '/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}' + dest_file_ext
            dest_resource_url_elem.set('template', wmts_service_template)

            wmts_gc_snippet_filename = '{0}_reproject.xml'.format(identifier)
            try:
                with open(os.path.join(wmts_staging_location, wmts_gc_snippet_filename), 'w+') as wmts_gc_snippet:
                    wmts_gc_snippet.write(
                        etree.tostring(layer, pretty_print=True))
            except IOError:
                log_sig_exit(
                    'ERROR', 'Could not create staging XML snippet', sigevent_url)

        if twms:
            try:
                twms_gc_staging_snippet = os.path.join(
                    twms_staging_location, identifier + '_gc.xml')
                # Open layer XML file
                twms_gc_xml = open(twms_gc_staging_snippet, 'w+')
            except IOError:
                mssg = str().join(['Cannot read layer XML file:  ',
                                   twms_gc_staging_snippet])
                log_sig_exit('ERROR', mssg, sigevent_url)

            twms_gc_layer_template = """<Layer queryable=\"0\">
            <Name>$Identifier</Name>
            <Title xml:lang=\"en\">$Title</Title>
            <Abstract xml:lang=\"en\">$Abstract</Abstract>
            <LatLonBoundingBox minx=\"$minx\" miny=\"$miny\" maxx=\"$maxx\" maxy=\"$maxy\"/>
            <Style>
                <Name>default</Name> <Title xml:lang=\"en\">(default) Default style</Title>
            </Style>
            <ScaleHint min=\"10\" max=\"100\"/> <MinScaleDenominator>100</MinScaleDenominator>
            </Layer>"""

            layer_output = ""
            lines = twms_gc_layer_template.splitlines(True)
            for line in lines:
                # replace lines in template
                if '</Layer>' in line:
                    line = ' ' + line + '\n'
                if '$Identifier' in line:
                    line = line.replace("$Identifier", identifier)
                if '$Title' in line:
                    line = line.replace("$Title", cgi.escape(src_title))
                if '$Abstract' in line:
                    abstract = identifier + ' abstract'
                    line = line.replace("$Abstract", abstract)
                if '$minx' in line:
                    line = line.replace("$minx", str(-dest_top_left_corner[0]))
                if '$miny' in line:
                    line = line.replace("$miny", str(-dest_top_left_corner[0]))
                if '$maxx' in line:
                    line = line.replace("$maxx", str(dest_top_left_corner[0]))
                if '$maxy' in line:
                    line = line.replace("$maxy", str(dest_top_left_corner[0]))
                layer_output = layer_output + line
            twms_gc_xml.writelines(layer_output)
            twms_gc_xml.close()

            twms_gts_layer_template = """<TiledGroup>
            <Name>$TiledGroupName</Name>
            <Title xml:lang=\"en\">$Title</Title>
            <Abstract xml:lang=\"en\">$Abstract</Abstract>
            <Projection>$Projection</Projection>
            <Pad>0</Pad>
            <Bands>$Bands</Bands>
            <LatLonBoundingBox minx=\"$minx\" miny=\"$miny\" maxx=\"$maxx\" maxy=\"$maxy\" />
            <Key>${time}</Key>
            $Patterns</TiledGroup>"""

            try:
                twms_gts_staging_snippet = os.path.join(
                    twms_staging_location, identifier + '_gts.xml')
                # Open layer XML file
                twms_gts_xml = open(twms_gts_staging_snippet, 'w+')
            except IOError:
                mssg = str().join(['Cannot read layer XML file:  ',
                                   twms_gts_staging_snippet])
                log_sig_exit('ERROR', mssg, sigevent_url)

            proj = osr.SpatialReference()
            proj.ImportFromEPSG(3857)

            layer_output = ""
            lines = twms_gts_layer_template.splitlines(True)
            for line in lines:
                # replace lines in template
                if '</TiledGroup>' in line:
                    line = ' ' + line + '\n'
                if '$TiledGroupName' in line:
                    formatted_identifier = identifier.replace('_', ' ')
                    line = line.replace('$TiledGroupName',
                                        formatted_identifier + ' tileset')
                if '$Title' in line:
                    line = line.replace("$Title", cgi.escape(src_title))
                if '$Abstract' in line:
                    abstract = identifier + ' abstract'
                    line = line.replace("$Abstract", abstract)
                    line = line.replace("$Abstract", '')
                if '$Projection' in line:
                    line = line.replace("$Projection", proj.ExportToWkt())
                if '$Bands' in line:
                    if src_format == 'image/png':
                        # GDAL wants 4 for PNGs
                        line = line.replace("$Bands", "4")
                    else:
                        line = line.replace("$Bands", "3")
                if '$minx' in line:
                    line = line.replace("$minx", str(dest_top_left_corner[0]))
                if '$miny' in line:
                    line = line.replace("$miny", str(dest_top_left_corner[0]))
                if '$maxx' in line:
                    line = line.replace("$maxx", str(-dest_top_left_corner[0]))
                if '$maxy' in line:
                    line = line.replace("$maxy", str(-dest_top_left_corner[0]))
                if '$Patterns' in line and len(out_tilematrixsets) > 0:
                    patterns = ''
                    for tilematrix in sorted(out_tilematrixsets[0].findall('{*}TileMatrix'), key=lambda matrix: float(matrix.findtext('{*}ScaleDenominator'))):
                        resx = (dest_top_left_corner[
                            1] - dest_top_left_corner[0]) / Decimal(tilematrix.findtext('MatrixWidth'))
                        resy = (dest_top_left_corner[
                            1] - dest_top_left_corner[0]) / Decimal(tilematrix.findtext('MatrixHeight'))
                        local_xmax = dest_top_left_corner[0] + resx
                        local_xmax_str = str(local_xmax) if local_xmax else '0'
                        local_ymax = dest_top_left_corner[1] - resy
                        local_ymax_str = str(local_ymax) if local_ymax else '0'
                        prefix = '<TilePattern><![CDATA['
                        postfix = ']]></TilePattern>\n'
                        time_str = 'request=GetMap&layers={0}&srs=EPSG:3857&format={1}&styles=&time={2}&width=256&height=256&bbox={3},{4},{5},{6}\n'.format(
                            identifier, dest_file_type, "${time}", dest_top_left_corner[0], local_ymax_str, local_xmax_str, dest_top_left_corner[1])
                        no_time_str = 'request=GetMap&layers={0}&srs=EPSG:3857&format={1}&styles=&width=256&height=256&bbox={2},{3},{4},{5}\n'.format(
                            identifier, dest_file_type, dest_top_left_corner[0], local_ymax_str, local_xmax_str, dest_top_left_corner[1])
                        if static:
                            patterns += prefix + no_time_str + postfix
                        else:
                            patterns += prefix + time_str + no_time_str + postfix
                    line = line.replace("$Patterns", patterns)
                layer_output = layer_output + line
            twms_gts_xml.writelines(layer_output)
            twms_gts_xml.close()

        if create_mapfile:
            # Use the template to create the new Mapfile snippet
            wms_layer_group_info = ''
            dimension_info = ''
            validation_info = ''
            style_info = ''
            if not static:
                default_datetime = dest_dim_elem.findtext('{*}Default')
                period_str = ','.join(
                    elem.text for elem in dest_dim_elem.findall("{*}Value"))
                dimension_info = bulk_replace(DIMENSION_TEMPLATE, [('{periods}', period_str),
                                                                   ('{default}', default_datetime)])
                validation_info = VALIDATION_TEMPLATE.replace(
                    '{default}', default_datetime)

            # If the source EPSG:4326 layer has a legend, then add that to the EPSG:3857 layer also
            legendUrlElems = []

            for styleElem in layer.findall('{*}Style'):
                legendUrlElems.extend(styleElem.findall('{*}LegendURL'))

            for legendUrlElem in legendUrlElems:
                attributes = legendUrlElem.attrib
                if attributes[xlink + 'role'].endswith("horizontal"):
                    style_info = bulk_replace(STYLE_TEMPLATE, [('{width}', attributes["width"]),
                                                               ('{height}', attributes["height"]),
                                                               ('{href}', attributes[xlink + 'href'].replace(".svg",".png"))])

            # Mapserver automatically converts to RGBA and works better if we
            # specify that for png layers
            mapserver_bands = 4 if 'image/png' in src_format else 3

            src_crs = layer_tilematrixsets[0].findtext('{*}SupportedCRS')
            src_epsg = get_epsg_code_for_proj_string(src_crs)

            if not target_epsg:
                target_epsg = src_epsg
            target_bbox = map(
                str, get_bbox_for_proj_string('EPSG:' + target_epsg, get_in_map_units=(src_epsg not in ['4326','3413','3031'])))

            mapfile_snippet = bulk_replace(
                MAPFILE_TEMPLATE, [('{layer_name}', identifier), ('{data_xml}', make_gdal_tms_xml(src_layer, mapserver_bands, src_epsg)), ('{layer_title}', cgi.escape(src_title)),
                                   ('{wms_layer_group_info}', wms_layer_group_info), ('{dimension_info}', dimension_info), ('{style_info}', style_info), ('{validation_info}', validation_info),
                                   ('{src_epsg}', src_epsg), ('{target_epsg}', target_epsg), ('{target_bbox}', ', '.join(target_bbox))])

            mapfile_name = os.path.join(
                mapfile_staging_location, identifier + '.map')
            with open(mapfile_name, 'w+') as f:
                f.write(mapfile_snippet)

    # Final routines (after all layers have been processed)
    if wmts:
        if not stage_only:
            # Copy all the WMTS config files to the endpoint
            layer_dirs = [subdir for subdir in os.listdir(wmts_staging_location) if os.path.isdir(
                os.path.join(wmts_staging_location, subdir))]
            for layer_dir in layer_dirs:
                layer_endpoint = os.path.join(wmts_base_endpoint, layer_dir)
                if os.path.exists(layer_endpoint):
                    shutil.rmtree(layer_endpoint)
                layer_staging_path = os.path.join(
                    wmts_staging_location, layer_dir)
                print '\nCopying reprojected WMTS layer directories: {0} -> {1} '.format(layer_staging_path, layer_endpoint)
                shutil.copytree(layer_staging_path, layer_endpoint)

            # Copy the WMTS Apache config to the specified directory (like
            # conf.d)
            apache_conf_path = os.path.join(
                wmts_apache_config_location, wmts_apache_config_basename + '.conf')
            print '\nCopying reprojected WMTS layer Apache config {0} -> {1}'.format(apache_staging_conf_path, apache_conf_path)
            try:
                shutil.copyfile(apache_staging_conf_path, apache_conf_path)
            except IOError, e:  # Try with sudo if permission denied
                if 'Permission denied' in str(e):
                    cmd = ['sudo', 'cp', apache_staging_conf_path,
                           apache_conf_path]
                    try:
                        run_command(cmd, sigevent_url)
                    except Exception, e:
                        log_sig_exit('ERROR', str(e), sigevent_url)

        if create_gc:
            # Configure GetCapabilties (routine copied from oe_configure_layer)
            try:
                # Copy and open base GetCapabilities.
                getCapabilities_file = os.path.join(
                    wmts_staging_location, 'getCapabilities.xml')
                if not base_wmts_gc:
                    log_sig_exit(
                        'ERROR', 'WMTS GetCapabilities creation selected but no base GC file specified.', sigevent_url)
                shutil.copyfile(base_wmts_gc, getCapabilities_file)
                getCapabilities_base = open(getCapabilities_file, 'r+')
            except IOError:
                log_sig_exit(
                    'ERROR', 'Cannot read getcapabilities_base_wmts.xml file: ' + base_wmts_gc, sigevent_url)
            else:
                lines = getCapabilities_base.readlines()
                for idx in range(0, len(lines)):
                    if '<ows:Get' in lines[idx]:
                        spaces = lines[idx].index('<')
                        getUrlLine = lines[idx].replace(
                            'ows:Get', 'Get xmlns:xlink="http://www.w3.org/1999/xlink"').replace('>', '/>')
                        getUrl = etree.fromstring(getUrlLine)
                        if '1.0.0/WMTSCapabilities.xml' in lines[idx]:
                            getUrl.attrib[
                                xlink + 'href'] = wmts_service_url + '1.0.0/WMTSCapabilities.xml'
                        elif 'wmts.cgi?' in lines[idx]:
                            getUrl.attrib[
                                xlink + 'href'] = wmts_service_url + 'wmts.cgi?'
                        else:
                            getUrl.attrib[xlink + 'href'] = wmts_service_url
                        lines[idx] = (' ' * spaces) + etree.tostring(getUrl, pretty_print=True).replace(
                            'Get', 'ows:Get').replace(' xmlns:xlink="http://www.w3.org/1999/xlink"', '').replace('/>', '>')
                    if 'ServiceMetadataURL' in lines[idx]:
                        spaces = lines[idx].index('<')
                        serviceMetadataUrlLine = lines[idx].replace(
                            'ServiceMetadataURL', 'ServiceMetadataURL xmlns:xlink="http://www.w3.org/1999/xlink"')
                        serviceMetadataUrl = etree.fromstring(
                            serviceMetadataUrlLine)
                        serviceMetadataUrl.attrib[
                            xlink + 'href'] = wmts_service_url + '1.0.0/WMTSCapabilities.xml'
                        lines[idx] = (' ' * spaces) + etree.tostring(serviceMetadataUrl, pretty_print=True).replace(
                            ' xmlns:xlink="http://www.w3.org/1999/xlink"', '')
                getCapabilities_base.seek(0)
                getCapabilities_base.truncate()
                getCapabilities_base.writelines(lines)
                getCapabilities_base.close()

    if twms:
        # Create final Apache configs (TWMS)
        twms_apache_conf_path_template = os.path.join(
            twms_base_endpoint, '${layer}/twms.config')
        if twms_reproject_endpoint is not None:
            twms_endpoint_apache_config = 'Alias {0} {1}\n'.format(
                twms_reproject_endpoint, twms_base_endpoint)
        else:
            twms_endpoint_apache_config = ''
        twms_endpoint_apache_config += '<Directory {0}>\n'.format(
            twms_base_endpoint)
        twms_endpoint_apache_config += '\ttWMS_RegExp twms.cgi\n'
        twms_endpoint_apache_config += '\ttWMS_ConfigurationFile {0}\n'.format(
            twms_apache_conf_path_template)
        twms_endpoint_apache_config += '</Directory>\n'
        twms_apache_staging_conf_path = os.path.join(
            twms_staging_location, twms_apache_config_basename + '.conf')
        try:
            with open(twms_apache_staging_conf_path, 'w+') as twms_apache_config_file:

                # Write endpoint Apache stuff
                twms_apache_config_file.write(twms_endpoint_apache_config)

        except IOError:
            log_sig_exit('ERROR', "Can't write TWMS staging apache conf: " +
                         twms_apache_staging_conf_path, sigevent_url)

        if not stage_only:
            # Copy all the TWMS config files to the endpoint
            layer_dirs = [subdir for subdir in os.listdir(twms_staging_location) if os.path.isdir(
                os.path.join(twms_staging_location, subdir))]
            for layer_dir in layer_dirs:
                layer_endpoint = os.path.join(twms_base_endpoint, layer_dir)
                if os.path.exists(layer_endpoint):
                    shutil.rmtree(layer_endpoint)
                layer_staging_path = os.path.join(
                    twms_staging_location, layer_dir)
                print '\nCopying reprojected TWMS layer directories: {0} -> {1} '.format(layer_staging_path, layer_endpoint)
                shutil.copytree(layer_staging_path, layer_endpoint)

            # Copy the TWMS Apache config to the specified directory (like
            # conf.d)
            twms_apache_conf_path = os.path.join(
                twms_apache_config_location, twms_apache_config_basename + '.conf')
            print '\nCopying reprojected TWMS layer Apache config {0} -> {1}'.format(twms_apache_staging_conf_path, twms_apache_conf_path)
            try:
                shutil.copyfile(twms_apache_staging_conf_path,
                                twms_apache_conf_path)
            except IOError, e:  # Try with sudo if permission denied
                if 'Permission denied' in str(e):
                    cmd = ['sudo', 'cp', twms_apache_staging_conf_path,
                           twms_apache_conf_path]
                    try:
                        run_command(cmd, sigevent_url)
                    except Exception, e:
                        log_sig_exit('ERROR', str(e), sigevent_url)

        # Configure base GC file for TWMS
        if create_gc:
            try:
                # Copy and open base GetCapabilities.
                getCapabilities_file = os.path.join(
                    twms_staging_location, 'getCapabilities.xml')
                if not base_twms_gc:
                    log_sig_exit(
                        'ERROR', 'TWMS GetCapabilities creation selected but no base GC file specified.', sigevent_url)
                shutil.copyfile(base_twms_gc, getCapabilities_file)
                getCapabilities_base = open(getCapabilities_file, 'r+')
            except IOError:
                log_sig_exit(
                    'ERROR', 'Cannot read getcapabilities_base_twms.xml file: ' + base_twms_gc, sigevent_url)
            else:
                lines = getCapabilities_base.readlines()
                for idx in range(0, len(lines)):
                    if '<SRS></SRS>' in lines[idx]:
                        lines[idx] = lines[idx].replace(
                            '<SRS></SRS>', '<SRS>EPSG:3857</SRS>')
                    if '<CRS></CRS>' in lines[idx]:
                        lines[idx] = lines[idx].replace(
                            '<CRS></CRS>', '<CRS>EPSG:3857</CRS>')
                    if 'OnlineResource' in lines[idx]:
                        spaces = lines[idx].index('<')
                        onlineResource = etree.fromstring(lines[idx])
                        if 'KeywordList' in lines[idx - 1]:
                            # don't include the cgi portion
                            onlineResource.attrib[
                                xlink + 'href'] = twms_service_url
                        else:
                            onlineResource.attrib[
                                xlink + 'href'] = twms_service_url + "twms.cgi?"
                        lines[idx] = (
                            ' ' * spaces) + etree.tostring(onlineResource, pretty_print=True)
                getCapabilities_base.seek(0)
                getCapabilities_base.truncate()
                getCapabilities_base.writelines(lines)
                getCapabilities_base.close()

            try:
                # Copy and open base GetTileService.
                getTileService_file = os.path.join(
                    twms_staging_location, 'getTileService.xml')
                if not base_twms_get_tile_service:
                    log_sig_exit(
                        'ERROR', 'TWMS GetTileService creation selected but no base GetTileService file specified.', sigevent_url)
                shutil.copyfile(base_twms_get_tile_service,
                                getTileService_file)
                getTileService_base = open(getTileService_file, 'r+')
            except IOError:
                log_sig_exit('ERROR', 'Cannot read gettileservice_base.xml file: ' +
                             getTileService_file, sigevent_url)
            else:
                lines = getTileService_base.readlines()
                for idx in range(0, len(lines)):
                    if 'BoundingBox' in lines[idx]:
                        lines[idx] = lines[idx].replace("BoundingBox", "LatLonBoundingBox").replace("{minx}", '-20037508.34278925').replace(
                            "{miny}", '-20037508.34278925').replace("{maxx}", '20037508.34278925').replace("{maxy}", '20037508.34278925')
                    if 'OnlineResource' in lines[idx]:
                        spaces = lines[idx].index('<')
                        onlineResource = etree.fromstring(lines[idx])
                        if 'KeywordList' in lines[idx - 1]:
                            # don't include the cgi portion
                            onlineResource.attrib[
                                xlink + 'href'] = twms_service_url
                        else:
                            onlineResource.attrib[
                                xlink + 'href'] = twms_service_url + "twms.cgi?"
                        lines[idx] = (
                            ' ' * spaces) + etree.tostring(onlineResource, pretty_print=True)
                getTileService_base.seek(0)
                getTileService_base.truncate()
                getTileService_base.writelines(lines)
                getTileService_base.close()

    return (warnings, errors)

# Main routine to be run in CLI mode
if __name__ == '__main__':
    print 'OnEarth Reproject layer config tool (for use with mod_reproject)'

    if 'LCDIR' not in os.environ:
        print 'LCDIR environment variable not set.\nLCDIR should point to your OnEarth layer_config directory.\n'
        lcdir = os.path.abspath(os.path.dirname(__file__) + '/..')
    else:
        lcdir = os.environ['LCDIR']

    usageText = 'oe_configure_reproject_layer.py --conf_file [layer_configuration_file.xml] --lcdir [$LCDIR] --no_xml --no_twms --no_wmts'

    # Define command line options and args.
    parser = OptionParser(usage=usageText, version=versionNumber)
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
    parser.add_option("-s", "--send_email", action="store_true", dest="send_email",
                      default=False, help="Send email notification for errors and warnings.")
    parser.add_option('--email_server', action='store', type='string', dest='email_server',
                      default='', help='The server where email is sent from (overrides configuration file value')
    parser.add_option('--email_recipient', action='store', type='string', dest='email_recipient',
                      default='', help='The recipient address for email notifications (overrides configuration file value')
    parser.add_option('--email_sender', action='store', type='string', dest='email_sender',
                      default='', help='The sender for email notifications (overrides configuration file value')
    parser.add_option("-w", "--no_wmts",
                      action="store_true", dest="no_wmts",
                      default=False, help="Do not use configurations for WMTS.")
    parser.add_option("-x", "--no_xml",
                      action="store_true", dest="no_xml",
                      default=False, help="Do not generate getCapabilities and getTileService XML.")
    parser.add_option("-z", "--stage_only",
                      action="store_true", dest="stage_only",
                      default=False, help="Do not move configurations to final location; keep configurations in staging location only.")
    parser.add_option("--debug",
                      action="store_true", dest="debug",
                      default=False, help="Produce verbose debug messages")

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

    layer_config_path = options.layer_config_path
    if not layer_config_path:
        print 'No layer config XML specified'
        sys.exit()

    # Send email.
    send_email = options.send_email
    # Email server.
    email_server = options.email_server
    # Email recipient
    email_recipient = options.email_recipient
    # Email sender
    email_sender = options.email_sender
    # Email metadata replaces sigevent_url
    if send_email:
        sigevent_url = (email_server, email_recipient, email_sender)
    else:
        sigevent_url = ''

    base_twms_gc = os.path.join(lcdir, '/conf/getcapabilities_base_twms.xml')
    base_twms_get_tile_service = os.path.join(
        lcdir, '/conf/gettileservice_base.xml')
    base_wmts_gc = os.path.join(lcdir, '/conf/getcapabilities_base_wmts.xml')

    print 'Using ' + lcdir + ' as $LCDIR.'

    if not xml:
        log_info_mssg(
            "no_xml specified, getCapabilities and getTileService files will be staged only")

    build_reproject_configs(layer_config_path, tilematrixsets_config_path, base_wmts_gc=base_wmts_gc, base_twms_gc=base_twms_gc,
                            base_twms_get_tile_service=base_twms_get_tile_service, wmts=wmts, twms=twms, xml=xml, sigevent_url=sigevent_url, stage_only=options.stage_only, debug=options.debug)
