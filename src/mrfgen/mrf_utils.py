#-------------------------------------------------------------------------------
# Name:        mrf_utils (modified from mrf_clean)
# Purpose:
# Copy the tile data and index files of an MRF, ignoring the unused parts
#
# Author:      lucian
# Author:      jacob (modified July 2019)
#
# Created:     05/10/2016
# Updated:     07/07/2017 Creates index files with holes if possible
# Updated:     11/09/2018 Use typed arrays instead of struct
#                         Process index file block at a time
# Updated      07/15/2019 Added support for Python 2.7
#
# Copyright:   (c) lucian 2016 - 2018
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
#-------------------------------------------------------------------------------

import os
import os.path
import sys
import array
import pdb
import struct

class IdxArray:
    def __init__(self, itemsize):
        self.itemsize = itemsize
        self.bytesize = self.itemsize * 8

        self.data = bytearray()

    def fromfile(self, file, size):
        for _ in range(size):
            self.data += file.read(self.itemsize)

    def tofile(self, file):
        for i in range(len(self.data)):
            file.write(self.data[i * self.itemsize : self.itemsize * (i + 1)])

    def __len__(self):
        return len(self.data) // self.itemsize

    def __repr__(self):
        return "IdxArray({})".format(self.data)

    def byteswap(self):
        for i in range(len(self.data) // self.itemsize):
            self.data[self.itemsize * i : self.itemsize * (i + 1)] = self.data[self.itemsize * i : self.itemsize * (i + 1)][::-1]

    def count(self, value):
        return self.data.count(str(value))

    def __getitem__(self, idx):
        if idx >= len(self.data) // self.itemsize:
            raise IndexError("byte index out of range")

        return struct.unpack("Q", self.data[idx * self.itemsize: (idx + 1) * self.itemsize])[0]

    def __setitem__(self, idx, value):
        if idx >= len(self.data) // self.itemsize:
            raise IndexError("byte assignment index out of range")        

        self.data[idx * self.itemsize : (idx + 1) * self.itemsize] = struct.pack("Q", value)

# empty_file content is used to initialize the data file
def mrf_clean(source, destination, empty_file = None):
    '''Copies the active tile from a source to a destination MRF'''

    def index_name(mrf_name):
        bname, ext = os.path.splitext(mrf_name)
        return bname + os.extsep + "idx"

    with open(index_name(source), "rb") as sidx:
        with open(source, "rb") as sfile:
            with open(index_name(destination),"wb") as didx:
                with open(destination, "wb") as dfile:
                    if empty_file:
                        dfile.write(open(empty_file,"rb").read())
                    doffset = dfile.tell()

                    # pdb.set_trace()

                    while True:
                        idx = IdxArray(8)
                        idx.fromfile(sidx, 512 // idx.itemsize)
                        
                        if len(idx) == 0:
                            break # Normal exit

                        # Don't write empty blocks
                        if idx.count(0) == len(idx):
                            didx.seek(len(idx) * idx.itemsize, os.SEEK_CUR)
                            continue

                        if sys.byteorder != 'big':
                            idx.byteswap() # To native
                        
                        # copy tiles in this block, adjust the offsets
                        for i in range(0, len(idx), 2):
                            if idx[i + 1] != 0: # size of tile
                                # pdb.set_trace()
                                sfile.seek(idx[i], os.SEEK_SET)
                                idx[i] = doffset
                                doffset += idx[i + 1]
                                dfile.write(sfile.read(idx[i+1]))

                        if sys.byteorder != 'big':
                            idx.byteswap() # Back to big before writing

                        idx.tofile(didx)

                    didx.truncate() # In case last block is empty


if __name__ == '__main__':
    mrf_clean(*sys.argv[1:])
