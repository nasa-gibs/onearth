#! /bin/python
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

# oe_create_mvt_mrt -- A utility to create MRFs that contain MVT tiles.

import sys
import os
import subprocess
from optparse import OptionParser
import sqlite3
import struct
import math
import xml.dom.minidom
import tempfile


def shapefile_to_mrf(shapefile_path, output_file_prefix, dest_path, proj_string, debug=False, max_zoom=3):
    """Takes an input shapefile and outputs an MVT MRF in the given location.

    Args:
        shapefile (str): A path to the .shp file that will be processed.
        mrf_file_prefix (str): The string that will be used as the prefix for MRF files that will be created, i.e. mrf_file_prefix_.idx
        dest_path (str): A path to the location where the output MRF files will be stored.
        proj_string (str): The EPSG projection being used by the dataset.
        (optional) debug (bool): Toggles verbose output and will leave behind artifact files.
        (optional) max_zoom (int): Number of zoom levels that will be added to the MRF. Defaults to 3.
    """
    if proj_string not in ('EPSG:4326', 'EPSG:3857'):
        raise ValueError('Projection not supported. Only EPSG:4326 and EPSG:3857 are currently supported.')

    if debug:
        temp_dir = './'
    else:
        temp_dir = tempfile.mkdtemp()

    # Generate GeoJSON from source shapefile
    if debug:
        print 'Converting shapefile to GeoJSON for MBTiles conversion...'
    
    output_geojson_path = os.path.join(temp_dir, output_file_prefix + '.geojson')
    subprocess.call(('ogr2ogr', '-f', 'GeoJSON', output_geojson_path, shapefile_path))

    geojson_to_mrf(output_geojson_path, output_file_prefix, dest_path, proj_string, debug=debug, max_zoom=max_zoom, del_src=True)

    return


def geojson_to_mrf(geojson_path, output_file_prefix, dest_path, proj_string, debug=False, max_zoom=3, del_src=False):
    """Takes an input geojson and outputs an MVT MRF in the given location.

    Args:
        geojson_path (str): A path to the .geojson file that will be processed.
        mrf_file_prefix (str): The string that will be used as the prefix for MRF files that will be created, i.e. mrf_file_prefix_.idx
        dest_path (str): A path to the location where the output MRF files will be stored.
        proj_string (str): The EPSG projection being used by the dataset.
        (optional) debug (bool): Toggles verbose output and will leave behind artifact files.
        (optional) max_zoom (int): Number of zoom levels that will be added to the MRF. Defaults to 3.

    """

    if debug:
        temp_dir = './'
    else:
        temp_dir = tempfile.mkdtemp()

    # Use tippecanoe to generate MBTiles stack
    if debug:
        print 'Converting GeoJSON to vector tiles...'
    output_mbtiles_path = os.path.join(temp_dir, output_file_prefix + '.mbtiles')
    subprocess.call(('tippecanoe', '-o', output_mbtiles_path, '-s', proj_string, '-z', str(max_zoom), '-pk', geojson_path))

    # Store MBTile stack contents into MRF
    if debug:
        print 'Storing vector tiles as MRF...'
    conn = sqlite3.connect(output_mbtiles_path)
    cur = conn.cursor()

    notile = struct.pack('!QQ', 0, 0)
    offset = 0

    try:
        fidx = open(os.path.join(dest_path, output_file_prefix + '_.idx'), 'w')
        fout = open(os.path.join(dest_path, output_file_prefix + '_.pvt'), 'w')
        fmrf = open(os.path.join(dest_path, output_file_prefix + '_.mrf'), 'w')
    except OSError as e:
        raise e

    cur.execute('SELECT zoom_level, tile_row, tile_column FROM tiles')
    tile_list = cur.fetchall()

    for z in xrange(max_zoom, -1, -1):
        max_tiles = int(math.pow(2, z))
        for y in xrange(max_tiles):
            for x in xrange(max_tiles):
                if debug:
                    print 'Writing tile {0}/{1}/{2}'.format(z, y, x)
                # MBTiles use Tile Map Service Specification for indicies -- have to flip y-index
                # http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
                flipped_y = max_tiles - 1 - y
                if (z, flipped_y, x) in tile_list:
                    cur.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_row=? AND tile_column=?', (z, flipped_y, x))
                    tile_row = cur.fetchone()
                    tile_data = tile_row[0]
                    # Write tile data bytes to pvt
                    fout.write(tile_data)
                    tile_index = struct.pack('!QQ', offset, len(tile_data))
                    offset += len(tile_data)
                else:
                    tile_index = notile
                fidx.write(tile_index)
    fidx.close()
    fout.close()
    if del_src:
        os.remove(geojson_path)
    if not debug:
        os.remove(output_mbtiles_path)

    # Now build the MRF XML
    mrf_impl = xml.dom.minidom.getDOMImplementation()
    mrf_dom = mrf_impl.createDocument(None, 'MRF_META', None)
    mrf_meta = mrf_dom.documentElement
    raster_node = mrf_dom.createElement('Raster')
    
    # Create <Size> element
    size_node = mrf_dom.createElement('Size')
    size_node.setAttribute('x', str(int(math.pow(2, max_zoom) * 256)))
    size_node.setAttribute('y', str(int(math.pow(2, max_zoom) * 256)))
    size_node.setAttribute('c', str(1))
    raster_node.appendChild(size_node)

    # Create <PageSize> element
    page_size_node = mrf_dom.createElement('PageSize')
    page_size_node.setAttribute('x', str(256))
    page_size_node.setAttribute('y', str(256))
    page_size_node.setAttribute('c', str(1))
    raster_node.appendChild(page_size_node)

    # Create <Compression> element
    compression_node = mrf_dom.createElement('Compression')
    compression_value = mrf_dom.createTextNode('PBF')
    compression_node.appendChild(compression_value)
    raster_node.appendChild(compression_node)

    # Add <DataValues> element
    data_values_node = mrf_dom.createElement('DataValues')
    data_values_node.setAttribute('NoData', '0')
    raster_node.appendChild(data_values_node)

    # Add <Quality> element
    # quality_node = mrf_dom.createElement('Quality')
    # quality_value = mrf_dom.createTextNode('80')
    # quality_node.appendChild(quality_value)
    # raster_node.appendChild(quality_node)

    mrf_meta.appendChild(raster_node)

    # Create <Rsets> element
    rsets_node = mrf_dom.createElement('Rsets')
    rsets_node.setAttribute('model', 'uniform')
    mrf_meta.appendChild(rsets_node)

    # Create <GeoTags> element
    geotags_node = mrf_dom.createElement('GeoTags')
    bbox_node = mrf_dom.createElement('BoundingBox')
    bbox_node.setAttribute('minx', '-20037508.34000000')
    bbox_node.setAttribute('miny', '-20037508.34000000')
    bbox_node.setAttribute('maxx', '20037508.34000000')
    bbox_node.setAttribute('maxy', '20037508.34000000')
    geotags_node.appendChild(bbox_node)

    projection_node = mrf_dom.createElement('Projection')
    projection_text = mrf_dom.createTextNode('PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"],AUTHORITY["EPSG","3857"]]')
    projection_node.appendChild(projection_text)
    geotags_node.appendChild(projection_node)

    mrf_meta.appendChild(geotags_node)
    
    fmrf.write(mrf_meta.toprettyxml())
    fmrf.close()
    return


if __name__ == "__main__":
    usage = 'vector_to_mrf.py [options] INPUT_SHAPEFILE'
    parser = OptionParser(usage=usage)
    parser.add_option('-z', '--zoom_levels', action='store', type='int', dest='zoom', default='3',
                      help='Number of zoom levels (including single-tile overview). Defaults to 3 (GoogleMapsCompatible_Level3)')
    parser.add_option('-s', '--source_projection', action='store', type='string', dest='source_projection',
                      help='Define the source projection of the shapefile or GeoJSON you\'re using. Default is EPSG:4326', default='EPSG:4326')
    parser.add_option('-p', '--prefix', action='store', dest='prefix', help='Set the prefix for the MRF files to be created.')
    parser.add_option('-o', '--output', action='store', dest='output', help='Set the output path for the created MRF files.')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Provide verbose output and leave behind file artifacts')

    (options, args) = parser.parse_args()

    if len(args) < 1:
        print 'Not enough arguments. Use the "-h" option for information on usage.'
        sys.exit()

    prefix = options.prefix if options.prefix else os.path.splitext(args[0])[0]
    dest_path = options.output if options.output else './'

    if os.path.splitext(args[0])[1] == '.geojson':
        geojson_to_mrf(args[0], prefix, dest_path, options.source_projection, debug=options.debug, max_zoom=options.zoom)
    else:
        shapefile_to_mrf(args[0], prefix, dest_path, options.source_projection, debug=options.debug, max_zoom=options.zoom)
