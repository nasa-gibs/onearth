
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
 * Author:   Lucian Plesea, Lucian.Plesea@jpl.nasa.gov
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

// Swap bytes in place, unconditional

static void swab_buff(buf_mgr &src, const ILImage &img) {
    switch (GDALGetDataTypeSize(img.dt)/8) {
    case 2: {
        short int *b=(short int*)src.buffer;
        for (int i=src.size/2;i;b++,i--) 
            *b=swab16(*b);
        break;
            };
    case 4: {
        int *b=(int*)src.buffer;
        for (int i=src.size/4;i;b++,i--) 
            *b=swab32(*b);
        break;
            };
    case 8: {
        long long *b=(long long*)src.buffer;
        for (int i=src.size/8;i;b++,i--)
            *b=swab64(*b);
        break;
            };
    }
}

GDALMRFRasterBand::GDALMRFRasterBand(GDALMRFDataset *parent_dataset, const ILImage &image,
                                    int band,int ov)

{
    poDS=parent_dataset;
    m_band=band-1;
    m_l=ov;
    img=image;
    eDataType=parent_dataset->current.dt;
    nRasterXSize=img.size.x;
    nRasterYSize=img.size.y;
    nBlockXSize=img.pagesize.x;
    nBlockYSize=img.pagesize.y;
    dfp=ifp=0;
}

// Clean up the overviews if they exist
GDALMRFRasterBand::~GDALMRFRasterBand() {
    while (0!=overviews.size()) {
        delete overviews[overviews.size()-1];
        overviews.pop_back();
    };
    if (NULL!=ifp) VSIFCloseL(ifp);
    if (NULL!=dfp) VSIFCloseL(dfp);
}

/************************************************************************/
/*                       GetColorInterpretation()                       */
/************************************************************************/

GDALColorInterp GDALMRFRasterBand::GetColorInterpretation()

{
    if (poDS->GetColorTable()) return GCI_PaletteIndex;
    return BandInterp(poDS->nBands,m_band+1);
}

// Utility function, returns a value from a vector corresponding to the band index
// or the first entry
static double getBandValue(std::vector<double> &v,int idx) {
    idx--;
    if (static_cast<int>(v.size())>idx) return v[idx];
    return v[0];
}

double GDALMRFRasterBand::GetNoDataValue( int *pbSuccess) {
    std::vector<double> &v=poDS->vNoData;
    if (v.size()==0)
        return GDALPamRasterBand::GetNoDataValue(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v,nBand);
}

double GDALMRFRasterBand::GetMinimum( int *pbSuccess) {
    std::vector<double> &v=poDS->vMin;
    if (v.size()==0)
        return GDALPamRasterBand::GetMinimum(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v,nBand);
}

double GDALMRFRasterBand::GetMaximum( int *pbSuccess) {
    std::vector<double> &v=poDS->vMax;
    if (v.size()==0)
        return GDALPamRasterBand::GetMaximum(pbSuccess);
    if (pbSuccess) *pbSuccess=TRUE;
    return getBandValue(v,nBand);
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

    // std::cerr << "Iread " << xblk << "," << yblk << " band " << m_band << " lev " << m_l << " IOffset " << IdxOffset(req,img) ;
    // std::cerr << " Offset " << img.idxoffset << " Pcount " << img.pcount.l << std::endl;
    CPLDebug("MRF","IReadBlock %d,%d,1,%d, level  %d\n",xblk,yblk,m_band,m_l);
    // std::cerr << "Blocks " << nBlocksPerRow << "," << nBlocksPerColumn << std::endl;

    // Size of the buffer is the size of page for a single band, single slice
    // Ignore the c, it could be different if order is separate
    if ((cstride==1)||(req.x!=poDS->tile.x || req.y!=poDS->tile.y || 
        req.z!=poDS->tile.z || req.l!=poDS->tile.l))
    { 
        // Need to read the page, in poDS->pbuffer
        // This is a new or empty tile
        if (CE_None!=ReadTileIdx(req,tinfo)) {
            CPLError( CE_Failure, CPLE_AppDefined, "Unable to read index at offset "
                "%lld", IdxOffset(req,img));
            return CE_Failure;
        }
        if (0==tinfo.size) { // empty page, just generate minfill
            // since the pmDS->tile hasn't changed, each empty band will
            // just read the tile info and return
            if ((eDataType==GDT_Byte) && poDS->vNoData.size())
                memset(buffer,(char) GetNoDataValue(0),blockSizeBytes());
            else
                memset(buffer,0,blockSizeBytes());
            return CE_None;
        }
        void *data=CPLMalloc(tinfo.size);
        VSIFSeekL(dfp,tinfo.offset,SEEK_SET);
        if (1!=VSIFReadL(data,tinfo.size,1,dfp)) {
            CPLFree(data);
            CPLError( CE_Failure, CPLE_AppDefined, "Unable to read data page, %lld@%lld",
                tinfo.size,tinfo.offset);
            return CE_Failure;
        }
        // We got the data, mark the buffer as invalid for now
        if (1!=cstride) poDS->tile=ILSize();
        CPLErr ret;

        buf_mgr src={(char *)data,tinfo.size};
        buf_mgr dst={(char *)poDS->pbuffer,img.pageSizeBytes};
        // If pages are separate, uncompress directly in output buffer
        if (1==cstride) dst.buffer=(char *)buffer;
        // Capture the dest buffer for potential swapping
        buf_mgr sbuf=dst;
        ret=Decompress(dst,src);

        // Swap whatever we decompressed if we need to
        if (is_Endianess_Dependent(img.dt,img.comp)&&(img.nbo!=NET_ORDER)) 
            swab_buff(sbuf,img);

        CPLFree(data);
        if (CE_None!=ret) return ret;

        // If pages are separate, we're done, the read was in the output buffer
        if (1==cstride) return CE_None;

        // Got the page correctly, so let the other bands know
        poDS->tile=req;

        // Force load of the other bands only if the order is interleaved,
        // they are already unpacked in the DS pbuffer
        for (int i=1;i<poDS->nBands;i++) {
            GDALRasterBand *b=poDS->GetRasterBand(i+1);
            if (b->GetOverviewCount()&&m_l)
          b=b->GetOverview(m_l-1);
            GDALRasterBlock *poBlock=b->GetLockedBlockRef(xblk,yblk);
            poBlock->DropLock();
        }
    }


// Just the right mix of templates and macros make this real tidy
#define CpySI(T) cpy_stride_in<T> (buffer,(T *)poDS->pbuffer+m_band, \
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

inline static int is_zero(char *b,size_t count)
{
    while (count--) if (*b++) return 0;
    return TRUE;
}

inline static int is_empty(char *b,size_t count, char val=0)

{
    while (count--) if (*(b++)!=val) return 0;
    return TRUE;
}

// Write a tile.  When size is zero the buffer is ignored
CPLErr GDALMRFRasterBand::WriteTile(const ILSize &pos, void *buff=0, size_t size=0) 

{
    CPLErr ret=CE_None;
    ILIdx tinfo={0,0};
    VSILFILE *dfp=DataFP();
    VSILFILE *ifp=IdxFP();

    if (size) {
        VSIFSeekL(dfp,0,SEEK_END);
        tinfo.offset=net64(VSIFTellL(dfp));
        tinfo.size=net64(size);
        if (size!=VSIFWriteL(buff,1,size,dfp))
            ret=CE_Failure;
    }

    VSIFSeekL(ifp,IdxOffset(pos,img),SEEK_SET);
    if (sizeof(tinfo)!=VSIFWriteL(&tinfo,1,sizeof(tinfo),ifp))
        ret=CE_Failure;
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
    // std::cerr << "Iwrite " << xblk << "," << yblk << " band " << m_band << " level " << m_l << std::endl;

    CPLDebug("MRF","IWriteBlock %d,%d,1,%d, level  %d\n",xblk,yblk,m_band,m_l);
    GInt32 cstride=img.pagesize.c;
    ILSize req(xblk,yblk,0,m_band/cstride,m_l);

    // std::cerr << "IW Block " << req << std::endl;

    // Separate bands, we can write it as is
    if (1==cstride) {

        // Empty page skip. Byte data only, the NoData needs improvements
        if ((eDataType==GDT_Byte) && (poDS->vNoData.size())) {
            if (is_empty((char *)buffer, img.pageSizeBytes, (char)GetNoDataValue(0)))
            return WriteTile(req,0,0);
        } else if (is_zero((char *)buffer,img.pageSizeBytes))
            return WriteTile(req,0,0);

        // Use the pbuffer to hold the compressed page before writing it
        poDS->tile=ILSize(); // Mark it corrupt

        buf_mgr src={(char *)buffer,img.pageSizeBytes};
        buf_mgr dst={(char *)poDS->pbuffer,img.pageSizeBytes};

        // Swab the source before encoding if we need to 
        if (is_Endianess_Dependent(img.dt,img.comp)&&(img.nbo!=NET_ORDER)) 
            swab_buff(src,img);

        // Compress functions need to return the compresed size in
        // the bytes in buffer field
        Compress(dst,src,img);
        return WriteTile(req,poDS->pbuffer,dst.size);
    }

    // Multiple bands per page
    poDS->tile=req; poDS->bdirty=0;

    // Get the other bands from the block cache
    for (int iBand=0; iBand < poDS->nBands; iBand++ )
    {
        const char *pabyThisImage=NULL;
        GDALRasterBlock *poBlock=NULL;

        if (iBand==m_band)
        {
            pabyThisImage=(char *) buffer;
            poDS->bdirty|=bandbit();
        } else {
            GDALRasterBand *band=poDS->GetRasterBand(iBand+1);
            // Writing to an overview
            if (m_l) 
                band=band->GetOverview(m_l-1);
            poBlock=((GDALMRFRasterBand *)band)
                ->TryGetLockedBlockRef(xblk,yblk);
            if (NULL==poBlock) continue;

            if (!poBlock->GetDirty()) {
                poBlock->DropLock();
                continue;
            }

            pabyThisImage = (char*) poBlock->GetDataRef();
            poDS->bdirty|=bandbit(iBand);
        }

        // Copy the data into the dataset buffer here
        // Just the right mix of templates and macros make this real tidy

#define CpySO(T) cpy_stride_out<T> (((T *)poDS->pbuffer)+iBand, pabyThisImage,\
    blockSizeBytes()/sizeof(T),cstride)

        // Build the page in pbuffer
        switch (GDALGetDataTypeSize(eDataType)/8) {
        case 1: CpySO(GByte); break;
        case 2: CpySO(GInt16); break;
        case 4: CpySO(GInt32); break;
        case 8: CpySO(GIntBig); break;
        default:
            CPLError(CE_Failure,CPLE_AppDefined, "MRF: Write datatype of %d bytes "
                "not implemented", GDALGetDataTypeSize(eDataType)/8);
            return CE_Failure;
        }

        if (poBlock != NULL)
        {
            poBlock->MarkClean();
            poBlock->DropLock();
        }
    }
    
    // Gets written on flush?
    if (poDS->bdirty!=AllBandMask())
        CPLError(CE_Warning,CPLE_AppDefined,
            "MRF: IWrite, band dirty mask is %0llx instead of %lld",
            poDS->bdirty, AllBandMask());

    CPLErr ret;

    // Skip writing if the tile is nodata or if it is zeros
    if ((eDataType==GDT_Byte) && poDS->vNoData.size()) {
        if (is_empty((char *)poDS->pbuffer, img.pageSizeBytes, (char)GetNoDataValue(0))) {
            poDS->bdirty=0;
            return WriteTile(req,0,0);
        }
    } else if (is_zero((char *)poDS->pbuffer,img.pageSizeBytes)) {
        poDS->bdirty=0;
        return WriteTile(req,0,0);
    }

    void *outbuff=CPLMalloc(img.pageSizeBytes);

    if (!outbuff) {
        CPLError(CE_Failure, CPLE_AppDefined, 
            "Can't get buffer for writing page");
        return CE_Failure;
    }

    buf_mgr src={(char *)poDS->pbuffer,img.pageSizeBytes};
    buf_mgr dst={(char *)outbuff,img.pageSizeBytes};

    Compress(dst,src,img);
    ret= WriteTile(req,outbuff,dst.size);
    CPLFree(outbuff);

    poDS->bdirty=0;

    return ret;
}

/**
 *\brief Read a tile index, convert it to the host endianess
 *
 *
 */

CPLErr GDALMRFRasterBand::ReadTileIdx(const ILSize &pos,ILIdx &tinfo) 

{
    VSILFILE *ifp=IdxFP();
    GIntBig offset=IdxOffset(pos,img);
    VSIFSeekL(ifp,offset,SEEK_SET);
    if (1!=VSIFReadL(&tinfo,sizeof(ILIdx),1,ifp))
        return CE_Failure;
    tinfo.offset=net64(tinfo.offset);
    tinfo.size=net64(tinfo.size);
    return CE_None;
}

