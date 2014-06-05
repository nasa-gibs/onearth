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
* Project:  Meta Raster File Format Driver Implementation, Dataset
* Purpose:  Implementation of GDAL dataset
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

#include <vector>

using std::vector;
using std::string;

// Returns the size of the index for image and overlays
// If scale is zero, only base image
GIntBig IdxSize(const ILImage &full, const int scale=0) {
    ILImage img=full;
    pcount(img.pcount,img.size,img.pagesize);
    GIntBig sz = img.pcount.l;
    while ( scale != 0 && 1 != img.pcount.x * img.pcount.y )
    {
	img.size.x = pcount(img.size.x, scale);
	img.size.y = pcount(img.size.y, scale);
	img.size.l++;
	pcount(img.pcount, img.size, img.pagesize);
	sz += img.pcount.l;
    }
    return sz*sizeof(ILIdx);
}

GDALMRFDataset::GDALMRFDataset()

{
    ifp.FP = dfp.FP = 0;
    pbuffer=0;
    pbsize=0;
    bdirty=0;
    level=-1;
    GeoTransform[0]=0.0; // X Origin, left of top-left pixel
    GeoTransform[1]=1.0; // X Pixel size
    GeoTransform[2]=0.0; // X-Y skew
    GeoTransform[3]=0.0; // Y Origin, top of top-left pixel
    GeoTransform[4]=0.0; // Y-X skew
    GeoTransform[5]=1.0; // Y Pixel size

    bGeoTransformValid=FALSE;
    optlist=0;
    cds=0;
    poSrcDS=NULL;
    pszProjection=0;
    poColorTable=0;
    tile=ILSize();
}

void GDALMRFDataset::SetPBuffer(unsigned int sz)
{
    //	fprintf(stderr, "Old size is %d %x, new is %d\n", pbsize, pbuffer, sz);
    pbuffer = CPLRealloc(pbuffer, sz);
    pbsize = (pbuffer == 0) ? 0:sz;
    //	fprintf(stderr, "After size is %d\n", pbsize);
}

GDALMRFDataset::~GDALMRFDataset()

{
    // Make sure everything gets written
    FlushCache();
    if (ifp.FP)
	VSIFCloseL(ifp.FP);
    if (dfp.FP)
	VSIFCloseL(dfp.FP);
    if (cds)
	delete cds;
    if (poSrcDS)
	delete poSrcDS;
    // OK to pass null
    CSLDestroy(optlist);
    // CPLFree ignores being called with NULL, so these are safe
    CPLFree(pbuffer);
    CPLFree(pszProjection);
    pbsize=0;
    if (poColorTable)
	delete poColorTable;
}


/*
*\brief Convert a projection code to WKT
*  Copied from wms/stuff.cpp
*
*/

static CPLString ProjToWKT(const CPLString &proj) {
    char* wkt = NULL;
    OGRSpatialReference sr;
    CPLString srs;

    if (sr.SetFromUserInput(proj.c_str()) != OGRERR_NONE) return srs;
    sr.exportToWkt(&wkt);
    srs = wkt;
    OGRFree(wkt);
    return srs;
}

/**
*\brief Erase the Overviews
*
* TBD
*/

CPLErr GDALMRFDataset::CleanOverviews() 
{
    return CE_None;
}


/*
 *\brief Called before the IRaster IO gets called
 *
 *
 *
 */
CPLErr GDALMRFDataset::AdviseRead( int nXOff, int nYOff, int nXSize, int nYSize,
			  int nBufXSize, int nBufYSize, 
			  GDALDataType eDT, 
			  int nBandCount, int *panBandList,
			  char **papszOptions )
{
    CPLDebug("MRF_IO", "AdviseRead %d, %d, %d, %d, bufsz %d,%d,%d\n",
	nXOff, nYOff, nXSize, nYSize, nBufXSize, nBufYSize, nBandCount);
    return CE_None;
}

/*
 *\brief Format specifc RasterIO, may be bypassed by BlockBasedRasterIO by setting
 * GDAL_FORCE_CACHING to Yes, in which case the band ReadBlock and WriteBLock are called
 * directly
 *
 *
 */
CPLErr GDALMRFDataset::IRasterIO( GDALRWFlag eRWFlag, int nXOff, int nYOff, int nXSize, int nYSize,
                       void *pData, int nBufXSize, int nBufYSize, GDALDataType eBufType,
                       int nBandCount, int *panBandMap,
                       int nPixelSpace, int nLineSpace, int nBandSpace)
{
    CPLDebug("MRF_IO", "IRasterIO %s, %d, %d, %d, %d, bufsz %d,%d,%d strides P %d, L %d, B %d \n",
	eRWFlag == GF_Write ? "Write":"Read",
	nXOff, nYOff, nXSize, nYSize, nBufXSize, nBufYSize, nBandCount, 
	nPixelSpace, nLineSpace, nBandSpace);

    //
    // Call the parent implementation, which splits it into bands and calls their IRasterIO
    // 
    return GDALPamDataset::IRasterIO(eRWFlag, nXOff, nYOff, nXSize, nYSize, pData, nBufXSize, nBufYSize,
	eBufType, nBandCount, panBandMap, nPixelSpace, nLineSpace, nBandSpace);
}


/**
*\brief Build some overviews
*
*  if nOverviews is 0, erase the overviews (reduce to base image only)
*/

CPLErr GDALMRFDataset::IBuildOverviews( 
    const char * pszResampling, 
    int nOverviews, int * panOverviewList,
    int nBands, int * panBandList,
    GDALProgressFunc pfnProgress, void * pProgressData )

{
    CPLErr       eErr = CE_None;

    CPLDebug("MRF_OVERLAY", "IBuildOverviews %d, bands %d\n", nOverviews, nBands);

    /* -------------------------------------------------------------------- */
    /*      If we don't have read access, then create the overviews         */
    /*      externally.                                                     */
    /*      Copied from the GTIFF driver, but doesn't work, just prints a   */
    /*      "not supported" message                                         */
    /*      Don't really know how to use the overview system                */
    /*                                                                      */
    /* -------------------------------------------------------------------- */
    if( GetAccess() != GA_Update )
    {
	CPLDebug( "MRF", "File open read-only, creating overviews externally." );

	return GDALDataset::IBuildOverviews( 
	    pszResampling, nOverviews, panOverviewList, 
	    nBands, panBandList, pfnProgress, pProgressData );
    }

    /* -------------------------------------------------------------------- */
    /*      If zero overviews were requested, we need to clear all          */
    /*      existing overviews.                                             */
    /*      This should just clear the index file                           */
    /*      Right now it just fails or does nothing                         */
    /* -------------------------------------------------------------------- */

    if( nOverviews == 0 )
    {
	if( current.size.l == 0 )
	    return GDALDataset::IBuildOverviews( 
	    pszResampling, nOverviews, panOverviewList, 
	    nBands, panBandList, pfnProgress, pProgressData );
	else
	    return CleanOverviews();
    }

    CPLXMLNode *config = ReadConfig();
    GDALRasterBand ***papapoOverviewBands=NULL;
    GDALRasterBand  **papoOverviewBandList=NULL;
    GDALRasterBand  **papoBandList=NULL;

    try {  // Throw an error code, to make sure memory gets freed properly
	const char* model = CPLGetXMLValue(config, "Rsets.model", "uniform");
	double scale;
	int uniform = EQUAL(model,"uniform");

	if (uniform) { // Indexes go at predefined offsets and only "factor" scales are allowed
	    scale=strtod(CPLGetXMLValue(config, "Rsets.scale", "2"), 0);

	    // Initialize the empty overlays, all of them for a given scale
	    // They could already exist, in which case they are not erased
	    GIntBig idxsize = AddOverviews(int(scale));
	    if (!CheckFileSize(current.idxfname, idxsize, GA_Update)) {
		CPLError(CE_Failure,CPLE_AppDefined,"MRF: Can't extend index file");
		return CE_Failure;
	    }

	    //  Set the uniform node, in case it was not set before, and save the new configuration
	    CPLSetXMLValue(config, "Rsets.#model", "uniform");
	    CPLSetXMLValue(config, "Rsets.#scale", CPLString().Printf("%g",scale).c_str());
	    if (!CPLSerializeXMLTreeToFile(config,fname)) {
		CPLError(CE_Failure,CPLE_AppDefined,"MRF: Can't rewrite the metadata file");
		return CE_Failure;
	    }

	    CPLDestroyXMLNode(config);
	    config = 0;

	} else { // This is a per-dataset Rset, just append it to the existing file
	    // For now, just throw an error
	    CPLError(CE_Failure,CPLE_AppDefined,
		"MRF:IBuildOverviews, Overviews not implemented for model %s", model);
	    throw CE_Failure;
	}

	// Generate the overview, using PatchOverview.  One overlay at the time, 
	// using the previous level as the source.
	for (int i=0; i < nOverviews ; i++) {
	    // Verify that scales are reasonable, val/scale has to be an integer
	    if (!IsPower(panOverviewList[i], scale)) {
		CPLError(CE_Warning,CPLE_AppDefined,
		    "MRF:IBuildOverviews, overview factor %d is not a power of %f",
		    panOverviewList[i], scale);
		continue;
	    };

	    int srclevel = -0.5 + logb(panOverviewList[i], scale);
	    GDALMRFRasterBand *b = static_cast<GDALMRFRasterBand *>(GetRasterBand(1));

	    // Warn and ignore requests for invalid levels
	    if (srclevel >= b->GetOverviewCount()) {
		CPLError(CE_Warning,CPLE_AppDefined,
		    "MRF:IBuildOverviews, overview factor %d is not valid for this dataset",
		    panOverviewList[i]);
		continue;
	    }

	    if (srclevel >0)
		b = static_cast<GDALMRFRasterBand *>(b->GetOverview(srclevel-1));

	    eErr = PatchOverview(0, 0, b->nBlocksPerRow, b->nBlocksPerColumn, srclevel, 0);
	    if (eErr == CE_Failure)
		throw eErr;
	}

    } catch (CPLErr e) {
	eErr=e;
    }
    if (config)
	CPLDestroyXMLNode(config);
    return eErr;
}

/*
*\brief blank separated list to vector of doubles
*/
static void list2vec(std::vector<double> &v,const char *pszList) {
    if ((pszList==NULL)||(pszList[0]==0)) return;
    char **papszTokens=CSLTokenizeString2(pszList," \t\n\r",
	CSLT_STRIPLEADSPACES|CSLT_STRIPENDSPACES);
    v.clear();
    for (int i=0;i<CSLCount(papszTokens);i++)
	v.push_back(CPLStrtod(papszTokens[i],NULL));
    CSLDestroy(papszTokens);
}

void GDALMRFDataset::SetNoDataValue(const char *pszVal) {
    list2vec(vNoData,pszVal);
}

void GDALMRFDataset::SetMinValue(const char *pszVal) {
    list2vec(vMin,pszVal);
}

void GDALMRFDataset::SetMaxValue(const char *pszVal) {
    list2vec(vMax,pszVal);
}

/**
*\brief Idenfity a MRF file, lightweight
*
* Lightweight test, otherwise Open gets called.
* It should make sure all three files exist
*
*/
int GDALMRFDataset::Identify(GDALOpenInfo *poOpenInfo)

{
    if ((poOpenInfo->nHeaderBytes == 0) &&
	EQUALN((const char *) poOpenInfo->pszFilename,"<MRF_META>", 10))
	return TRUE;
    if ((poOpenInfo->nHeaderBytes >= 10) &&
	EQUALN((const char *) poOpenInfo->pabyHeader, "<MRF_META>", 10))
	return TRUE;
    if (poOpenInfo->nHeaderBytes == 0 &&
	EQUALN(poOpenInfo->pszFilename, "MRF:", 4))
	return TRUE;
    return FALSE;
}


/**
*
*\Brief Read the XML config tree, from file
*  Caller is responsible for freeing the memory
*
* @param pszFilename the file to open.
* @return NULL on failure, or the document tree on success.
*
*/
CPLXMLNode *GDALMRFDataset::ReadConfig()
{
    return CPLParseXMLFile(fname);
}

/**
*\Brief Write the XML config tree
* Caller is responsible for correctness of data
* and for freeing the memory
*
* @param config The document tree to write 
* @return TRUE on success, FALSE otherwise
*/
int GDALMRFDataset::WriteConfig(CPLXMLNode *config)
{
    return CPLSerializeXMLTreeToFile(config,fname);
}

/**
*\Brief Open a MRF file
*
*/
GDALDataset *GDALMRFDataset::Open(GDALOpenInfo *poOpenInfo)

{
    CPLXMLNode *config = NULL;
    CPLErr ret = CE_None;
    const char* pszFileName=poOpenInfo->pszFilename;
    int level=-1;

    // Test that this is a MRF file
    // Allow for the whole metadata to be passed as the filename
    if ((poOpenInfo->nHeaderBytes == 0) &&
	EQUALN(pszFileName,"<MRF_META>", 10))
	config = CPLParseXMLString(pszFileName);
    else if ((poOpenInfo->nHeaderBytes >= 10) &&
	EQUALN((const char *) poOpenInfo->pabyHeader, "<MRF_META>", 10)) 
	config = CPLParseXMLFile(pszFileName);
    else if ((poOpenInfo->nHeaderBytes == 0) && EQUALN(pszFileName,"MRF:",4)) {
	pszFileName+=4;
	if (!isdigit(*pszFileName)) {
	    CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Use MRF:<num>:filename");
	    return NULL;
	} else level=atoi(pszFileName);
	pszFileName=strstr(pszFileName,":")+1;
	if (!pszFileName) {
	    CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Use MRF:<num>:filename");
	    return NULL;
	}
	config = CPLParseXMLFile(pszFileName);
    }
    else
	return NULL;

    if (config == NULL)
	return NULL;

    GDALMRFDataset *ds = new GDALMRFDataset();
    ds->fname=pszFileName;
    ds->eAccess=poOpenInfo->eAccess;
    ds->level=level;

    if (level != -1) {
	ds->cds = new GDALMRFDataset();
	ds->cds->fname = pszFileName;
	ds->cds->eAccess = ds->eAccess;
	ret = ds->cds->Initialize(config);
	if (ret==CE_None)
	    ret = ds->LevelInit(level);
    }
    else
	ret = ds->Initialize(config);
    CPLDestroyXMLNode(config);

    if (ret!=CE_None) {
	delete ds;
	return NULL;
    }

    // If not set by the band, get a pageSizeBytes buffer
    if ( ds->GetPBufferSize() == 0 )
	ds->SetPBuffer(ds->current.pageSizeBytes);

    // Tell PAM what our real file name is, and load it if there
    ds->SetPhysicalFilename(pszFileName);
    ds->TryLoadXML();

    // This is after PAM, because it ignores what we set?
    ds->SetMetadataItem("INTERLEAVE", OrderName(ds->full.order), "IMAGE_STRUCTURE");

    return ds;
}

CPLErr GDALMRFDataset::LevelInit(const int l) {

    if (l<0 || l>cds->GetRasterBand(1)->GetOverviewCount()) {
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: No such level found!");
	return CE_Failure;
    }
    GDALMRFRasterBand *srcband=(GDALMRFRasterBand *)cds->GetRasterBand(1)->GetOverview(l);
    // Copy the sizes from this level
    current=full=srcband->img;
    current.size.c=cds->current.size.c;
    scale=cds->scale;
    SetProjection(cds->GetProjectionRef());

    SetMetadataItem("INTERLEAVE",OrderName(current.order),"IMAGE_STRUCTURE");
    SetMetadataItem("COMPRESS",CompName(current.comp),"IMAGE_STRUCTURE");

    for (int i=0;i<6;i++)
	GeoTransform[i]=cds->GeoTransform[i];
    for (int i=0;i<l;i++) {
	GeoTransform[1]/=scale;
	GeoTransform[5]/=scale;
    }

    nRasterXSize=current.size.x;
    nRasterYSize=current.size.y;
    nBands=current.size.c;

    bGeoTransformValid=TRUE;

    // Add the bands
    for (int i=1;i<=nBands;i++) {
	GDALMRFLRasterBand *band=new GDALMRFLRasterBand((GDALMRFRasterBand *)
	    cds->GetRasterBand(i)->GetOverview(l));

	SetBand(i,band);
	band->SetColorInterpretation(BandInterp(nBands,i));
    }

    return CE_None;
}

// Is the string positive or not
inline bool on(const char *pszValue) {
    if ( !pszValue || pszValue[0] == 0)
	return false;
    return (EQUAL(pszValue, "ON") || EQUAL(pszValue, "TRUE") || EQUAL(pszValue, "YES"));
}

/**
*\brief Initialize the image structure 
* 
* @param image, the structure to be initialized
* @param config, the Raster node of the xml structure
* @param ds, the parent dataset, some things get inherited
*
* The structure should be initialized with the default values as much as possible
*
*/

static CPLErr Init_ILImage(ILImage &image, CPLXMLNode *config, GDALMRFDataset *ds)
{
    CPLXMLNode *node; // temporary
    CPLXMLNode *defimage=CPLGetXMLNode(config,"Raster");
    if (!defimage) {
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Can't find raster info");
	return CE_Failure;
    }

    // Size is mandatory
    node=CPLGetXMLNode(defimage,"Size");
    if (!node) {
	CPLError(CE_Failure, CPLE_AppDefined, "No size defined");
	return CE_Failure;
    }

    image.size=ILSize(
	static_cast<int>(getXMLNum(node,"x",-1)),
	static_cast<int>(getXMLNum(node,"y",-1)),
	static_cast<int>(getXMLNum(node,"NumImgs",1)),
	static_cast<int>(getXMLNum(node,"c",1)),
	0);
    // Basic checks
    if (image.size.x<1||image.size.y<1) {
	CPLError(CE_Failure, CPLE_AppDefined, "Need at least x,y size");
	return CE_Failure;
    }

    //  Pagesize, defaults to 512,512,z,c
    image.pagesize=ILSize(
	MIN(512,image.size.x),
	MIN(512,image.size.y),
	1,
	image.size.c,
	1);

    node=CPLGetXMLNode(defimage,"PageSize");
    if (node) image.pagesize=ILSize(
	static_cast<int>(getXMLNum(node,"x",image.pagesize.x)),
	static_cast<int>(getXMLNum(node,"y",image.pagesize.y)),
	static_cast<int>(getXMLNum(node,"z",image.pagesize.z)),
	static_cast<int>(getXMLNum(node,"c",image.pagesize.c)),
	1);

    // Orientation
    if (!EQUAL(CPLGetXMLValue(defimage,"Orientation","TL"),"TL")) {
	// GDAL only handles Top Left Images
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Only Top-Left orientation is supported");
	return CE_Failure;
    }

    // Page Encoding, defaults to PNG
    image.comp = CompToken(CPLGetXMLValue(defimage,"Compression","PNG"));

    if (image.comp==IL_ERR_COMP) {
	CPLError(CE_Failure, CPLE_AppDefined, 
	    "GDAL MRF: Compression %s is unknown",
	    CPLGetXMLValue(defimage,"Compression",NULL));
	return CE_Failure;
    }

    // Is there a palette?
    //
    // GDAL only supports RGB+A palette, the other modes don't work
    //
    // Format is
    // <Palette>
    //   <Size>N</Size> : Optional
    //   <Model>RGBA|RGB|CMYK|HSV|HLS|L</Model> :mandatory
    //   <Entry idx=i c1=v1 c2=v2 c3=v3 c4=v4/> :Optional
    //   <Entry .../>
    // </Palette>
    // the idx attribute is optional, it autoincrements
    // The entries are actually vertices, interpolation takes place inside
    // The palette starts initialized with zeros
    // HSV and HLS are the similar, with c2 and c3 swapped
    // RGB or RGBA are same
    // 

    if ((image.pagesize.c==1)&&(node=CPLGetXMLNode(defimage,"Palette"))) {
	int entries=static_cast<int>(getXMLNum(node,"Size",255));
	GDALPaletteInterp eInterp=GPI_RGB;
	// A flag to convert from HLS to HSV
	bool is_hsv=false;
	CPLString pModel=CPLGetXMLValue(node,"Model","RGB");
	if (!pModel.empty()) {
	    if (pModel.find("HSV")!=string::npos) {
		eInterp=GPI_HLS;
		is_hsv=true;
	    } else if (pModel.find("HLS")!=string::npos)
		eInterp=GPI_HLS;
	    else if (pModel.find("CMYK")!=string::npos) eInterp=GPI_CMYK;
	    // Can it do LuminanceAlpha?
	    else if (pModel.find("L")!=string::npos) eInterp=GPI_Gray;
	    // RGBA and RGB are the same
	    else if (pModel.find("RGB")!=string::npos) eInterp=GPI_RGB;
	    else {
		CPLError(CE_Failure, CPLE_AppDefined,
		    "GDAL MRF: Palette Model %s is unknown, use RGB,RGBA,HSV,HLS,CMYK or L",
		    pModel.c_str());
		return CE_Failure;
	    }
	}

	if ((entries>0)&&(entries<257)) {
	    int start_idx, end_idx;
	    GDALColorEntry ce_start={0,0,0,255},ce_end={0,0,0,255};

	    // Create it and initialize it to nothing
	    GDALColorTable *poColorTable = new GDALColorTable(eInterp);
	    poColorTable->CreateColorRamp(0,&ce_start,entries-1,&ce_end);
	    // Read the values
	    CPLXMLNode *p=CPLGetXMLNode(node,"Entry");
	    if (p) {
		// Initialize the first entry, just in case
		ce_start=GetXMLColorEntry(p);
		if (is_hsv) ce_start=HSVSwap(ce_start);
		start_idx=static_cast<int>(getXMLNum(p,"idx",0));
		if (start_idx<0) {
		    CPLError(CE_Failure, CPLE_AppDefined,
			"GDAL MRF: Palette index %d not allowed",start_idx);
		    delete poColorTable;
		    return CE_Failure;
		}
		poColorTable->SetColorEntry(start_idx,&ce_start);
		while (NULL!=(p=SearchXMLSiblings(p,"Entry"))) {
		    // For every entry, create a ramp
		    ce_end=GetXMLColorEntry(p);
		    if (is_hsv) ce_end=HSVSwap(ce_end);
		    end_idx=static_cast<int>(getXMLNum(p, "idx", start_idx+1));
		    if ((end_idx<=start_idx)||(start_idx>=entries)) {
			CPLError(CE_Failure, CPLE_AppDefined,
			    "GDAL MRF: Index Error at index %d",end_idx);
			delete poColorTable;
			return CE_Failure;
		    }
		    poColorTable->CreateColorRamp(start_idx,&ce_start,
			end_idx,&ce_end);
		    ce_start=ce_end;
		    start_idx=end_idx;
		}
	    }

	    ds->SetColorTable(poColorTable);
	} else {
	    CPLError(CE_Failure, CPLE_AppDefined,"GDAL MRF: Palette definition error");
	    return CE_Failure;
	}
    }

    // Order of increment
    image.order = OrderToken(CPLGetXMLValue(defimage, "Order",
	(image.pagesize.c != image.size.c)? "BAND" : "PIXEL"));
    if (image.order==IL_ERR_ORD) {
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Order %s is unknown",
	    CPLGetXMLValue(defimage,"Order",NULL));
	return CE_Failure;
    }

    image.quality=atoi(CPLGetXMLValue(defimage,"Quality","85"));

    if (image.quality<0 && image.quality>99) {
	CPLError(CE_Warning, CPLE_AppDefined, "GDAL MRF: Quality setting error, using default of 85");
	image.quality=85;
    }

    // Data Type, use GDAL Names
    image.dt=GDALGetDataTypeByName(
	CPLGetXMLValue(defimage,"DataType",GDALGetDataTypeName(image.dt)));
    if (image.dt==GDT_Unknown) {
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Image has wrong type");
	return CE_Failure;
    }

    // Check the endianess if needed, assume host order
    if (is_Endianess_Dependent(image.dt,image.comp))
	image.nbo = on(CPLGetXMLValue(defimage,"NetByteOrder","No"));

    CPLXMLNode *DataValues=CPLGetXMLNode(defimage,"DataValues");
    if (NULL!=DataValues) {
	const char *pszValue;
	pszValue=CPLGetXMLValue(DataValues, "NoData", 0);
	if (pszValue) ds->SetNoDataValue(pszValue);
	pszValue=CPLGetXMLValue(DataValues, "min", 0);
	if (pszValue) ds->SetMinValue(pszValue);
	pszValue=CPLGetXMLValue(DataValues, "max", 0);
	if (pszValue) ds->SetMaxValue(pszValue);
    }

    // Calculate the page size in bytes
    image.pageSizeBytes=GDALGetDataTypeSize(image.dt)/8*
	image.pagesize.x * image.pagesize.y * image.pagesize.z * image.pagesize.c;

    // Calculate the page count, including the total for the level
    pcount(image.pcount,image.size,image.pagesize);

    // Data File Name and offset
    image.datfname=getFname(defimage,"DataFile",ds->GetFname(),ILComp_Ext[image.comp]);
    image.dataoffset=static_cast<int>(
	getXMLNum(CPLGetXMLNode(defimage,"DataFile"), "offset",0));

    // Index File Name and offset
    image.idxfname=getFname(defimage, "IndexFile", ds->GetFname(), ".idx");
    image.idxoffset=static_cast<int>(
	getXMLNum(CPLGetXMLNode(defimage,"IndexFile"), "offset",0));

    return CE_None;
}

char      **GDALMRFDataset::GetFileList() 
{
    char** papszFileList=0;

    // Add the header file name if it is real
    VSIStatBufL  sStat;
    if ( VSIStatExL( fname, &sStat, VSI_STAT_EXISTS_FLAG ) == 0 )
	papszFileList = CSLAddString( papszFileList, fname);

    // These two should be real
    papszFileList = CSLAddString( papszFileList, full.datfname);
    papszFileList = CSLAddString( papszFileList, full.idxfname);

    return papszFileList;
}

// Returns the dataset index file or null 
VSILFILE *GDALMRFDataset::IdxFP() {
    if (ifp.FP != NULL)
	return ifp.FP;
    char *mode = "rb";
    ifp.acc = GF_Read;

    if (eAccess == GA_Update || !source.empty()) {
	mode = "r+b";
	ifp.acc = GF_Write;
    }
    ifp.FP = VSIFOpenL(current.idxfname, mode );

    // Got it open or it doesn't need one
    if (ifp.FP || current.comp == IL_NONE)
	return ifp.FP;

    // Could be a caching MRF
    if (source.empty()) {
	CPLError(CE_Failure, CPLE_AppDefined,
	"GDAL MRF: Can't open index file %s\n", current.idxfname.c_str());
	return ifp.FP;
    }

    // This is a caching MRF, could be read only
    mode = "rb";
    ifp.acc = GF_Read;
    ifp.FP = VSIFOpenL(current.idxfname.c_str(), mode);
    if (NULL != ifp.FP)
	return ifp.FP;

    // Caching and not index file exits, try to create it
    // Nope, try to create it, and make it large enough
    int idx_sz = static_cast<int>(IdxSize(current, scale));
    if (!CheckFileSize(current.idxfname.c_str(), idx_sz, GA_Update)) {
	CPLError(CE_Failure,CPLE_AppDefined,"Can't create the cache index file");
	return NULL;
    }

    // Try opening it again in rw mode
    mode = "r+b";
    ifp.acc = GF_Write;
    ifp.FP = VSIFOpenL(current.idxfname.c_str(), mode);

    // Nothing more we can do
    if (NULL == ifp.FP)
	CPLError(CE_Failure, CPLE_AppDefined,
	"GDAL MRF: Can't open cache index file %s\n", current.idxfname.c_str());

    return ifp.FP;
};

//
// Returns the dataset data file or null 
// Data file is opened either in Read or Append mode, never in straight write
//
VSILFILE *GDALMRFDataset::DataFP() {
    if (dfp.FP != NULL)
	return dfp.FP;
    char *mode = "rb";
    dfp.acc = GF_Read;

    // Open it for writing if updating or if caching
    if (eAccess == GA_Update || !source.empty()) {
	mode = "a+b";
	dfp.acc = GF_Write;
    }

    dfp.FP = VSIFOpenL(current.datfname.c_str(), mode);
    if (dfp.FP)
	return dfp.FP;

    // It could be a caching MRF
    if (source.empty()) {
	CPLError(CE_Failure, CPLE_AppDefined,
	"GDAL MRF: Can't open data file %s\n", current.datfname.c_str());
	return dfp.FP;
    }

    // Cloud be there but read only, remember it was open that way
    mode = "rb";
    dfp.acc = GF_Read;
    dfp.FP = VSIFOpenL(current.datfname.c_str(), mode);
    if (NULL != dfp.FP)
	return dfp.FP;

    // We should have created it above with "a+b"
    CPLError(CE_Failure, CPLE_AppDefined,
	"GDAL MRF: Can't open data file %s\n", current.datfname.c_str());
    return dfp.FP;
};

/**
* \Brief Populates the dataset variables from the XML definition file
*
*
*/
CPLErr GDALMRFDataset::Initialize(CPLXMLNode *config)

{
    // We only need a basic initialization here, usually gets overwritten by the image params
    full.dt=GDT_Byte;
    full.hasNoData=false;
    full.NoDataValue = 0;
    Quality=85;

    CPLErr ret=Init_ILImage(full, config, this);
    Quality=full.quality;
    if (CE_None!=ret)
	return ret;

    // Bounding box
    CPLXMLNode *bbox = CPLGetXMLNode(config, "GeoTags.BoundingBox");
    if (NULL!=bbox) {
	double x0,x1,y0,y1;

	x0=atof(CPLGetXMLValue(bbox,"minx","0"));
	x1=atof(CPLGetXMLValue(bbox,"maxx","1"));
	y1=atof(CPLGetXMLValue(bbox,"maxy","1"));
	y0=atof(CPLGetXMLValue(bbox,"miny","0"));

	GeoTransform[0]=x0;
	GeoTransform[1]=(x1-x0)/full.size.x;
	GeoTransform[2]=0;
	GeoTransform[3]=y1;
	GeoTransform[4]=0;
	GeoTransform[5]=(y0-y1)/full.size.y;
	bGeoTransformValid=TRUE;
    }

    SetProjection(CPLGetXMLValue(config,"GeoTags.Projection",
	ProjToWKT("EPSG:4326")));

    // Copy the full size to current, data and index are not yet open
    current=full;
    // Bands can be used to overwrite from the whole c size
    current.size.c = static_cast<int>(getXMLNum(config,"Bands",current.size.c));

    // Dataset metadata setup
    SetMetadataItem("INTERLEAVE",OrderName(current.order), "IMAGE_STRUCTURE");
    SetMetadataItem("COMPRESS",CompName(current.comp), "IMAGE_STRUCTURE");
    if (is_Endianess_Dependent(full.dt, full.comp))
	SetMetadataItem("NETBYTEORDER", full.nbo?"TRUE":"FALSE", "IMAGE_STRUCTURE");

    // Open the files for the current image, either RW or RO
    nRasterXSize = current.size.x;
    nRasterYSize = current.size.y;
    nBands = current.size.c;

    if (!nBands || !nRasterXSize || !nRasterYSize ) {
	CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Image size missing");
	return CE_Failure;
    }

    // Pick up the source data image, if there is one
    source = CPLStrdup(CPLGetXMLValue(config,"CachedSource.Source",0));
    options = CPLStrdup(CPLGetXMLValue(config,"Options",0));
    optlist = CSLTokenizeString2(options.c_str()," \t\n\r",
	CSLT_STRIPLEADSPACES|CSLT_STRIPENDSPACES);

    // We have the options, so we can call rasterband
    CPLXMLNode *rsets=CPLGetXMLNode(config,"Rsets");
    for (int i=1;i<=nBands;i++) {
	// The subimages are low resolution copies of the current one.
	GDALMRFRasterBand *band = newMRFRasterBand(this, current, i);
	SetBand(i,band);
	band->SetColorInterpretation(BandInterp(nBands, i));
    }

    // If no overviews are defined, done
    if ((NULL==rsets) || (NULL==rsets->psChild))
	return CE_None;

    // Regular spaced overlays, until everything fits in a single tile
    if (EQUAL("uniform",CPLGetXMLValue(rsets,"model","uniform"))) {
	scale = getXMLNum(rsets,"scale",2.0);
	if (scale<=1) {
	    CPLError(CE_Failure, CPLE_AppDefined, "MRF: zoom factor less than unit not allowed");
	    return CE_Failure;
	}
	// Looks like there are overlays
	AddOverviews(int(scale));
	return CE_None;
    } else {
	CPLError(CE_Failure, CPLE_AppDefined, "Unknown Rset definition");
	return CE_Failure;
    }
}

/**
*\Brief Get the source dataset, open it if necessary
*/
GDALDataset *GDALMRFDataset::GetSrcDS() {
    if (poSrcDS) 
	return poSrcDS;
    // Does it actualy have a file name
    if (source.empty())
	return 0;
    // Try to open it, add the path from the current MRF if this file doesn't have one but the file does
    if (source.find_first_of("/\\") == std::string::npos
	&& fname.find_first_of("/\\") != std::string::npos )
	    source = fname.substr(0,fname.find_last_of("/\\")) + "/" + source;
    return
	poSrcDS = (GDALDataset *) (GDALOpenShared( source.c_str(), GA_ReadOnly ));
}

/**
*\Brief Add or verify that all overlays exits
*
* @return size of the index file
*/

GIntBig GDALMRFDataset::AddOverviews(int scale) {
    // Fit the overlays
    ILImage img=full;
    do {
	// Adjust the offsets for indices
	img.idxoffset+=sizeof(ILIdx)*img.pcount.l;
	img.size.x=pcount(img.size.x,scale);
	img.size.y=pcount(img.size.y,scale);
	img.size.l++; // Increment the level
	pcount(img.pcount,img.size,img.pagesize);
	// Create and register the the overviews for each band
	for (int i=1;i<=nBands;i++) {
	    GDALMRFRasterBand *b=(GDALMRFRasterBand *)GetRasterBand(i);
	    if (!(b->GetOverview(img.size.l-1)))
		b->AddOverview(newMRFRasterBand(this,img,i,img.size.l));
	}
    } while (1!=img.pcount.x*img.pcount.y);

    // Last adjustment, should be a single set of c and z tiles
    img.idxoffset+=sizeof(ILIdx)*img.pcount.l;
    return img.idxoffset;
}

//
// Print a double in a reversible way when read with strtod
//
static CPLString PrintDouble(double d)
{

    CPLString res;
    res.FormatC(d,0);
    double v=CPLStrtod(res.c_str(),NULL);
    if (d == v) return res;
    
//  This would be the right code with a C99 compiler that supports %a readback in strod()
//    return CPLString().Printf("%a",d);

    return CPLString().FormatC(d, "%12.8f");
}


/**
 *\Brief Create a MRF file from an existing DS
 */
GDALDataset *GDALMRFDataset::CreateCopy(const char *pszFilename, 
					GDALDataset *poSrcDS, int bStrict, char **papszOptions, 
					GDALProgressFunc pfnProgress, void *pProgressData)
{
    const char *pszValue;
    GDALColorTable *poColorTable=NULL;

    ILImage img;

    // Defaults
    int nXSize = poSrcDS->GetRasterXSize();
    int nYSize = poSrcDS->GetRasterYSize();
    int nBands = poSrcDS->GetRasterCount();

    img.size = ILSize(nXSize, nYSize, 1, nBands);
    // Set some defaults
    ILCompression comp=IL_PNG;
    // Most formats can't handle more than 4 bands interleaved (JPEG,PNG)
    ILOrder ord = (nBands < 5) ? IL_Interleaved : IL_Separate;
    ILSize page(512,512,1,1);
    int quality = 85;
    bool nbo=NET_ORDER;

    // Use the info from the input image
    // Use the poSrcDS or the first band to find out info about the dataset
    GDALRasterBand *poPBand=poSrcDS->GetRasterBand(1);
    GDALDataType dt=poPBand->GetRasterDataType();

    // Use the blocks from the input image if it is reasonable, otherwise stick to the default
    int srcXBlk,srcYBlk;
    poPBand->GetBlockSize(&srcXBlk,&srcYBlk);
    // Ignore the line blocking that TIF emulates
    if (srcYBlk <= 2) srcYBlk=nYSize;
    if ((srcXBlk!=nXSize) && (srcYBlk!=nYSize)) {
	page.x=srcXBlk;
	page.y=srcYBlk;
    }

    // This could be a cached source file
    CPLString source(CPLStrdup(CSLFetchNameValue(papszOptions, "CACHEDSOURCE")));
    // Get freeform params
    CPLString options(CPLStrdup(CSLFetchNameValue(papszOptions, "OPTIONS")));

    // Except if the BLOCKSIZE BLOCKXSIZE and BLOCKYSIZE are set
    pszValue = CSLFetchNameValue(papszOptions,"BLOCKSIZE");
    if ( pszValue != NULL ) page.x = page.y = atoi( pszValue );
    pszValue = CSLFetchNameValue(papszOptions,"BLOCKXSIZE");
    if ( pszValue != NULL ) page.x = atoi( pszValue );
    pszValue = CSLFetchNameValue(papszOptions,"BLOCKYSIZE");
    if ( pszValue != NULL ) page.y = atoi( pszValue );

    // Get the quality setting
    pszValue = CSLFetchNameValue(papszOptions,"QUALITY");    
    if ( pszValue != NULL )
	quality = atoi( pszValue );

    if ( quality < 0 || quality > 99 ) {
	CPLError(CE_Warning, CPLE_AppDefined,
	    "GDAL MRF: Quality setting should be between 0 and 99, using 85");
	quality = 85;
    }

    // If the source image has a NoDataValue, min or max, we keep them
    CPLString NoData;
    CPLString Min;
    CPLString Max;
    int bHas;
    double dfData;

    for (int i=0; i <nBands; i++) {
	dfData=poSrcDS->GetRasterBand(i+1)->GetNoDataValue(&bHas);
	if (bHas)
	    NoData.append(PrintDouble(dfData) + " ");
    }

    for (int i=0; i <nBands; i++) {
	dfData=poSrcDS->GetRasterBand(i+1)->GetMinimum(&bHas);
	if (bHas)
	    Min.append(PrintDouble(dfData) + " ");
    }

    for (int i=0; i <nBands; i++) {
	dfData=poSrcDS->GetRasterBand(i+1)->GetMaximum(&bHas);
	if (bHas)
	    Max.append(PrintDouble(dfData) + " ");
    }

    // Network byte order requested?
    nbo = on(CSLFetchNameValue(papszOptions,"NETBYTEORDER"));

    // Use the source compression if we understand it
    comp=CompToken(poPBand->GetMetadataItem("COMPRESSION","IMAGE_STRUCTURE"),comp);

    // Input options, overrides
    pszValue=CSLFetchNameValue(papszOptions,"COMPRESS");
    if (pszValue) if (IL_ERR_COMP==(comp=CompToken(pszValue))) {
	CPLError(CE_Warning, CPLE_AppDefined, "GDAL MRF: Compression %s is unknown, "
	    "using PNG", pszValue);
	comp=IL_PNG;
    }

    // Order, from source, overwritten by options
    pszValue = poPBand->GetMetadataItem("INTERLEAVE", "IMAGE_STRUCTURE");
    if (0 != CSLFetchNameValue(papszOptions,"INTERLEAVE"))
	pszValue = CSLFetchNameValue(papszOptions,"INTERLEAVE");


#if defined(LERC)
    if (comp==IL_LERC)
	ord=IL_Separate;
#endif

    if (pszValue) if (IL_ERR_ORD==(ord=OrderToken(pszValue))) {
	CPLError(CE_Warning, CPLE_AppDefined, "GDAL MRF: Interleave model %s is unknown, "
	    "using PIXEL",pszValue);
	ord=IL_Interleaved;
    }

    // Error checks and synchronizations

    // If interleaved model is requested and no page size is set,
    // use the number of bands
    if (nBands>1 && IL_Interleaved==ord)
	page.c=nBands;

    // Check compression based limitations
    if (1 != page.c) {
	if ((IL_PNG==comp)||(IL_PPNG==comp)) {
	    if (page.c>4) {
		CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: %s "
		    " Compression can't handle %d pixel interleaved bands\n",
		    CompName(IL_PNG),page.c);
		return NULL;
	    }
	}
	if (IL_JPEG==comp) {
	    if ((2==page.c) || (page.c>4)) {
		CPLError(CE_Failure, CPLE_AppDefined, "GDAL MRF: Compression %s "
		    "can't handle %d pixel interleaved bands\n",
		    CompName(IL_JPEG),page.c);
		return NULL;
	    }
	}
    }

#if defined(LERC)
    if (comp==IL_LERC && ord!=IL_Separate) {
	CPLError(CE_Warning, CPLE_AppDefined, "GDAL MRF: LERC ony handles BAND Interleave");
	ord=IL_Separate;
	page.c = 1;
    }
#endif

    // Check data type
    if ((IL_JPEG==comp) && (dt!=GDT_Byte)) {
	CPLError(CE_Failure,CPLE_AppDefined, "GDAL MRF: JPEG compression only supports byte data");
	return NULL;
    } else if ((IL_PNG==comp) && (dt!=GDT_Byte) && (dt!=GDT_Int16) && (dt!=GDT_UInt16)) {
	CPLError(CE_Failure,CPLE_AppDefined, 
	    "GDAL MRF: PNG only supports 8 and 16 bits of data, format is %s",GDALGetDataTypeName(dt));
	return NULL;
    }

    CPLString fname_data(getFname(pszFilename, ILComp_Ext[comp]));
    CPLString fname_idx(getFname(pszFilename, ".idx"));

    // Get the color palette if we only have one band
    if ( 1==nBands && GCI_PaletteIndex==poPBand->GetColorInterpretation() )
	poColorTable=poPBand->GetColorTable()->Clone();

    // Check for format is PPNG and we don't have a palette
    // TODO: create option to build a palette, using the syntax from VRT LUT
    if (( poColorTable==NULL ) && ( comp==IL_PPNG )) {
	comp=IL_PNG;
	CPLError(CE_Warning,CPLE_AppDefined, 
	    "GDAL MRF: PPNG needs a palette based input, switching to PNG");
    }

    int factor=0;
    pszValue = CSLFetchNameValue(papszOptions,"UNIFORM_OVERLAY_SCALE");
    if ( pszValue != NULL )
	factor = atoi( pszValue );

    if (!source.empty()) { // Extra stuff to worry about when caching

    }

    img.pagesize = page;

    // Build the XML file
    CPLXMLNode *config=CPLCreateXMLNode(NULL,CXT_Element,"MRF_META");
    if (!source.empty()) {
	CPLXMLNode *CS = CPLCreateXMLNode(config, CXT_Element, "CachedSource");
	// Should wrap the string in CDATA, in case it is XML
	CPLXMLNode *S = CPLCreateXMLElementAndValue(CS, "Source",source.c_str());
    }

    CPLXMLNode *raster=CPLCreateXMLNode(config,CXT_Element,"Raster");
    XMLSetAttributeVal(raster,"Size",ILSize(nXSize,nYSize,1,nBands),"%.0f");

    if (comp!=IL_PNG)
	CPLCreateXMLElementAndValue(raster,"Compression",CompName(comp));

    if (dt!=GDT_Byte)
	CPLCreateXMLElementAndValue(raster,"DataType",GDALGetDataTypeName( dt));

    if (NoData.size()|| Min.size()|| Max.size()) {
	CPLXMLNode *values=CPLCreateXMLNode(raster,CXT_Element,"DataValues");
	if (NoData.size()) {
	    CPLCreateXMLNode(values,CXT_Attribute,"NoData");
	    CPLSetXMLValue(values,"NoData",NoData.c_str());
	}
	if (Min.size()) {
	    CPLCreateXMLNode(values,CXT_Attribute,"min");
	    CPLSetXMLValue(values,"min",Min.c_str());
	}
	if (Max.size()) {
	    CPLCreateXMLNode(values,CXT_Attribute,"max");
	    CPLSetXMLValue(values,"max",Max.c_str());
	}
    }

    // palette, if we have one
    if (poColorTable!=NULL) {
	CPLXMLNode *pal = CPLCreateXMLNode(raster,CXT_Element,"Palette");
	int sz=poColorTable->GetColorEntryCount();
	if (sz!=256)
	    XMLSetAttributeVal(pal,"Size",poColorTable->GetColorEntryCount());
	// Should also check and set the colormodel, RGBA for now
	for (int i=0;i<sz;i++) {
	    CPLXMLNode *entry=CPLCreateXMLNode(pal,CXT_Element,"Entry");
	    const GDALColorEntry *ent=poColorTable->GetColorEntry(i);
	    // No need to set the index, it is always from 0 no size-1
	    XMLSetAttributeVal(entry,"c1",ent->c1);
	    XMLSetAttributeVal(entry,"c2",ent->c2);
	    XMLSetAttributeVal(entry,"c3",ent->c3);
	    if (ent->c4!=255)
		XMLSetAttributeVal(entry,"c4",ent->c4);
	}

	// Done with the palette
	delete poColorTable;
    }

    if (is_Endianess_Dependent(dt,comp)) // Need to set the order
	CPLCreateXMLElementAndValue(raster,"NetByteOrder",
	(nbo||NET_ORDER)? "TRUE": "FALSE");

    if (quality>0)
	CPLCreateXMLElementAndValue(raster,"Quality", CPLString().Printf("%d",quality).c_str());

    XMLSetAttributeVal(raster,"PageSize",img.pagesize,"%.0f");
    // Done with raster

    CPLCreateXMLNode(config, CXT_Element,"Rsets");
    if (factor != 0) {
	CPLSetXMLValue(config, "Rsets.#model", "uniform");
	CPLSetXMLValue(config, "Rsets.#scale", CPLString().Printf("%d",factor).c_str());
    }
    CPLXMLNode *gtags=CPLCreateXMLNode(config, CXT_Element, "GeoTags");

    // Do we have a meaningfull affine transform?
    double gt[6];

    if (poSrcDS->GetGeoTransform(gt)==CE_None
	&& (gt[0] != 0 || gt[1] != 1 || gt[2] != 0 || 
	gt[3] != 0 || gt[4] != 0 || gt[5] != 1 ))
    {
	static const char frmt[]="%12.8f";
	double minx=gt[0];
	double maxx=gt[1]*poSrcDS->GetRasterXSize()+minx;
	double maxy=gt[3];
	double miny=gt[5]*poSrcDS->GetRasterYSize()+maxy;
	CPLXMLNode *bbox=CPLCreateXMLNode(gtags,CXT_Element,"BoundingBox");
	XMLSetAttributeVal(bbox,"minx",minx,frmt);
	XMLSetAttributeVal(bbox,"miny",miny,frmt);
	XMLSetAttributeVal(bbox,"maxx",maxx,frmt);
	XMLSetAttributeVal(bbox,"maxy",maxy,frmt);
    }

    const char *pszProj=poSrcDS->GetProjectionRef();
    if (pszProj&&(!EQUAL(pszProj,"")))
	CPLCreateXMLElementAndValue(gtags,"Projection",pszProj);

    CPLCreateXMLElementAndValue(config, "Options", options.c_str());

    // Dump the XML
    CPLSerializeXMLTreeToFile(config,pszFilename);
    CPLDestroyXMLNode(config);

    // Create the data and index files, but only if they don't exist, otherwise leave them untouched
    VSILFILE *f_data=VSIFOpenL(fname_data,"r+b");
    if (NULL==f_data)
	f_data = VSIFOpenL(fname_data,"w+b");
    VSILFILE *f_idx=VSIFOpenL(fname_idx,"r+b");
    if (NULL==f_idx)
	f_idx = VSIFOpenL(fname_idx,"w+b");

    if ((NULL == f_data)||(NULL == f_idx)) {
	CPLError(CE_Failure,CPLE_AppDefined,"Can't open data or index files in update mode");
	return NULL;
    }
    // Close them
    VSIFCloseL(f_idx);
    VSIFCloseL(f_data);

    // Leave the data empty but build the index file
    int idx_sz = static_cast<int>(IdxSize(img, factor));

    // Create or check the index file
    int ret = CheckFileSize(fname_idx, idx_sz, GA_Update);

    if (!ret) {
	CPLError(CE_Failure,CPLE_AppDefined,"Can't extend the index file");
	return NULL;
    }

    // Reopen in RW mode and use the standard CopyWholeRaster
    GDALDataset *poDS = (GDALDataset *) GDALOpen(pszFilename, GA_Update);

    // If there is a source name and copy is disabled, we're done
    if (!source.empty() && on(CSLFetchNameValue(papszOptions, "NOCOPY")))
	return poDS;

    // Need to flag the dataset as compressed (COMPRESSED=TRUE) to force block writes
    // This might not be what we want, if the input and out order is separate
    char **papszCWROptions = CSLDuplicate(0);
    papszCWROptions = CSLAddNameValue(papszCWROptions, "COMPRESSED", "TRUE");
    CPLErr err=GDALDatasetCopyWholeRaster( (GDALDatasetH) poSrcDS,
	(GDALDatasetH) poDS, papszCWROptions, pfnProgress,
	pProgressData);
    CSLDestroy(papszCWROptions);
    if (CE_Failure==err) {
	delete poDS;
	// Maybe clean up the files that might have been created here?
	return NULL;
    }

    return poDS;
}

CPLErr GDALMRFDataset::SetProjection( const char *pszNewProjection)

{
    CPLFree( pszProjection );
    pszProjection = CPLStrdup( pszNewProjection );
    return CE_None;
}

const char *GDALMRFDataset::GetProjectionRef()

{
    if (NULL==pszProjection||EQUAL(pszProjection,""))
	return GDALPamDataset::GetProjectionRef();
    return pszProjection;
}

CPLErr GDALMRFDataset::SetGeoTransform( double *gt)

{
    if ( GetAccess() == GA_Update )
    {
	memcpy( GeoTransform, gt, 6*sizeof(double));
	bGeoTransformValid=TRUE;
	return CE_None;
    }
    CPLError( CE_Failure, CPLE_NotSupported,
	"SetGeoTransform called on read only file");
    return CE_Failure;
}

/*
*  Should return 0,1,0,0,0,1 even if it was not set
*/
CPLErr GDALMRFDataset::GetGeoTransform( double *gt)

{
    memcpy(gt,GeoTransform, 6*sizeof(double));
    if (!bGeoTransformValid) return CE_Failure;
    return CE_None;
}


// Averaging round up, 0.5 for integers, 0 for floats
template<typename T> T AvgRoundUpVal(T mul) {
    return T(0.5*mul);
}
double AvgRoundUpVal(double) { return 0; }
float AvgRoundUpVal(float) { return 0; }

template<typename T> void average_by_four(T *buff,int xsz, int ysz) {
    T *obuff=buff;
    T *evenline=buff;
    // Type dependent premultiplied bias
    T bias = AvgRoundUpVal(T(4));

    for (int line=0;line<ysz;line++) {
	T *oddline=evenline+xsz*2;
	for (int col=0; col<xsz; col++)
	    *obuff++ = (bias + *evenline++ + *evenline++ + *oddline++ + *oddline++) / 4;
	evenline += xsz*2;  // Skips the other line
    }
}

/*
 *\brief Patches an overview for the selected area
 * arguments are in blocks in the source level, if toTheTop is false it only does the next level
 * It will read adjacent blocks if they are needed, so actual area read might be padded by one block in 
 * either side
 */

CPLErr GDALMRFDataset::PatchOverview(int BlockX,int BlockY,
				      int Width,int Height, 
				      int srcLevel, int recursive) 
{
    GDALRasterBand *b0=GetRasterBand(1);
    if ( b0->GetOverviewCount() <= srcLevel) 
	return CE_None;

    int BlockXOut = BlockX/2 ; // Round down
    Width += BlockX & 1; // Increment width if rounding down
    int BlockYOut = BlockY/2 ; // Round down
    Height += BlockY & 1; // Increment height if rounding down

    int WidthOut = Width/2 + (Width & 1); // Round up
    int HeightOut = Height/2 + (Height & 1); // Round up

    int bands=GetRasterCount();
    int tsz_x,tsz_y;
    b0->GetBlockSize(&tsz_x,&tsz_y);
    GDALDataType eDataType=b0->GetRasterDataType();

    int pixel_size=GDALGetDataTypeSize(eDataType)/8; // Bytes per pixel per band
    int line_size=tsz_x*pixel_size; // A line has this many bytes
    int buffer_size=line_size*tsz_y; // A block size in bytes

    // Build a vector of output bands
    vector<GDALRasterBand *>src_b;
    vector<GDALRasterBand *>dst_b;

    for (int band=1;band<=bands;band++) {
	if (srcLevel==0)
	    src_b.push_back(GetRasterBand(band));
	else
	    src_b.push_back(GetRasterBand(band)->GetOverview(srcLevel-1));
	dst_b.push_back(GetRasterBand(band)->GetOverview(srcLevel));
    }

    // Allocate space for four blocks
    void *buffer=CPLMalloc(buffer_size *4 );

    void *in_buff[4]; // Pointers to the four blocks
    for (int i=0;i<4;i++)
	in_buff[i]=(char *)buffer+i*buffer_size;

    for (int y=0; y<HeightOut; y++) {
	int dst_offset_y = BlockYOut+y;
	int src_offset_y = dst_offset_y *2;
	for (int x=0; x<WidthOut; x++) {
	    int dst_offset_x = BlockXOut + x;
	    int src_offset_x = dst_offset_x * 2;

	    // Do it band at a time so we can work in grayscale
	    for (int band=0; band<bands; band++) { // Counting from zero in a vector
		// This gets read from the right overview
		int sz_x = 2*tsz_x ,sz_y = 2*tsz_y ;

		//
		// Clip to the size to the input image
		// This is one of the worst features of GDAL, it doesn't tollerate any padding
		//

		if ( src_b[band]->GetXSize() < (src_offset_x + 2) * tsz_x )
		    sz_x = src_b[band]->GetXSize() - src_offset_x * tsz_x;
		if ( src_b[band]->GetYSize() < (src_offset_y + 2) * tsz_y )
		    sz_y = src_b[band]->GetYSize() - src_offset_y * tsz_y;

		src_b[band]->RasterIO( GF_Read,
		    src_offset_x*tsz_x,src_offset_y*tsz_y, // offset in input image
		    sz_x, sz_y, // Size in output image
		    buffer, sz_x, sz_y, // Buffer and size in buffer
		    eDataType, // Requested type
		    pixel_size, 2*line_size ); // Pixel and line space


#define avg(T) average_by_four((T *)buffer,tsz_x,tsz_y); break
		switch(eDataType) {
		case GDT_Byte:      avg(unsigned char);
		case GDT_UInt16:    avg(unsigned short int);
		case GDT_Int16:     avg(short int);
		case GDT_UInt32:    avg(unsigned int);
		case GDT_Int32:     avg(int);
		case GDT_Float32:   avg(float);
		case GDT_Float64:   avg(double);
		default: // This is an error, undefined behaviour
		    fprintf(stderr,"Unknown data type for MRF overlays");
		}
#undef avg

		// Always grayscale here
		// Argh, still need to clip the output to the band size on the right and bottom
		// The offset should be fine, just the size might need adjustments

		sz_x = tsz_x;
		sz_y = tsz_y ;

		if ( dst_b[band]->GetXSize() < dst_offset_x * tsz_x + tsz_x )
		    sz_x=dst_b[band]->GetXSize() - dst_offset_x * tsz_x;
		if ( dst_b[band]->GetYSize() < dst_offset_y * tsz_y + tsz_y )
		    sz_y=dst_b[band]->GetYSize() - dst_offset_y * tsz_y;

		dst_b[band]->RasterIO( GF_Write,
		    dst_offset_x*tsz_x,dst_offset_y*tsz_y, // offset in output image
		    sz_x, sz_y, // Size in output image
		    buffer, sz_x, sz_y, // Buffer and size in buffer
		    eDataType, // Requested type
		    pixel_size, line_size ); // Pixel and line space
	    }
	}
    }

    CPLFree(buffer);

    for (int band=0; band<bands; band++) 
	dst_b.at(band)->FlushCache(); // Commit the output to disk

    if (!recursive)
	return CE_None;
    return PatchOverview( BlockXOut, BlockYOut, WidthOut, HeightOut, srcLevel+1, true);
}
