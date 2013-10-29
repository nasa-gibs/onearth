

/*
* Copyright (c) 2002-2012, California Institute of Technology.
* All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.

* Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
*   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
*   2. Redistributions in binary form must reproduce the above copyright notice, 
*      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
*   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL), 
*      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to 
*      endorse or promote products derived from this software without specific prior written permission.

* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
* IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
* EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
* STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*/



/*
 * $Id$
 * TIFF band
 * TIFF page compression and decompression functions
 * These functions are not methods, they reside in the global space
 *
 */

// This can get complicated, since the TIFFs can be have many options, and it can't be written in a buffer
// It also has to take into account the data type and the tile size
//
// Probably the best would be to use GDAL itself to read/write a tif.
//

#include "marfa.h"

CPLErr CompressTIF(buf_mgr &dst, buf_mgr &src, const ILImage &img)
{
    return CE_None;
}

CPLErr DecompressTIF(buf_mgr &dst, buf_mgr &src)
{
    return CE_None;
}

CPLErr TIF_Band::Decompress(buf_mgr &dst, buf_mgr &src) 
{ 
    return DecompressTIF(dst,src); 
}
CPLErr TIF_Band::Compress(buf_mgr &dst, buf_mgr &src,const ILImage &img) 
{ 
    return CompressTIF(dst,src,img); 
}
