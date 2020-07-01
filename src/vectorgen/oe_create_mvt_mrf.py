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
"""
oe_create_mvt_mrt -- A utility to create MRFs that contain MVT tiles. This can be run either from the command line,
or by using the create_vector_mrf() function in another script.
"""

import os
import sys
import struct
import StringIO
import gzip
import xml.dom.minidom
import math
import random
import fiona
import shapely.geometry
import rtree
import mapbox_vector_tile
from osgeo import osr
import decimal
import re
from oe_utils import *


# Main tile-creation function.
def create_vector_mrf(input_file_path,
                      output_path,
                      mrf_prefix,
                      layer_name,
                      target_x,
                      target_y,
                      target_extents,
                      tile_size,
                      overview_levels,
                      projection_str,
                      filter_list,
                      feature_reduce_rate=2.5,
                      cluster_reduce_rate=2,
                      buffer_size=5,
                      buffer_edges=False,
                      debug=False):
    """
    Creates a MVT MRF stack using the specified TileMatrixSet.

    NOTE: Vectors don't have a concept of pixels. We're only using pixel dimensions as a way of expressing the proportional size of the tiles and to match them up with
    raster tilesets.

    Args:
        input_file_path (str) -- Path to the vector datafile to be used. Accepts GeoJSON and Shapefiles
        output_path (str) -- Path to where the output MRF files should be stored.
        mrf_prefix (str) -- Prefix for the MRF filenames that will be generated.
        layer_name (str) -- Name for the layer to be packed into the tile. Only single layers currently supported.
        target_x (int) -- Pixel width of the highest zoom level.
        target_y (int) -- Pixel height of the highest zoom level.
        target_extents (list float) -- The bounding box for the chosen projection in map units.
        tile_size (int) -- Pixel size of the tiles to be generated.
        overview_levels (list int) -- A list of the overview levels to be used (i.e., a level of 2 will render a level that's 1/2 the width and height of the base level)
        projection_str (str) -- EPSG code for the projection to be used.
        filter_list (list object) -- List of options for filtering features
        feature_reduce_rate (float) -- (currently only for Point data) Rate at which to reduce features for each successive zoom level.
            Defaults to 2.5 (1 feature retained for every 2.5 in the previous zoom level)
        cluster_reduce_rate (float) -- (currently only for Point data) Rate at which to reduce points in clusters of 1px or less.
            Default is 2 (retain the square root of the total points in the cluster).
        buffer_size (float) -- The buffer size around each tile to avoid cutting off features and styling elements such as labels.
            Default is 5 (pixel size in map units at each zoom level) which allows enough room for most styling.
        buffer_edges (boolean) -- Flag indicating whether buffering should be performed on the edges of the tile matrix.
            Default is False
        debug (bool) -- Toggle verbose output messages and MVT file artifacts (MVT tile files will be created in addition to MRF)
    """
    # Get projection and calculate overview levels if necessary
    proj = osr.SpatialReference()
    proj.ImportFromEPSG(int(projection_str.split(':')[1]))
    if not target_y:
        target_y = (target_x / 2) if proj.IsGeographic() else target_x
    if not overview_levels:
        overview_levels = [2]
        exp = 2
        while (overview_levels[-1] * tile_size) < target_x:
            overview_levels.append(2**exp)
            exp += 1

    tile_matrices = get_tms(target_x, target_y, target_extents, tile_size,
                            overview_levels, proj)

    # Open MRF data and index files and generate the MRF XML
    fidx = open(os.path.join(output_path, mrf_prefix + '.idx'), 'w+')
    fout = open(os.path.join(output_path, mrf_prefix + '.pvt'), 'w+')
    notile = struct.pack('!QQ', 0, 0)
    pvt_offset = 0

    mrf_dom = build_mrf_dom(tile_matrices, target_extents, tile_size, proj)
    with open(os.path.join(output_path, mrf_prefix) + '.mrf', 'w+') as f:
        f.write(mrf_dom.toprettyxml())

    spatial_dbs = []
    source_schemas = []
    # Dump contents of shapefile into a mutable rtree spatial database for faster searching.
    for input_file in input_file_path:
        log_info_mssg('Processing ' + input_file)
        with fiona.open(input_file) as shapefile:
            try:
                spatial_db = rtree.index.Index(
                    rtree_index_generator(list(shapefile), filter_list))
            except rtree.core.RTreeError as e:
                log_info_mssg('ERROR -- problem importing feature data. If you have filters configured, ' \
                              'the source dataset may have no features that pass. Err: {0}'.format(e))
                return False
            spatial_dbs.append(spatial_db)
            source_schema = shapefile.schema['geometry']
            source_schemas.append(source_schema)
            if debug:
                log_info_mssg('Points to process: ' + str(spatial_db.count(spatial_db.bounds)))

    # Build tilematrix pyramid from the bottom (highest zoom) up. We generate tiles left-right, top-bottom and write them
    # successively to the MRF.
    for i, tile_matrix in enumerate(reversed(tile_matrices)):
        z = len(tile_matrices) - i - 1

        for idx, spatial_db in enumerate(spatial_dbs):
            # We do general point rate reduction randomly, deleting those items from the
            # spatial index. The highest zoom level is never reduced.
            if source_schemas[
                    idx] == 'Point' and feature_reduce_rate and z != len(
                        tile_matrices) - 1:
                feature_count = spatial_dbs[idx].count(spatial_dbs[idx].bounds)
                num_points_to_delete = int(feature_count - math.floor(
                    feature_count / feature_reduce_rate))
                if debug:
                    print 'Deleting ' + str(
                        num_points_to_delete) + ' points from dataset'
                for feature in random.sample([
                        feature for feature in spatial_dbs[idx].intersection(
                            spatial_dbs[idx].bounds, objects=True)
                ], num_points_to_delete):
                    spatial_dbs[idx].delete(feature.id, feature.bbox)

            # Here we're culling points that are less than a pixel away from each other. We use a queue to keep track of them and avoid looking at points twice.
            if source_schemas[
                    idx] == 'Point' and cluster_reduce_rate and z != len(
                        tile_matrices) - 1:
                feature_queue = [
                    item for item in spatial_dbs[idx].intersection(
                        spatial_dbs[idx].bounds, objects=True)
                ]
                while feature_queue:
                    feature = feature_queue.pop()
                    sub_pixel_bbox = (
                        feature.bbox[0] - tile_matrix['resolution'],
                        feature.bbox[1] - tile_matrix['resolution'],
                        feature.bbox[2] + tile_matrix['resolution'],
                        feature.bbox[3] + tile_matrix['resolution'])
                    nearby_points = [
                        item for item in spatial_dbs[idx].intersection(
                            sub_pixel_bbox, objects=True)
                        if item.id != feature.id
                    ]
                    if nearby_points:
                        # We reduce the number of clustered points to 1/nth of their previous number. (user-selectable)
                        # All the nearby points are then dropped from the queue.
                        for point in random.sample(
                                nearby_points,
                                len(nearby_points) - int(
                                    math.floor(
                                        len(nearby_points)**
                                        (1 / float(cluster_reduce_rate))))):
                            spatial_dbs[idx].delete(point.id, point.bbox)
                        for point in nearby_points:
                            [
                                feature_queue.remove(item)
                                for item in feature_queue
                                if item.id == point.id
                            ]

        # Start making tiles. We figure out the tile's bbox, then search for all the features that intersect with that bbox,
        # then turn the resulting list into an MVT tile and write the tile.
        for y in xrange(tile_matrix['matrix_height']):
            for x in xrange(tile_matrix['matrix_width']):
                # Get tile bounds
                tile_size = tile_matrix['tile_size_in_map_units']

                min_x = tile_matrix['matrix_extents'][0] + (x * tile_size)
                max_y = tile_matrix['matrix_extents'][3] - (y * tile_size)
                max_x = min_x + tile_size
                min_y = max_y - tile_size
                tile_bbox = shapely.geometry.box(min_x, min_y, max_x, max_y)

                # If we're buffering around the edges, then use the same min/max buffer for all dimensions and tiles
                if buffer_edges:
                    tile_min_x_buffer = tile_max_x_buffer = tile_min_y_buffer = tile_max_y_buffer = (buffer_size * (tile_size / 256))

                # Else, set the min/max buffer to 0 if we're on an edge
                else:
                    tile_min_x_buffer = buffer_size * (tile_size / 256) if x != 0 else 0
                    tile_max_x_buffer = buffer_size * (tile_size / 256) if x != (tile_matrix['matrix_width'] - 1) else 0
                    tile_min_y_buffer = buffer_size * (tile_size / 256) if y != 0 else 0
                    tile_max_y_buffer = buffer_size * (tile_size / 256) if y != (tile_matrix['matrix_height'] - 1) else 0

                tile_buffer_bbox = shapely.geometry.box(
                    min_x - tile_min_x_buffer, min_y - tile_min_y_buffer,
                    max_x + tile_max_x_buffer, max_y + tile_max_y_buffer)

                if debug:
                    print "Processing tile: {0}/{1}/{2}\r".format(z, x, y)
                    print 'Tile Bounds: ' + str(tile_bbox.bounds)

                # Iterate through the shapefile geometry and grab anything in this tile's bounds
                tile_features = []
                for spatial_db in spatial_dbs:
                    for feature in [
                            item.object for item in spatial_db.intersection(
                                tile_buffer_bbox.bounds, objects=True)
                    ]:
                        geometry = shapely.geometry.shape(feature['geometry'])
                        # If the feature isn't fully contained in the tile bounds, we need to clip it.
                        if not shapely.geometry.shape(feature['geometry']).within(tile_buffer_bbox):
                            geometry = tile_buffer_bbox.intersection(geometry)
                        new_feature = {
                            'geometry': geometry,
                            'properties': feature['properties']
                        }
                        tile_features.append(new_feature)

                # Create MVT tile from the features in this tile (Only doing single layers for now)
                new_layer = {'name': layer_name, 'features': tile_features}
                # Have to change the default rounding if in Python 2.6 due to Decimal rounding issues.
                if sys.version_info < (2, 7):
                    round_fn = py_26_round_fn
                else:
                    round_fn = None
                mvt_tile = mapbox_vector_tile.encode(
                    [new_layer],
                    quantize_bounds=tile_bbox.bounds,
                    y_coord_down=False,
                    round_fn=round_fn)

                # Write out artifact mvt files for debug mode.
                if debug and mvt_tile:
                    mvt_filename = os.path.join(
                        os.getcwd(), 'tiles/test_{0}_{1}_{2}.mvt'.format(
                            z, x, y))
                    with open(mvt_filename, 'w+') as f:
                        f.write(mvt_tile)

                # Write out MVT tile data to MRF. Note that we have to gzip the tile first.
                if mvt_tile:
                    out = StringIO.StringIO()
                    gzip_obj = gzip.GzipFile(fileobj=out, mode='w')
                    gzip_obj.write(mvt_tile)
                    gzip_obj.close()
                    zipped_tile_data = out.getvalue()
                    tile_index = struct.pack('!QQ', pvt_offset,
                                             len(zipped_tile_data))
                    pvt_offset += len(zipped_tile_data)
                    fout.write(zipped_tile_data)

                else:
                    tile_index = notile
                fidx.write(tile_index)

    fidx.close()
    fout.close()

    return True


# UTILITY FUNCTIONS
"""
mapbox_vector_tile module is not compatible with Python 2.6's decimal handling, so we
use a modified rounding function if necessary.
ref: http://stackoverflow.com/questions/8000318/conversion-from-float-to-decimal-in-python-2-6-how-to-do-it-and-why-they-didnt
"""


def py_26_float_to_decimal(f):  # mapbox_vector_tile monkeypatch for python 2.6
    "Convert a floating point number to a Decimal with no loss of information"
    n, d = f.as_integer_ratio()
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result


def py_26_round_fn(val):  # mapbox_vector_tile monkeypatch for python 2.6
    d = py_26_float_to_decimal(val)
    rounded = d.quantize(1, rounding=decimal.ROUND_HALF_EVEN)
    return float(rounded)


def get_tms(target_x, target_y, extents, tile_size, o_levels, proj):
    tile_matrices = []
    if proj.IsGeographic():
        map_meters_per_unit = 2 * math.pi * 6370997 / 360
    else:
        map_meters_per_unit = 1

    width_in_meters = map_meters_per_unit * (extents[2] - extents[0])

    o_levels.insert(0, 1)
    for level in sorted(o_levels, reverse=True):
        tms = {}
        x_dim = target_x / level
        y_dim = target_y / level

        tms['matrix_width'] = int(math.ceil(float(x_dim) / float(tile_size)))
        tms['matrix_height'] = int(math.ceil(float(y_dim) / float(tile_size)))

        if proj.IsGeographic():
            # We don't support 0-level tiles in geographic
            if x_dim <= tile_size:
                continue
            # Current solution for dealing with the weird GIBS geographic TMSs
            if tms['matrix_width'] == 5:
                tms['resolution'] = 0.14078259895979
            elif tms['matrix_width'] == 3:
                tms['resolution'] = 0.28156519791957
            elif tms['matrix_width'] == 2:
                tms['resolution'] = 0.56313039583914
            else:
                tms['resolution'] = 360 / float(x_dim)
            max_x = tms['resolution'] * tile_size * tms['matrix_width']
            min_y = -(tms['resolution'] * tile_size * tms['matrix_height'])
            tms['matrix_extents'] = (-180, min_y, max_x, 90)
            tms['tile_size_in_map_units'] = max_x / tms['matrix_width']
        else:
            tms['matrix_extents'] = extents
            tms['tile_size_in_map_units'] = (
                extents[2] - extents[0]) / tms['matrix_width']
            tms['resolution'] = width_in_meters / x_dim

        tile_matrices.append(tms)

    return tile_matrices


def build_mrf_dom(tile_matrices, extents, tile_size, proj):
    """
    Function that builds and returns an MRF XML DOM.

    Args:
        tile_matrices (list obj) -- List of tilematrices as produced by get_tilematrixset()
    Returns:
        xml.dom object.
    """

    mrf_impl = xml.dom.minidom.getDOMImplementation()
    mrf_dom = mrf_impl.createDocument(None, 'MRF_META', None)
    mrf_meta = mrf_dom.documentElement
    raster_node = mrf_dom.createElement('Raster')

    # Create <Size> element
    size_node = mrf_dom.createElement('Size')
    size_node.setAttribute('x',
                           str(tile_matrices[-1]['matrix_width'] * tile_size))
    size_node.setAttribute('y',
                           str(tile_matrices[-1]['matrix_height'] * tile_size))
    raster_node.appendChild(size_node)

    # Create <PageSize> element
    page_size_node = mrf_dom.createElement('PageSize')
    page_size_node.setAttribute('x', str(tile_size))
    page_size_node.setAttribute('y', str(tile_size))
    raster_node.appendChild(page_size_node)

    # Create <Compression> element
    compression_node = mrf_dom.createElement('Compression')
    compression_value = mrf_dom.createTextNode('MVT')
    compression_node.appendChild(compression_value)
    raster_node.appendChild(compression_node)

    # Add <DataValues> element
    data_values_node = mrf_dom.createElement('DataValues')
    data_values_node.setAttribute('NoData', '0')
    raster_node.appendChild(data_values_node)

    mrf_meta.appendChild(raster_node)

    # Create <Rsets> element
    rsets_node = mrf_dom.createElement('Rsets')
    rsets_node.setAttribute('model', 'uniform')
    rsets_node.setAttribute('scale', '2')
    mrf_meta.appendChild(rsets_node)

    # Create <GeoTags> element
    geotags_node = mrf_dom.createElement('GeoTags')
    bbox_node = mrf_dom.createElement('BoundingBox')
    bbox_node.setAttribute('minx', str(extents[0]))
    bbox_node.setAttribute('miny', str(extents[1]))
    bbox_node.setAttribute('maxx', str(extents[2]))
    bbox_node.setAttribute('maxy', str(extents[3]))
    geotags_node.appendChild(bbox_node)

    projection_node = mrf_dom.createElement('Projection')
    projection_text = mrf_dom.createTextNode(proj.ExportToWkt())
    projection_node.appendChild(projection_text)
    geotags_node.appendChild(projection_node)

    mrf_meta.appendChild(geotags_node)
    return mrf_meta


# UTILITY STUFF


# This is the recommended way of building an rtree index.
def rtree_index_generator(features, filter_list):
    for idx, feature in enumerate(features):
        try:
            if len(filter_list) == 0 or passes_filters(feature, filter_list):
                yield (idx, shapely.geometry.shape(feature['geometry']).bounds,
                       feature)
        except ValueError as e:
            print "WARN - " + str(e)


def passes_filters(feature, filter_list):
    return any(
        map(lambda filter_block: filter_block_func(feature, filter_block),
            filter_list))


def filter_block_func(feature, filter_block):
    if filter_block['logic'].lower() == "and":
        return all(
            map(lambda comp: filter_func(feature, comp),
                filter_block['filters']))
    else:
        return any(
            map(lambda comp: filter_func(feature, comp),
                filter_block['filters']))


def filter_func(feature, comparison):
    property_value = str(feature['properties'].get(comparison['name']))
    equality = comparison['comparison'] == 'equals'
    regexp = comparison['regexp']
    if regexp:
        result = regexp.search(property_value)
    else:
        result = feature['properties'].get(
            comparison['name']) == comparison['value']
    return result if equality else not result
