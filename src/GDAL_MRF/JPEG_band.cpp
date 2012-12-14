


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
 * JPEG band
 * JPEG page compression and decompression functions
 *
 */

#include "marfa.h"
#include <setjmp.h>

CPL_C_START
#include "../jpeg/libjpeg/jpeglib.h"
CPL_C_END

/**
 *\Brief Helper class for jpeg error management
 */

struct ErrorMgr: public jpeg_error_mgr {
    inline ErrorMgr();
    int signaled() { return setjmp(setjmpBuffer); };
    jmp_buf setjmpBuffer;
};

/**
 *\brief Called when jpeg wants to report a warning
 * msgLevel can be:
 * -1 Corrupt data
 * 0 always display
 * 1... Trace level
 */

static void emitMessage (j_common_ptr cinfo, int msgLevel) 
{
    jpeg_error_mgr* err=cinfo->err;
    if (msgLevel > 0) return; // No trace msgs
    // There can be many warnings, just print the first one
    if (err->num_warnings++ >1) return;
    char buffer[JMSG_LENGTH_MAX];
    err->format_message(cinfo,buffer);
    CPLError(CE_Failure,CPLE_AppDefined,buffer);
}

static void errorExit(j_common_ptr cinfo)
{
  ErrorMgr* err = (ErrorMgr*)cinfo->err;
  // format the warning message
  char buffer[JMSG_LENGTH_MAX];

  err->format_message(cinfo, buffer);
  CPLError(CE_Failure,CPLE_AppDefined,buffer);
  // return control to the setjmp point
  longjmp(err->setjmpBuffer,1);
}

/**
 *\bried set up the normal JPEG error routines, then override error_exit
 */
ErrorMgr::ErrorMgr()
{
    jpeg_std_error(this);
    error_exit=errorExit;
    emit_message=emitMessage;
}

/**
 *\Brief Do nothing stub function for JPEG library, called
 */
void stub_source_dec(j_decompress_ptr cinfo) {};

/**
 *\Brief: Do nothing stub function for JPEG library, called?
 */
boolean fill_input_buffer_dec(j_decompress_ptr cinfo) {return TRUE;};

/**
 *\Brief: Do nothing stub function for JPEG library, not called
 */
void skip_input_data_dec(j_decompress_ptr cinfo, long l) {};

// Destination should be already set up
static void init_or_terminate_destination(j_compress_ptr cinfo) {}

// Called if the buffer provided is too small
static boolean empty_output_buffer(j_compress_ptr cinfo) {
    std::cerr << "JPEG Output buffer empty called\n";
    return FALSE;
}

/*
 *\Brief Compress a JPEG page
 * 
 * For now it only handles byte data, grayscale, RGB or CMYK
 *
 * Returns the compressed size in dest.size
 */

CPLErr CompressJPEG(buf_mgr &dst, buf_mgr &src, const ILImage &img) 

{

    // The cinfo should stay open and reside in the DS, since it can be left initialized
    // It saves some time because it has the tables initialized
    struct jpeg_compress_struct cinfo;
    ErrorMgr jerr;
//    ILImage *img=&(pmDS->current);

    jpeg_destination_mgr jmgr;
    jmgr.next_output_byte=(JOCTET *)dst.buffer;
    jmgr.free_in_buffer=dst.size;
    jmgr.init_destination=init_or_terminate_destination;
    jmgr.empty_output_buffer=empty_output_buffer;
    jmgr.term_destination=init_or_terminate_destination;

    // Look at the source of this, some interesting tidbits
    jpeg_create_compress(&cinfo);
    cinfo.dest=&jmgr;
    cinfo.err=&jerr;

    // The page specific info, size and color spaces
    cinfo.image_width=img.pagesize.x;
    cinfo.image_height=img.pagesize.y;
    cinfo.input_components=img.pagesize.c;
    switch (cinfo.input_components) {
    case 1:cinfo.in_color_space=JCS_GRAYSCALE; break;
    case 4:cinfo.in_color_space=JCS_CMYK; break;
    default:cinfo.in_color_space=JCS_RGB;
    }

    // Set all required fields and overwrite the ones we want to change
    jpeg_set_defaults(&cinfo);

    jpeg_set_quality(&cinfo,img.quality,TRUE);
    cinfo.dct_method=JDCT_FLOAT;

    int linesize=cinfo.image_width*cinfo.num_components*((cinfo.data_precision==8)?1:2);
    JSAMPROW *rowp=(JSAMPROW *)CPLMalloc(sizeof(JSAMPROW)*img.pagesize.y);
    for (int i=0;i<img.pagesize.y;i++)
        rowp[i]=(JSAMPROW)(src.buffer+i*linesize);

    if (jerr.signaled()) {
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: JPEG compression error");
        jpeg_destroy_compress(&cinfo);
        CPLFree(rowp);
        return CE_Failure;
    }
    
    jpeg_start_compress(&cinfo,TRUE);
    jpeg_write_scanlines(&cinfo,rowp,img.pagesize.y);
    jpeg_finish_compress(&cinfo);
    jpeg_destroy_compress(&cinfo);

    CPLFree(rowp);

    // Figure out the size
    dst.size-=jmgr.free_in_buffer;

    return CE_None;
}

/**
 *\brief In memory decompression of JPEG file
 *
 * @param data pointer to output buffer 
 * @param png pointer to PNG in memory
 * @param sz if non-zero, test that uncompressed data fits in the buffer.
 */

CPLErr DecompressJPEG(buf_mgr &dst,buf_mgr &isrc) 

{
    // Locals, clean up after themselves
    jpeg_decompress_struct cinfo={0};
    ErrorMgr jerr;

    struct jpeg_source_mgr src={(JOCTET *)isrc.buffer,isrc.size};

    cinfo.err=&jerr;
    src.term_source=src.init_source=stub_source_dec;
    src.skip_input_data=skip_input_data_dec;
    src.fill_input_buffer=fill_input_buffer_dec;
    src.resync_to_restart=jpeg_resync_to_restart;

    if (jerr.signaled()) {
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error reading JPEG page");
        return CE_Failure;
    }
    jpeg_create_decompress(&cinfo);
    cinfo.src=&src;
    jpeg_read_header(&cinfo,TRUE);
    // Use float, it is actually faster than the ISLOW method by a tiny bit
    cinfo.dct_method=JDCT_FLOAT;
    jpeg_start_decompress(&cinfo);
    int linesize=cinfo.image_width*cinfo.num_components*((cinfo.data_precision==8)?1:2);
    // We have a missmatch between the real and the declared data format
    // warn and fail if output buffer is too small
    if (linesize*cinfo.image_height!=dst.size) {
        CPLError(CE_Warning,CPLE_AppDefined,"MRF: read JPEG size is wrong");
        if (linesize*cinfo.image_height>dst.size) {
            CPLError(CE_Failure,CPLE_AppDefined,"MRF: JPEG decompress buffer insufficient");
            jpeg_destroy_decompress(&cinfo);
            return CE_Failure;
        }
    }
    // Decompress, two lines at a time
    while (cinfo.output_scanline < cinfo.image_height ) {
        char *rp[2];
        rp[0]=(char *)dst.buffer+linesize*cinfo.output_scanline;
        rp[1]=rp[0]+linesize;
        // if this fails, it calls the error handler
        // which will report an error
        jpeg_read_scanlines(&cinfo,JSAMPARRAY(rp),2);
    }
    jpeg_finish_decompress(&cinfo);
    jpeg_destroy_decompress(&cinfo);
    return CE_None;
}

CPLErr JPEG_Band::Decompress(buf_mgr &dst, buf_mgr &src) 
{ 
    return DecompressJPEG(dst,src); 
}

CPLErr JPEG_Band::Compress(buf_mgr &dst, buf_mgr &src,const ILImage &img) 
{ 
    return CompressJPEG(dst,src,img);
}

