

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
 * PNG band
 * PNG page compression and decompression functions
 * These functions are not methods, they reside in the global space
 *
 */

#include "marfa.h"

CPL_C_START
#include "../png/libpng/png.h"
CPL_C_END

//Lucian recommended to change the following three lines to above as
// it is causing trouble compiling for AMNH folks.
//CPL_C_START
//#include <png.h>
//CPL_C_END

// Do Nothing
void flush_png(png_structp) {}

// Warning Emit
void pngWH(png_struct *png,png_const_charp message) 
{
    CPLError(CE_Warning,CPLE_AppDefined,"MRF: PNG warning %s",message);
}

// Fatal Warning
void pngEH(png_struct *png, png_const_charp message) 
{
    CPLError(CE_Failure,CPLE_AppDefined,"MRF: PNG Failure %s",message);
    longjmp(png->jmpbuf,1);
}

// Read memory handlers for PNG
// No check for attempting to read past the end of the buffer

void read_png(png_structp pngp, png_bytep data, png_size_t length)
{
    buf_mgr *pmgr=(buf_mgr *)png_get_io_ptr(pngp);
    memcpy(data,pmgr->buffer,length);
    pmgr->buffer+=length;
    pmgr->size-=length;
}

void write_png( png_structp pngp, png_bytep data, png_size_t length) {
    buf_mgr *mgr=(buf_mgr *) png_get_io_ptr(pngp);

    if (length<=mgr->size) {
        memcpy(mgr->buffer,data,length);
        mgr->buffer+=length;
        mgr->size-=length;
    } else {
	// This is a bad error actually, but we can't report errors
        CPLError(CE_Warning,CPLE_AppDefined,
            "MRF: PNG Write buffer too small!!");
        memcpy(mgr->buffer,data,mgr->size);
        mgr->buffer+=mgr->size;
        mgr->size=0;
    }
}

/**
 *\brief In memory decompression of PNG file
 */

CPLErr PNG_Band::DecompressPNG(buf_mgr &dst, buf_mgr &src) 
{
    png_bytep *png_rowp;

    // pngp=png_create_read_struct(PNG_LIBPNG_VER_STRING,0,pngEH,pngWH);
    png_structp pngp=png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (0 == pngp) {
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error creating PNG decompress");
        return CE_Failure;
    }

    png_infop infop=png_create_info_struct(pngp);
    if ( 0 == infop ) {
        if (pngp) png_destroy_read_struct(&pngp,&infop,0);
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error creating PNG info");
        return CE_Failure;
    }

    if (setjmp(png_jmpbuf(pngp))) {
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error starting PNG decompress");
        return CE_Failure;
    }

    // The mgr data ptr is already set up
    png_set_read_fn(pngp,&src,read_png);
    // Ready to read
    png_read_info(pngp,infop);
    GInt32 height=png_get_image_height(pngp,infop);
    GInt32 byte_count=png_get_bit_depth(pngp,infop)/8;
    // Check the size
    if (dst.size<(png_get_rowbytes(pngp,infop)*height)) {
        CPLError(CE_Failure,CPLE_AppDefined,
            "MRF: PNG Page data bigger than the buffer provided");
        png_destroy_read_struct(&pngp,&infop,0);
        return CE_Failure;
    }

    png_rowp=(png_bytep *)CPLMalloc(sizeof(png_bytep)*height);

    int rowbytes=png_get_rowbytes(pngp,infop);
    for(int i=0;i<height;i++)
        png_rowp[i]=(png_bytep)dst.buffer+i*rowbytes;

    // Finally, the read
    // This is the lower level, the png_read_end allows some transforms
    // Like pallete to RGBA
    png_read_image(pngp,png_rowp);

    if (byte_count!=1) { // Swap from net order if data is short
        for (int i=0;i<height;i++) {
            unsigned short int*p=(unsigned short int *)png_rowp[i];
            for (int j=0; j<rowbytes/2; j++,p++)
				*p=net16(*p);
        }
    }

    //    ppmWrite("Test.ppm",(char *)data,ILSize(512,512,1,4,0));
    // Required
    png_read_end(pngp,infop);

    // png_set_rows(pngp,infop,png_rowp);
    // png_read_png(pngp,infop,PNG_TRANSFORM_IDENTITY,0);

    CPLFree(png_rowp);
    png_destroy_read_struct(&pngp,&infop,0);
    return CE_None;
}

/**
 *\Brief Compres a page in PNG format
 * Returns the compressed size in dst.size
 *
 */

CPLErr PNG_Band::CompressPNG(buf_mgr &dst, buf_mgr &src) 

{
    png_structp pngp;
    png_infop infop;
    buf_mgr mgr=dst;

    pngp=png_create_write_struct(PNG_LIBPNG_VER_STRING,NULL,pngEH,pngWH);
    if (!pngp) {
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error creating png structure");
        return CE_Failure;
    }
    infop=png_create_info_struct(pngp);
    if (!infop) {
        png_destroy_write_struct(&pngp,NULL);
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error creating png info structure");
        return CE_Failure;
    }

    if (setjmp(png_jmpbuf(pngp))) {
        png_destroy_write_struct(&pngp,&infop);
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error during png init");
        return CE_Failure;
    }

    png_set_write_fn(pngp,&mgr,write_png,flush_png);

    int png_ctype;

    switch (img.pagesize.c) {
    case 1: if (PNGColors!=NULL) png_ctype=PNG_COLOR_TYPE_PALETTE;
            else png_ctype=PNG_COLOR_TYPE_GRAY; 
            break;
    case 2: png_ctype=PNG_COLOR_TYPE_GRAY_ALPHA; break;
    case 3: png_ctype=PNG_COLOR_TYPE_RGB; break;
    case 4: png_ctype=PNG_COLOR_TYPE_RGB_ALPHA; break;
    default: { // This never happens if we check at the open
        CPLError(CE_Failure,CPLE_AppDefined,"MRF:PNG Write with %d colors called",
            img.pagesize.c);
        return CE_Failure;
             }
    }

    png_set_IHDR(pngp, infop, img.pagesize.x, img.pagesize.y, 
        GDALGetDataTypeSize(img.dt), png_ctype,
        PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

	// Optional, force certain filters only.  Makes it somewhat faster but worse compression
	// png_set_filter(pngp, PNG_FILTER_TYPE_BASE, PNG_FILTER_SUB);
	
#if defined(PNG_LIBPNG_VER) && (PNG_LIBPNG_VER > 10200)
	png_uint_32 mask, flags;

	flags = png_get_asm_flags(pngp);
	mask = png_get_asm_flagmask(PNG_SELECT_READ | PNG_SELECT_WRITE);
	png_set_asm_flags(pngp, flags | mask); // use flags &~mask to disable all

	// Test that the MMX is compiled into PNG
//	fprintf(stderr,"MMX support is %d\n", png_mmx_support());

#endif

	// Should let the quality control the compression level

    // Write the palete and the transparencies if they exist
    if (PNGColors!=NULL)
    {
        png_set_PLTE( pngp, infop, (png_colorp) PNGColors,PalSize );
        if (TransSize!=0)
            png_set_tRNS( pngp, infop, (unsigned char*) PNGAlpha, TransSize, NULL );
    }

    png_write_info (pngp,infop);

    png_bytep *png_rowp=(png_bytep *)CPLMalloc(sizeof(png_bytep)*img.pagesize.y);

    if (setjmp(png_jmpbuf(pngp))) {
        CPLFree(png_rowp);
        png_destroy_write_struct(&pngp,&infop);
        CPLError(CE_Failure,CPLE_AppDefined,"MRF: Error during png compression");
        return CE_Failure;
    }

    int rowbytes=png_get_rowbytes(pngp,infop);
    for (int i=0;i<img.pagesize.y;i++) {
        png_rowp[i]=(png_bytep)(src.buffer+i*rowbytes);
        if (img.dt!=GDT_Byte) { // Swap to net order if data is short
            unsigned short int*p=(unsigned short int *)png_rowp[i];
            for (int j=0;j<rowbytes/2;j++,p++) *p=net16(*p);
        }
    }

    png_write_image(pngp,png_rowp);
    png_write_end(pngp,infop);

    // Done
    CPLFree(png_rowp);
    png_destroy_write_struct(&pngp,&infop);
    
    // Done
    // mgr.size holds the available bytes, so the size of the compressed png
    // is the original destination size minus the still available bytes
    dst.size-=mgr.size;

    return CE_None;
}

CPLErr PNG_Band::Decompress(buf_mgr &dst, buf_mgr &src)
{
    return DecompressPNG(dst,src);
}

CPLErr PNG_Band::Compress(buf_mgr &dst, buf_mgr &src,const ILImage &img)
{
    return CompressPNG(dst,src);
}


/**
 * \Brief For PPNG, builds the data structures needed to write the palette
 * The presence of the PNGColors and PNGAlpha is used as a flag for PPNG only
 * The palette must be defined when creating the band
 */

PNG_Band::PNG_Band(GDALMRFDataset *pDS, const ILImage &image, int b, int level) : 
	GDALMRFRasterBand(pDS,image,b,level),PNGColors(NULL),PNGAlpha(NULL)

{
    if (image.comp==IL_PPNG)
    {  // Convert the GDAL LUT to PNG style
        GDALColorTable *poCT=GetColorTable();
        TransSize=PalSize=poCT->GetColorEntryCount();

        png_color *pasPNGColors = (png_color *) CPLMalloc(sizeof(png_color) * PalSize);
        unsigned char *pabyAlpha = (unsigned char *)CPLMalloc(TransSize);
        PNGColors=(void *)pasPNGColors;
        PNGAlpha=(void *)pabyAlpha;
        bool NoTranspYet=true;

	// Set the palette from the end to reduce the size of the opacity mask
        for ( int iColor = PalSize-1; iColor >=0 ; iColor-- )
        {
	    GDALColorEntry  sEntry;
	    poCT->GetColorEntryAsRGB( iColor, &sEntry );

	    pasPNGColors[iColor].red = (png_byte) sEntry.c1;
	    pasPNGColors[iColor].green = (png_byte) sEntry.c2;
	    pasPNGColors[iColor].blue = (png_byte) sEntry.c3;
	    if (NoTranspYet && sEntry.c4==255)
		TransSize--;
	    else {
		NoTranspYet=false;
		pabyAlpha[iColor]=(unsigned char) sEntry.c4;
            }
        }
    }
}

PNG_Band::~PNG_Band() {
    CPLFree(PNGColors);
    CPLFree(PNGAlpha);
}
