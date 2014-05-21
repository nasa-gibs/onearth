
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


/******************************************************************************
* $Id$
*
* Project:  Meta Raster File Format Driver Implementation, RasterBand
* Purpose:  Implementation of Pile of Tile Format
*
* Author:   Lucian Plesea, Lucian.Plesea@jpl.nasa.gov, lplesea@esri.com
*
******************************************************************************
*
*
* 
*
* 
****************************************************************************/

#include "marfa.h"
#include <gdal_priv.h>
#include <ogr_srs_api.h>
#include <ogr_spatialref.h>

#include <vector>

using std::vector;
using std::string;

// Is the buffer filled with zeros
inline int is_zero(char *b,size_t count)
{
    while (count--) if (*b++) return 0;
    return TRUE;
}

// Does every byte in the buffer have the same value
inline int is_empty(char *b,size_t count, char val=0)

{
    while (count--) if (*(b++)!=val) return 0;
    return TRUE;
}

// Swap bytes in place, unconditional

static void swab_buff(buf_mgr &src, const ILImage &img)
{
	switch (GDALGetDataTypeSize(img.dt)) {
	case 16: {
		short int *b=(short int*)src.buffer;
		for (int i=src.size/2;i;b++,i--) 
			*b=swab16(*b);
		break;
			 }
	case 32: {
		int *b=(int*)src.buffer;
		for (int i=src.size/4;i;b++,i--) 
			*b=swab32(*b);
		break;
			 }
	case 64: {
		long long *b=(long long*)src.buffer;
		for (int i=src.size/8;i;b++,i--)
			*b=swab64(*b);
		break;
			 }
	}
}

GDALMRFRasterBand::GDALMRFRasterBand(GDALMRFDataset *parent_dataset,
					const ILImage &image, int band, int ov)
{
    poDS=parent_dataset;
    m_band=band-1;
    m_l=ov;
    img=image;
    eDataType=parent_dataset->current.dt;
    nRasterXSize = img.size.x;
    nRasterYSize = img.size.y;
    nBlockXSize = img.pagesize.x;
    nBlockYSize = img.pagesize.y;
    nBlocksPerRow = img.pcount.x;
    nBlocksPerColumn = img.pcount.y;
    dfp = ifp = NULL;
    img.NoDataValue = GetNoDataValue( &img.hasNoData);
}

// Clean up the overviews if they exist
GDALMRFRasterBand::~GDALMRFRasterBand()
{
    while (0!=overviews.size()) {
	delete overviews[overviews.size()-1];
	overviews.pop_back();
    };
}

// Look for a string from the dataset options or from the environment
const char * GDALMRFRasterBand::GetOptionValue(const char *opt, const char *def)
{
    const char *optValue = CSLFetchNameValue(poDS->optlist, opt);
    if (0 != optValue)
	return optValue;
    return CPLGetConfigOption(opt, def);
}

/************************************************************************/
/*                       GetColorInterpretation()                       */
/************************************************************************/

GDALColorInterp GDALMRFRasterBand::GetColorInterpretation()
{
    if (poDS->GetColorTable()) 
	return GCI_PaletteIndex;
    return BandInterp(poDS->nBands, m_band+1);
}

// Utility function, returns a value from a vector corresponding to the band index
// or the first entry
static double getBandValue(std::vector<double> &v,int idx)
{
    if (static_cast<int>(v.size()) > idx)
	return v[idx];
    return v[0];
}

double GDALMRFRasterBand::GetNoDataValue(int *pbSuccess)
{
    std::vector<double> &v=poDS->vNoData;
    if (v.size() == 0)
	return GDALPamRasterBand::GetNoDataValue(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v, m_band);
}

double GDALMRFRasterBand::GetMinimum(int *pbSuccess)
{
    std::vector<double> &v=poDS->vMin;
    if (v.size() == 0)
	return GDALPamRasterBand::GetMinimum(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v, m_band);
}

double GDALMRFRasterBand::GetMaximum(int *pbSuccess)
{
    std::vector<double> &v=poDS->vMax;
    if (v.size() == 0)
	return GDALPamRasterBand::GetMaximum(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v, m_band);
}


/**
*\brief Fills a buffer with no data
*
*/
CPLErr GDALMRFRasterBand::IFillBlock(void *buffer)
{
    if ((eDataType == GDT_Byte) && poDS->vNoData.size())
	memset(buffer, (char) GetNoDataValue(0), blockSizeBytes());
    else
	memset(buffer, 0, blockSizeBytes());
    return CE_None;
}

/**
*\brief Fetch a block from the backing store dataset and make a copy in the cache
*
* @xblk The X block number, zero based
* @yblk The Y block number, zero based
* @param tinfo The return, updated tinfo for this specific tile
*
*/
CPLErr GDALMRFRasterBand::IFetchBlock(int xblk, int yblk)

{
    CPLDebug("MRF_IB","IFetchBlock %d,%d,0,%d, level  %d\n",xblk,yblk,m_band,m_l);

    GDALDataset *poSrcDS;
    GInt32 cstride = img.pagesize.c;
    ILSize req(xblk, yblk, 0, m_band/cstride, m_l);

    if (poDS->source.empty()) {
	CPLError( CE_Failure, CPLE_AppDefined, "MRF: No cached source image to fetch from");
	return CE_Failure;
    }
    if ( 0 == (poSrcDS = poDS->GetSrcDS())) {
	CPLError( CE_Failure, CPLE_AppDefined, "MRF: Can't open source file %s", poDS->source.c_str());
	return CE_Failure;
    }

    // Mark the current buffer as invalid
    poDS->tile=ILSize();

    // Scale to base resolution
    double scl = pow(poDS->scale, m_l);
    if (0 == m_l) scl = 1; // No scaling for base level
    // How many bytes does a single band take
    int vsz = GDALGetDataTypeSize(eDataType)/8;
    int Xoff = xblk * img.pagesize.x * scl;
    int Yoff = yblk * img.pagesize.y * scl;
    int readszx = img.pagesize.x * scl;
    int readszy = img.pagesize.y * scl;

    // Compare with the full size and clip if needed
    int clip=0;
    if (Xoff + readszx > poDS->full.size.x) {
	clip |= 1;
	readszx = poDS->full.size.x - Xoff;
    }
    if (Yoff + readszy > poDS->full.size.y) {
	clip |= 1;
	readszy = poDS->full.size.y - Yoff;
    }

    // Fill buffer with NoData if clipping
    if (clip)
	IFillBlock(poDS->pbuffer);

    // Which bands to read
    int *panBandMap = new int[cstride];
    for (int i=0 ; i < cstride; i++)
	panBandMap[i] = m_band + i + 1;

    // Use the dataset RasterIO if reading all bands
    CPLErr ret = poSrcDS->RasterIO( GF_Read, Xoff, Yoff, readszx, readszy,
	poDS->pbuffer, pcount(readszx, int(scl)), pcount(readszy, int(scl)),
	eDataType, cstride, panBandMap,
	// pixel, line, band stride
	vsz * img.pagesize.c,
	vsz * img.pagesize.c * img.pagesize.x, 
	vsz * img.pagesize.c * img.pagesize.x * img.pagesize.y );

    delete[] panBandMap;

    if (ret != CE_None)
	return ret;
    // Got the block in the pbuffer, mark it
    poDS->tile = req;

    // If it should not be stored, mark it as such
    if (eDataType == GDT_Byte && poDS->vNoData.size()) {
	if (is_empty((char *)poDS->pbuffer, img.pageSizeBytes, (char)GetNoDataValue(0)))
	    return WriteTile(req, (void *)1, 0);
    } else if (is_zero((char *)poDS->pbuffer, img.pageSizeBytes))
	return WriteTile(req, (void *)1, 0);

    // Write the page in the local cache
    buf_mgr src={(char *)poDS->pbuffer, img.pageSizeBytes};

    // Have to use a separate buffer.  We should make this one permanent too.
    void *outbuff = CPLMalloc(poDS->pbsize);

    if (!outbuff) {
	CPLError(CE_Failure, CPLE_AppDefined, 
	    "Can't get buffer for writing page");
	// This is not an error for a cache, the data is fine
	return CE_Failure;
    }

    buf_mgr dst={(char *)outbuff, poDS->pbsize};
    Compress(dst, src, img);

    // Update the tile index here
    ret = WriteTile(req, outbuff, dst.size);
    CPLFree(outbuff);

    return ret;
}

/**
*\brief read a block in the provided buffer
* 
*  For separate band model, the DS buffer is not used, the read is direct
*  For pixel interleaved model, the DS buffer holds the temp copy
*  and all the other bands are forced read.
*
*/
CPLErr GDALMRFRasterBand::IReadBlock(int xblk, int yblk, void *buffer)

{
    ILIdx tinfo;
    GInt32 cstride=img.pagesize.c;
    ILSize req(xblk,yblk,0,m_band/cstride,m_l);
    VSILFILE *dfp=DataFP();

    if (dfp == NULL)
	return CE_Failure;

    CPLDebug("MRF_IB","IReadBlock %d,%d,0,%d, level  %d\n",xblk,yblk,m_band,m_l);

    // Size of the buffer is the size of a page for a single band, single slice
    // If a new page needs to be read and decompressed, do this:
    if ((req.x!=poDS->tile.x || req.y!=poDS->tile.y || req.z!=poDS->tile.z || req.l!=poDS->tile.l)
	|| (1 == cstride && req.c != m_band)
	)
    {
	if (CE_None != ReadTileIdx(req, tinfo)) {
	    CPLError( CE_Failure, CPLE_AppDefined,
		"MRF: Unable to read index at offset %lld", IdxOffset(req, img));
	    return CE_Failure;
	}

	CPLDebug("MRF_IB","Tinfo offset %lld, size %lld\n", tinfo.offset, tinfo.size);
	// No source or tinfo.offset != 0 means there is no reason to check the source
	if (0 == tinfo.size) {
	    // since the pmDS->tile hasn't changed, each empty band will
	    // just read the tile info and return
	    if ( 0 != tinfo.offset || poDS->source.empty() || GA_Update == poDS->eAccess )
		return IFillBlock(buffer);

	    if (CE_None != IFetchBlock(xblk, yblk)) {
		CPLError(CE_Failure, CPLE_AppDefined, "MRF: Unable to fetch data page, %d@%d",xblk ,yblk);
		return CE_Failure;
	    }

	    // Try again, after the fetch
	    return IReadBlock(xblk, yblk, buffer);
	}


	// Should use a permanent IO buffer to avoid repeated allocations
	void *data = CPLMalloc(tinfo.size);
	VSIFSeekL(dfp, tinfo.offset, SEEK_SET);
	if (1 != VSIFReadL(data, tinfo.size, 1, dfp)) {
	    CPLFree(data);
	    CPLError(CE_Failure, CPLE_AppDefined, "Unable to read data page, %lld@%lld",
		tinfo.size, tinfo.offset);
	    return CE_Failure;
	}

	// We got the data, mark the buffer as invalid for now
	if (1!=cstride)
	    poDS->tile=ILSize();
	CPLErr ret;

	buf_mgr src={(char *)data, tinfo.size};

	// For reading, the size has to be pageSizeBytes
	buf_mgr dst={(char *)poDS->pbuffer, img.pageSizeBytes};

	// If pages are separate, uncompress directly in output buffer
	if (1==cstride)
	    dst.buffer=(char *)buffer;

	ret = Decompress(dst, src);
	if (CE_None!=ret)
	    return ret;

	dst.size = img.pageSizeBytes; // In case decompress failed, force it back

	// Swap whatever we decompressed if we need to
	if (is_Endianess_Dependent(img.dt,img.comp)&&(img.nbo!=NET_ORDER)) 
	    swab_buff(dst, img);

	// Safe if null
	CPLFree(data);

	// If pages are separate, we're done, the read was in the output buffer
	if (1==cstride)
	    return CE_None;

	// Got the page correctly, so let the other bands know
	poDS->tile = req;

	// Force load of the other bands only if the order is interleaved,
	// they are already unpacked in the DS pbuffer
	for (int i=1; i<poDS->nBands; i++) {
	    GDALRasterBand *b = poDS->GetRasterBand(i+1);
	    if (b->GetOverviewCount() && m_l)
		b = b->GetOverview(m_l -1);
	    GDALRasterBlock *poBlock = b->GetLockedBlockRef(xblk, yblk);
	    poBlock->DropLock();
	}
    }

    int boffset = (1==cstride)? 0:m_band;
    // If the stride is 1, offset is allways 0, also buffer is only valid once
    if (1 == cstride) {
	boffset = 0;
	poDS->tile=ILSize();
    }

    // Just the right mix of templates and macros make unpacking real tidy
#define CpySI(T) cpy_stride_in<T> (buffer,(T *)poDS->pbuffer + boffset, \
    blockSizeBytes()/sizeof(T),cstride)

    // Page is already in poDS->pbuffer, not empty
    switch (GDALGetDataTypeSize(eDataType)/8) {
    case 1: CpySI(GByte); break;
    case 2: CpySI(GInt16); break;
    case 4: CpySI(GInt32); break;
    case 8: CpySI(GIntBig); break;
    default:
	CPLError(CE_Failure,CPLE_AppDefined, "MRF: Datatype of size %d not implemented",
	    GDALGetDataTypeSize(eDataType)/8);
	return CE_Failure;
    }
    return CE_None;
}

// Write a tile at the end of the data file.
// If buff and size are zero, it is equivalent to erasing the info
// If only size is zero, it is a special empty tile, offset should be 1
CPLErr GDALMRFRasterBand::WriteTile(const ILSize &pos, void *buff=0, size_t size=0) 

{
    CPLErr ret=CE_None;
    ILIdx tinfo={0,0};
    VSILFILE *dfp=DataFP();
    VSILFILE *ifp=IdxFP();

    // This is the critical section for concurrent writes.
    // There is no file lock support in VSI
    if (size) {
	VSIFSeekL(dfp, 0, SEEK_END);
	tinfo.offset = net64(VSIFTellL(dfp));
	tinfo.size = net64(size);
	if (size != VSIFWriteL(buff, 1, size, dfp))
	    ret=CE_Failure;
    }

    // Special case
    // Any non-zero will do, use 1 to only consume one bit
    if ( 0 != buff && 0 == size)
	tinfo.offset = net64(GUIntBig(buff));

    VSIFSeekL(ifp, IdxOffset(pos, img), SEEK_SET);
    if (sizeof(tinfo) != VSIFWriteL(&tinfo, 1, sizeof(tinfo), ifp))
	ret=CE_Failure;
    // Flush if this is a caching MRF
    if (poDS->GetSrcDS()) {
	VSIFFlushL(dfp);
	VSIFFlushL(ifp);
    }
    return ret;
};


/**
*\brief Write a block from the provided buffer
* 
* Same trick as read, use a dataset buffer
* Write the block once it has all the bands, report 
* if a new block is started before the old one was completed
*
*/

CPLErr GDALMRFRasterBand::IWriteBlock(int xblk, int yblk, void *buffer)

{
    GInt32 cstride = img.pagesize.c;
    ILSize req(xblk, yblk, 0, m_band/cstride, m_l);
    CPLDebug("MRF_IB", "IWriteBlock %d,%d,0,%d, level  %d, stride %d\n", xblk, yblk, 
	m_band, m_l, cstride);

    // Separate bands, we can write it as is
    if (1 == cstride) {
	// Empty page skip. Byte data only, the NoData needs work
	if ((eDataType==GDT_Byte) && (poDS->vNoData.size())) {
	    if (is_empty((char *)buffer, img.pageSizeBytes, char(GetNoDataValue(0))))
		return WriteTile(req,0,0);
	} else if (is_zero((char *)buffer, img.pageSizeBytes)) // Don't write buffers with zero
	    return WriteTile(req,0,0);

	// Use the pbuffer to hold the compressed page before writing it
	poDS->tile = ILSize(); // Mark it corrupt

	buf_mgr src = {(char *)buffer, img.pageSizeBytes};
	buf_mgr dst = {(char *)poDS->pbuffer, poDS->pbsize};

	// Swab the source before encoding if we need to 
	if (is_Endianess_Dependent(img.dt, img.comp) && (img.nbo != NET_ORDER)) 
	    swab_buff(src, img);

	// Compress functions need to return the compresed size in
	// the bytes in buffer field
	Compress(dst, src, img);
	return WriteTile(req, poDS->pbuffer, dst.size);
    }

    // Multiple bands per page, we use the pbuffer to assemble the page
    poDS->tile=req; poDS->bdirty=0;

    // Get the other bands from the block cache
    for (int iBand=0; iBand < poDS->nBands; iBand++ )
    {
	const char *pabyThisImage=NULL;
	GDALRasterBlock *poBlock=NULL;

	if (iBand == m_band)
	{
	    pabyThisImage = (char *) buffer;
	    poDS->bdirty |= bandbit();
	} else {
	    GDALRasterBand *band = poDS->GetRasterBand(iBand +1);
	    // Pick the right overview
	    if (m_l) band = band->GetOverview(m_l -1);
	    poBlock = ((GDALMRFRasterBand *)band)
		->TryGetLockedBlockRef(xblk, yblk);
	    if (NULL==poBlock) continue;
	    // This should never happen, we can't have clean bands in this block
	    if (!poBlock->GetDirty())
	    {
		poBlock->DropLock();
		continue;
	    }

	    // This is where the image data is for this band
	    pabyThisImage = (char*) poBlock->GetDataRef();
	    poDS->bdirty|=bandbit(iBand);
	}

	// Copy the data into the dataset buffer here
	// Just the right mix of templates and macros make this real tidy
#define CpySO(T) cpy_stride_out<T> (((T *)poDS->pbuffer)+iBand, pabyThisImage,\
		blockSizeBytes()/sizeof(T), cstride)

	// Build the page in pbuffer
	switch (GDALGetDataTypeSize(eDataType)/8)
	{
	    case 1: CpySO(GByte); break;
	    case 2: CpySO(GInt16); break;
	    case 4: CpySO(GInt32); break;
	    case 8: CpySO(GIntBig); break;
	    default:
		CPLError(CE_Failure,CPLE_AppDefined, "MRF: Write datatype of %d bytes "
			"not implemented", GDALGetDataTypeSize(eDataType)/8);
		return CE_Failure;
	}
#undef CpySO

	if (poBlock != NULL)
	{
	    poBlock->MarkClean();
	    poBlock->DropLock();
	}
    }

    // Gets written on flush
    if (poDS->bdirty != AllBandMask())
	CPLError(CE_Warning, CPLE_AppDefined,
	"MRF: IWrite, band dirty mask is %0llx instead of %lld",
	poDS->bdirty, AllBandMask());

    //    ppmWrite("test.ppm",(char *)poDS->pbuffer,ILSize(nBlockXSize,nBlockYSize,0,poDS->nBands));

    // Skip writing if the tile is nodata or if it is zeros
    if ((eDataType == GDT_Byte) && poDS->vNoData.size()) {
	if (is_empty((char *)poDS->pbuffer, img.pageSizeBytes, (char)GetNoDataValue(0))) {
	    poDS->bdirty=0;
	    return WriteTile(req, 0, 0);
	}
    } else if (is_zero((char *)poDS->pbuffer, img.pageSizeBytes)) {
	poDS->bdirty = 0;
	return WriteTile(req, 0, 0);
    }

    buf_mgr src={(char *)poDS->pbuffer, img.pageSizeBytes};

    // Have to use a separate buffer.  We should make this one permanent too.
    void *outbuff = CPLMalloc(poDS->pbsize);

    if (!outbuff) {
	CPLError(CE_Failure, CPLE_AppDefined, 
	    "Can't get buffer for writing page");
	return CE_Failure;
    }

    buf_mgr dst={(char *)outbuff, poDS->pbsize};
    Compress(dst, src, img);

    CPLErr ret = WriteTile(req, outbuff, dst.size);
    CPLFree(outbuff);

    poDS->bdirty = 0;
    return ret;
}

/**
*\brief Read a tile index, convert it to the host endianess
*
*
*/

CPLErr GDALMRFRasterBand::ReadTileIdx(const ILSize &pos,ILIdx &tinfo) 

{
    VSILFILE *ifp = IdxFP();
    GIntBig offset = IdxOffset(pos, img);
    VSIFSeekL(ifp, offset, SEEK_SET);
    if (1 != VSIFReadL(&tinfo, sizeof(ILIdx), 1, ifp))
	return CE_Failure;
    tinfo.offset=net64(tinfo.offset);
    tinfo.size=net64(tinfo.size);
    return CE_None;
}

