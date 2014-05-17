/*
* Copyright (c) 2002-2012, California Institute of Technology.
* All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
* Redistribution and use in source and binary forms, with or without modification, are permitted provided 
* that the following conditions are met:
*   1. Redistributions of source code must retain the above copyright notice, this list of conditions and 
*      the following disclaimer.
*   2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and 
*      the following disclaimer in the documentation and/or other materials provided with the distribution.
*   3. Neither the name of the California Institute of Technology (Caltech), its operating division the 
*      Jet Propulsion Laboratory (JPL), the National Aeronautics and Space Administration (NASA), 
*      nor the names of its contributors may be used to endorse or promote products derived from this software
*      without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
* IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
* EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
* STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/*
 * TIFF band
 * TIFF page compression and decompression functions
 *
 * Author:  Lucian Plesea, lplesea@esri.com
 *
 */

#include "marfa.h"

// Returns a string in /vsimem/ + prefix + count that doesn't exist when this function gets called
// It is not completely safe, open the result as soon as possible
CPLString uniq_memfname(const char *prefix)
{
    CPLString fname;
    VSIStatBufL statb;
    static unsigned int cnt=0;
    do fname.Printf("/vsimem/%s_%08x",prefix, cnt++);
    while (!VSIStatL(fname, &statb));
    return fname;
}

//
// Uses GDAL to create a temporary TIF file, using the band create options
// copies the content to the destination buffer then erases the temp TIF
//
CPLErr CompressTIF(buf_mgr &dst, buf_mgr &src, const ILImage &img, char **papszOptions)
{
    CPLErr ret;
    CPLString fname;
    GDALDriver *poTiffDriver = GetGDALDriverManager()->GetDriverByName("GTiff");
    VSIStatBufL statb;
    // No point to check return or capabilities, GDAL had geotiff

// #define MRF_LOCAL_TMP
// Define MRF_LOCAL_TMP to use local files instead of RAM
#if defined(MRF_LOCAL_TMP)
    // This is a good alternative but uses the local temp folder
    fname = CPLGenerateTempFilename("mrf_tif_write");
#else
    // This is troublesome, filenames are not guaranteed to be unique
    // But it is in memory, so it is likely to be faster
    fname = uniq_memfname("mrf_tif_write");
#endif


    GDALDataset *poTiff = poTiffDriver->Create(fname, img.pagesize.x, img.pagesize.y,
	img.pagesize.c, img.dt, papszOptions );

    // Read directly to avoid double caching in GDAL
    // Unfortunately not possible for multiple bands
    if (img.pagesize.c == 1) {
	ret = poTiff->GetRasterBand(1)->WriteBlock(0,0,src.buffer);
    } else {
	ret = poTiff->RasterIO(GF_Write, 0,0,img.pagesize.x,img.pagesize.y, 
	    src.buffer, img.pagesize.x, img.pagesize.y, img.dt, img.pagesize.c, 
	    NULL, 0,0,0);
    }
    if (CE_None != ret)	return ret;

    // poTiff->FlushCache();
    // Delete flushes and closes the file
    GDALClose(poTiff);

    // Check that we can could read the file
    if (VSIStatL(fname, &statb))
    {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, cant stat %s", fname.c_str()));
        return CE_Failure;
    }

    if (statb.st_size > dst.size)
    {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, Tiff too large"));
        return CE_Failure;
    }

    VSILFILE *pf = VSIFOpenL(fname,"rb");
    if (pf == NULL)
    {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, cant open %s", fname.c_str()));
        return CE_Failure;
    }
    
    VSIFReadL(dst.buffer, statb.st_size, 1, pf);
    dst.size = statb.st_size;
    VSIFCloseL(pf);
    if (VSIUnlink(fname)) {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, cant unlink"));
        return CE_Failure;
    }

    return CE_None;
}

// Read from a RAM Tiff. This is rather generic
CPLErr DecompressTIF(buf_mgr &dst, buf_mgr &src, const ILImage &img)
{
    CPLString fname = uniq_memfname("mrf_tif_read");
    VSILFILE *fp = VSIFileFromMemBuffer(fname, (GByte *)(src.buffer), src.size, false);
    if (fp) VSIFCloseL(fp);
    else {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, cant open %s as a temp file", fname.c_str()));
        return CE_Failure;
    }
    GDALDataset *poTiff = reinterpret_cast<GDALDataset*>(GDALOpen(fname, GA_ReadOnly));
    if (!fp) {
	CPLError(CE_Failure,CPLE_AppDefined,
	    CPLString().Printf("MRF: TIFF, cant open page as a Tiff"));
        return CE_Failure;
    }

    CPLErr ret;
    // Bypass the GDAL caching
    if (img.pagesize.c == 1) {
	ret = poTiff->GetRasterBand(1)->ReadBlock(0,0,dst.buffer);
    } else {
	ret = poTiff->RasterIO(GF_Read,0,0,img.pagesize.x,img.pagesize.y, 
	    dst.buffer, img.pagesize.x, img.pagesize.y, img.dt, img.pagesize.c, 
	    NULL, 0,0,0);
    }

    if (CE_None != ret)
	return ret;

    GDALClose(poTiff);

    // This just removes the reference from vmem, the buffer stays allocated
    VSIUnlink(fname);

    char **dirlist = CPLReadDir("/vsimem/");
    CSLPrint(dirlist,stdout);
    CSLDestroy(dirlist);

    return CE_None;
}

CPLErr TIF_Band::Decompress(buf_mgr &dst, buf_mgr &src) 
{ 
    return DecompressTIF(dst, src, img);
}
CPLErr TIF_Band::Compress(buf_mgr &dst, buf_mgr &src,const ILImage &img) 
{ 
    return CompressTIF(dst,src,img, papszOptions); 
}

TIF_Band::TIF_Band(GDALMRFDataset *pDS, const ILImage &image, int b, int level):
        GDALMRFRasterBand(pDS,image,b,int(level))
{
    // Increase the page buffer by 1K in case Tiff expands data
    pDS->SetPBuffer(image.pageSizeBytes + 1024);

    // Static create options for TIFF tiles
    papszOptions = CSLAddNameValue(NULL, "COMPRESS", "DEFLATE");
    papszOptions = CSLAddNameValue(papszOptions, "TILED", "Yes");
    papszOptions = CSLAddNameValue(papszOptions, "BLOCKXSIZE", CPLString().Printf("%d",img.pagesize.x));
    papszOptions = CSLAddNameValue(papszOptions, "BLOCKYSIZE", CPLString().Printf("%d",img.pagesize.y));
    int q = img.quality / 10;
    // Move down so the default 85 maps to 6.  This makes the maz ZLEVEL 8, which is OK
    if (q >2) q-=2;
    papszOptions = CSLAddNameValue(papszOptions, "ZLEVEL", CPLString().Printf("%d",q));
};

TIF_Band::~TIF_Band() 
{
    CSLDestroy(papszOptions);
};
