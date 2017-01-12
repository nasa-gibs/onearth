/*
* Copyright (c) 2002-2016, California Institute of Technology.
* All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
*
* Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
*   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
*   2. Redistributions in binary form must reproduce the above copyright notice,
*      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
*   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
*      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
*      endorse or promote products derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
* IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
* EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
* STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

// #define STRING_SIZE 2048

// One such record is stored for each page, in the indes file
// Zero-Zero means not present.
// These get stored in big endian order
typedef struct {
  long long offset;
  long long size;
} index_s;

typedef struct {
  int psizex,psizey; // page size in pixels
  int xcount,ycount; // page count on X and Y
  long long index_add; // Value to be added to the index record offset when
                       // reading and writing to the index file. This allows
                       // for index files to be shared between levels.
  index_s empty_record; // Default page pointer. Leave 0,0 if not used.

  // Bounding box for the level
  double X0, Y0, X1, Y1;

  // values for the pages size.
  double levelx,levely;

  // These are pointers or offsets
  char *dfname;
  char *ifname;
  char *default_dfname;
  char *default_ifname;
} WMSlevel;

typedef struct {
  int size; // The size of the cache structure on disk.
            // It is equal to the size of the current structure+levels*sizeof(WMSlevel)
  int levels;  // How many levels are there
  int levelt_offset;
           // offset of the level structure table, from the cache itself
  int signature; // Content of the first four bytes of each page.
                 // Architecture independent. Set to 0 if not used.
  int orientation; // flag for page orientation. 0 is top-left, 1 is bottom-right
  int num_patterns; // num_patterns
  char *pattern; // patterns that cache matcheS
  char *prefix;
  char *time_period;
  char *zidxfname;
  char *default_zidxfname;
  int num_periods;
  int zlevels; // the max number of z levels
} WMSCache;

typedef struct { // One of these per cache pack
  int size; // Size of all records, plus the strings
  int count; // How many WMSCache records are there
} Caches;

// Macro to get the offset of the X-th cache giving the pointer to the cache file
#define GETCACHE(C,X) ((WMSCache *) ( ((char *) C) + sizeof(Caches) + X*sizeof(WMSCache) ))
// Macro to get a pointer to the level table of a given cache C, relative to the cache itself
#define GETLEVELS(C) ((WMSlevel *) ( ((char *) C) + C->levelt_offset ))
