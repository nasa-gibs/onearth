#!/usr/bin/env python3

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

import argparse
from osgeo import gdal, gdalconst
from osgeo.gdalconst import *
import numpy as np
import numpy.ma as ma
import math


def pack(infile, outfile, calcscaleoffset=False, forgibs=False, minmax=None, rawnodata = None, scaleoffset=None, noverifydata=False):
    # Get metadata information
    tiffds = gdal.Open(infile, GA_ReadOnly)
    projection = tiffds.GetProjection()
    geotransform = tiffds.GetGeoTransform()
    metadata = tiffds.GetMetadata()

    nodata = []
    if tiffds.GetRasterBand(1).GetNoDataValue() is not None:
        nodata.append(tiffds.GetRasterBand(1).GetNoDataValue())
    if rawnodata is not None:
        del nodata[:]
        for k in range(len(rawnodata)):
            nodata.append(float(rawnodata[k]))
    scale = tiffds.GetRasterBand(1).GetScale()
    offset = tiffds.GetRasterBand(1).GetOffset()
    numbands = 3
    if len(nodata) != 0:
        numbands = 4

    # Create new raster
    ptiffraster = gdal.GetDriverByName("GTiff").Create(outfile, tiffds.RasterXSize, tiffds.RasterYSize, numbands,
                                                       GDT_Byte, ['COMPRESS=LZW', 'BIGTIFF=YES'])
    ptiffraster.SetProjection(projection)
    ptiffraster.SetGeoTransform(geotransform)
    ptiffraster.SetMetadata(metadata)

    overviewlist = []
    for i in range(tiffds.GetRasterBand(1).GetOverviewCount()):
        overviewlist.append(tiffds.GetRasterBand(1).XSize / tiffds.GetRasterBand(1).GetOverview(i).XSize + 1)

    ptiffraster.BuildOverviews(overviewlist=overviewlist)

    print("Getting statistics in source data...")
    if minmax is None:
        if rawnodata is not None:
            minmax = [float("inf"), float("-inf")]
            stride = 5

            for j in range(0, tiffds.GetRasterBand(1).YSize, stride):
                if (tiffds.GetRasterBand(1).YSize - j) < stride:
                    stride = tiffds.GetRasterBand(1).YSize % stride
                mask = np.zeros((stride, tiffds.GetRasterBand(1).XSize))
                tiffdsa = tiffds.GetRasterBand(1).ReadAsArray(xoff=0, yoff=j, win_xsize=tiffds.GetRasterBand(1).XSize,
                                                              win_ysize=stride).astype(np.float32)
                for k in range(len(rawnodata)):
                    mask[tiffdsa == nodata[k]] = 1
                masktiffdsa = ma.MaskedArray(tiffdsa, mask)
                thismin = np.amin(masktiffdsa)
                thismax = np.amax(masktiffdsa)
                if thismin < minmax[0]:
                    minmax[0] = thismin
                if thismax > minmax[1]:
                    minmax[1] = thismax
        else:
            tiffstats = tiffds.GetRasterBand(1).GetStatistics(0, 1)
            minmax = (tiffstats[0], tiffstats[1])

    poffset = math.floor(minmax[0])
    pscale = math.floor((2 ** 24 - 1) / (minmax[1] - poffset))
    if scaleoffset is not None:
        pscale = scaleoffset[0]
        poffset = scaleoffset[1]
    print("New scale is %.9f" % pscale)
    print("New offset is %f" % poffset)

    if calcscaleoffset:
        return

    print("Reading in source data...")

    for i in range(1, numbands + 1):
        print("Writing band %d data..." % i)
        stride = 5
        for j in range(0, tiffds.GetRasterBand(1).YSize, stride):
            if (tiffds.GetRasterBand(1).YSize - j) < stride:
                stride = tiffds.GetRasterBand(1).YSize % stride
            tiffdsa = tiffds.GetRasterBand(1).ReadAsArray(xoff=0, yoff=j, win_xsize=tiffds.GetRasterBand(1).XSize,
                                                          win_ysize=stride).astype(np.float32)

            if scale is not None:
                np.multiply(tiffdsa, scale, tiffdsa)
            if offset is not None:
                np.add(tiffdsa, offset, tiffdsa)

            if i <= 3:
                for k in range(len(nodata)):
                    tiffdsa[tiffdsa == nodata[k]] = poffset
                np.subtract(tiffdsa, poffset, tiffdsa)
                if not noverifydata:
                    assert (tiffdsa < 0).sum() == 0, "The offset must be less than the minimum value in the data."
                np.multiply(tiffdsa, pscale, tiffdsa)
                if not noverifydata:
                    assert (tiffdsa >= 2 ** 24).sum() == 0, "The scale must make the values fall between 0 and 2^24"
                tiffdsa = tiffdsa.astype(np.int32)
                np.right_shift(tiffdsa, (i - 1) * 8, tiffdsa)
                np.bitwise_and(tiffdsa, 0x000000ff, tiffdsa)
            if i == 4:
                nodatadsa = np.empty(tiffdsa.shape)
                np.ndarray.fill(nodatadsa, 0x000000ff)
                for k in range(len(nodata)):
                    nodatadsa[tiffdsa == nodata[k]] = 0
                tiffdsa = nodatadsa
            ptiffraster.GetRasterBand(i).WriteArray(tiffdsa, xoff=0, yoff=j)
        ptiffraster.GetRasterBand(i).SetScale(pscale)
        ptiffraster.GetRasterBand(i).SetOffset(poffset)
        if len(nodata) != 0:  # Write nodata for every band if there is nodata information
            ptiffraster.GetRasterBand(i).SetNoDataValue(nodata[0])
            if forgibs:
                ptiffraster.GetRasterBand(i).SetNoDataValue(0)
        ptiffraster.FlushCache()

    for j in range(len(overviewlist)):
        tiffdsa = tiffds.GetRasterBand(1).GetOverview(j).ReadAsArray().astype(np.float32)

        if scale is not None:
            np.multiply(tiffdsa, scale, tiffdsa)
        if offset is not None:
            np.add(tiffdsa, offset, tiffdsa)

        for i in range(1, numbands + 1):
            if i <= 3:
                np.subtract(tiffdsa, poffset, tiffdsa)
                np.multiply(tiffdsa, pscale, tiffdsa)
                tiffdsa = tiffdsa.astype(np.int32)
                np.right_shift(tiffdsa, (i - 1) * 8, tiffdsa)
                np.bitwise_and(tiffdsa, 0x000000ff, tiffdsa)
            if i == 4:
                nodatadsa = np.empty(tiffdsa.shape)
                np.ndarray.fill(nodatadsa, 0x000000ff)
                for k in range(len(nodata)):
                    nodatadsa[tiffdsa == nodata[k]] = 0
                tiffdsa = nodatadsa
            print("Writing band %d, overview %d data..." % (i, j))
            ptiffraster.GetRasterBand(i).GetOverview(j).WriteArray(tiffdsa)
            ptiffraster.GetRasterBand(i).GetOverview(j).SetScale(pscale)
            ptiffraster.GetRasterBand(i).GetOverview(j).SetOffset(poffset)
            if len(nodata) != 0:
                ptiffraster.GetRasterBand(i).GetOverview(j).SetNoDataValue(nodata[0])
                if forgibs:
                    ptiffraster.GetRasterBand(i).SetNoDataValue(0)
            ptiffraster.FlushCache()


def main():
    parser = argparse.ArgumentParser(
        description='This utility packs a GeoTIFF with up to a Float32 data type into a 3 channel GeoTIFF suitable for converting into a PNG for use in browsers.')
    parser.add_argument('tiff', help='The source GeoTIFF')
    parser.add_argument('ptiff', help='The output packed GeoTIFF')
    parser.add_argument('-c', '--calculate-scale-offset', dest='calcscaleoffset', action='store_true',
                        help='Calculates optimal scale and offset only, does not process data')
    parser.add_argument('-g', '--for-gibs-mrfgen', dest='forgibs', action='store_true', help='Set the nodata value to 0 for GIBS mrfgen.')
    parser.add_argument('-d', '--no-data', dest='nodata', nargs='?', action='append',
                        help='Only use specified nodata values and not the source nodata values. Only for use with poorly generated GeoTIFFs, will slow processing.')
    parser.add_argument('-n', '--no-verify-data', dest='noverifydata', action='store_true',
                        help='Does not verify data (that offset >= min data value and scaled values < 2^24)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--minmax', dest='minmax', type=float, nargs=2,
                       help='The minimum and maximum values for scale and offset)')
    group.add_argument('-s', '--scaleoffset', dest='scaleoffset', type=float, nargs=2,
                       help='The scale and offset values, computed automatically if not specified. Note: offset is also scaled.')
    args = parser.parse_args()

    pack(args.tiff, args.ptiff, args.calcscaleoffset, args.forgibs, args.minmax, args.nodata, args.scaleoffset, args.noverifydata)


if __name__ == "__main__":
    main()
