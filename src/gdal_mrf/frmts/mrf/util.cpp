

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



/**
 *  $Id$
 *
 *  Functions used by the driver, should all have prototypes in the header file
 *
 *  Author: Lucian Plesea, Lucian.Plesea@jpl.nasa.gov
 */

#include "marfa.h"

static const char *ILC_N[]={ "PNG", "PPNG", "JPEG", "NONE", "DEFLATE", "TIF", "Unknown" };
static const char *ILC_E[]={ ".ppg", ".ppg", ".pjg", ".til", ".pzp", ".ptf", "" };
static const char *ILO_N[]={ "PIXEL", "BAND", "LINE", "Unknown" };

char const **ILComp_Name=ILC_N;
char const **ILComp_Ext=ILC_E;
char const **ILOrder_Name=ILO_N;

CPL_C_START
void GDALRegister_mrf(void);
void GDALDeregister_mrf( GDALDriver * ) {};
CPL_C_END

/************************************************************************/
/*                           BandInterp()                               */
/************************************************************************/

/**
 * \brief Utility function to calculate color band interpretation.
 * Only handles Gray, GrayAlpha, RGB and RGBA, based on total band count
 *
 * @param nbands is the total number of bands in the image
 *
 * @param band is the band number, starting with 1
 *
 * @return GDALColorInterp of the band
 */

GDALColorInterp BandInterp(int nbands, int band) 
{
    switch (nbands) {
    case 1: return GCI_GrayIndex;
    case 2: return ((band==1)?GCI_GrayIndex:GCI_AlphaBand);
    case 3: // RGB
    case 4: // RBGA
        if (band<3)
            return ((band==1)?GCI_RedBand:GCI_GreenBand);
        return ((band==3)?GCI_BlueBand:GCI_AlphaBand);
    default:
        return GCI_Undefined;
    }
}

/**
 *  Get the string for a compression type
 */

const char *CompName(ILCompression comp) 
{
    if (comp>=IL_ERR_COMP) return ILComp_Name[IL_ERR_COMP];
    return ILComp_Name[comp];
}

/**
 *  Get the string for an order type
 */

const char *OrderName(ILOrder val) 
{
    if (val>=IL_ERR_ORD) return ILOrder_Name[IL_ERR_ORD];
    return ILOrder_Name[val];
}

ILCompression CompToken(const char *opt, ILCompression def) 
{
    int i;
    if (NULL==opt) return def;
    for (i=0; ILCompression(i)<IL_ERR_COMP; i++)
        if (EQUAL(opt,ILComp_Name[i]))
            break;
    if (IL_ERR_COMP==ILCompression(i)) 
        return def;
    return ILCompression(i);
}

/**
 *  Find a compression token
 */

ILOrder OrderToken(const char *opt, ILOrder def) 
{
    int i;
    if (NULL==opt) return def;
    for (i=0; ILOrder(i)<IL_ERR_ORD; i++)
        if (EQUAL(opt,ILOrder_Name[i]))  
            break;
    if (IL_ERR_ORD==ILOrder(i)) 
        return def;
    return ILOrder(i);
}

//
//  Inserters for ILSize and ILIdx types
//

std::ostream& operator<<(std::ostream &out, const ILSize& sz)
{
    out << "X=" << sz.x << ",Y=" << sz.y << ",Z=" << sz.z 
        << ",C=" << sz.c << ",L=" << sz.l;
    return out;
}

std::ostream& operator<<(std::ostream &out, const ILIdx& t) {
    out << "offset=" << t.offset << ",size=" << t.size;
    return out;
}

// Define PPMW in marfa.h to enable this handy debug function

#ifdef PPMW
void ppmWrite(const char *fname, const char *data, const ILSize &sz) {
    FILE *fp=fopen(fname,"wb");
    switch(sz.c) {
    case 4: 
        {
            fprintf(fp,"P6 %d %d 255\n",sz.x,sz.y);
            char *d=(char *)data;
            for(int i=sz.x*sz.y;i;i--) {
                fwrite(d,3,1,fp);
                d+=4;
            }
            break;
        }
    case 3:
        {
            fprintf(fp,"P6 %d %d 255\n",sz.x,sz.y);
            fwrite(data,sz.x*sz.y,3,fp);
            break;
        }
    case 1:
        {
            fprintf(fp,"P5 %d %d 255\n",sz.x,sz.y);
            fwrite(data,sz.x,sz.y,fp);
            break;
        }
    default:
        fprintf(stderr,"Can't write ppm file with %d bands\n",sz.c);
        return;
    }
    fclose(fp);
}
#endif

/**
 *\brief Get a file name by replacing the extension.
 * pass the data file name and the default extension starting with .
 * If name length is not sufficient, it returns the def argument
 */

CPLString getFname(const CPLString &in, const char *def) 
{
    CPLString ret(in);

    if ((strlen(def)==4)&&(strlen(in)>4)) {
        ret.replace(ret.size()-4,4,def);
        return ret;
    }

    return CPLString(def);
}

/**
 *\brief Get a file name, either from the configuration or from the default file name
 * If the token is not defined by CPLGetXMLValue, if the extension of the in name is .xml, 
 * it returns the token with the extension changed to defext.  
 * Otherwise it retuns the token itself
 */

CPLString getFname(CPLXMLNode *node,const char *token, const CPLString &in, const char *def) 
{
    return CPLGetXMLValue(node,token,getFname(in,def).c_str());
}


/**
 *\Brief Extracts a numerical value from a XML node
 * It works like CPLGetXMLValue except for the default value being
 * a number instead of a string
 */

double getXMLNum(CPLXMLNode *node, const char *pszPath, double def) 
{
    const char *textval=CPLGetXMLValue(node,pszPath,0);
    if (textval) return atof(textval);
    return def;
}

//
// Calculate offset of index, pos is in pages
//

GIntBig IdxOffset(const ILSize &pos,const ILImage &img) 
{
    return img.idxoffset+sizeof(ILIdx)*
        ((GIntBig)pos.c+img.pcount.c*(pos.x+img.pcount.x*
        (pos.y+img.pcount.y*pos.z)));
}

// Is compress type endianess dependent?
bool is_Endianess_Dependent(GDALDataType dt, ILCompression comp) {
    if (IL_ZLIB==comp||IL_NONE==comp)
        if (GDALGetDataTypeSize( dt )>8) return true;
    return false;
}


/************************************************************************/
/*                          GDALRegister_mrf()                          */
/************************************************************************/

void GDALRegister_mrf(void)

{
    GDALDriver *driver;

    if (GDALGetDriverByName("MRF") == NULL) {
        driver = new GDALDriver();
        driver->SetDescription("MRF");
        driver->SetMetadataItem(GDAL_DMD_LONGNAME, "Meta Raster Format");
        driver->SetMetadataItem(GDAL_DMD_HELPTOPIC, "frmt_marfa.html");

        // These will need to be revisited.  Are they required?
        driver->SetMetadataItem(GDAL_DMD_CREATIONDATATYPES,"Byte UInt16 Int16 Int32 UInt32 Float32 Float64");
        driver->SetMetadataItem(GDAL_DMD_CREATIONOPTIONLIST,
            "<CreationOptionList>\n"
            "   <Option name='COMPRESS' type='string-select' default='PNG' description='PPNG = Palette PNG; DEFLATE = zlib '>\n"
            "       <Value>JPEG</Value>"
            "       <Value>PNG</Value>"
            "       <Value>PPNG</Value>"
            "       <Value>DEFLATE</Value>"
            "       <Value>NONE</Value>"
            "   </Option>\n"
            "   <Option name='INTERLEAVE' type='string-select' default='PIXEL'>\n"
            "       <Value>PIXEL</Value>"
            "       <Value>BAND</Value>"
            "   </Option>\n"
            "   <Option name='QUALITY' type='int' description='best=99, bad=0, default=85'/>\n"
            "   <Option name='BLOCKSIZE' type='int' description='Block size, both x and y, default 512'/>\n"
            "   <Option name='BLOCKXSIZE' type='int' description='Page x size, default=512'/>\n"
            "   <Option name='BLOCKYSIZE' type='int' description='Page y size, default=512'/>\n"
            "   <Option name='NETBYTEORDER' type='boolean' description='Force endian for certain compress options, default is host order'/>\n"
            "</CreationOptionList>\n");

        driver->pfnOpen = GDALMRFDataset::Open;
        driver->pfnIdentify = GDALMRFDataset::Identify;
        driver->pfnUnloadDriver = GDALDeregister_mrf;
        driver->pfnCreateCopy = GDALMRFDataset::CreateCopy;
        GetGDALDriverManager()->RegisterDriver(driver);
    }
}

GDALMRFRasterBand *newMRFRasterBand(GDALMRFDataset *pDS, const ILImage &image, int b, int level)

{
    switch(pDS->current.comp) 
    {
    case IL_PPNG: // Uses the PNG code, just has a palette in each PNG
    case IL_PNG: return new PNG_Band(pDS,image,b,level);
    case IL_JPEG: return new JPEG_Band(pDS,image,b,level);
    case IL_NONE: return new Raw_Band(pDS,image,b,level);
    case IL_ZLIB: return new ZLIB_Band(pDS,image,b,level);
    case IL_TIF: return new TIF_Band(pDS,image,b,level);
    default:
        return NULL;
    }
}

/**
 *\Brief log in a given base 
 */
double logb(double val, double base) {
    return log(val)/log(base);
}

/**
 *\Brief Is logb(val) an integer?
 *
 */

int IsPower(double value,double base) {
    double v=logb(value,base);
    return CPLIsEqual(v,int(v+0.5));
}

/************************************************************************/
/*                           SearchXMLSiblings()                        */
/************************************************************************/

/**
 *\Brief Search for a sibling of the root node with a given name.
 *
 * Searches only the next siblings of the node passed in for the named element or attribute.
 * If the first character of the pszElement is '=', the search includes the psRoot node
 * 
 * @param psRoot the root node to search.  This should be a node of type
 * CXT_Element.  NULL is safe.
 *
 * @param pszElement the name of the element or attribute to search for.
 *
 *
 * @return The first matching node or NULL on failure. 
 */

CPLXMLNode *SearchXMLSiblings( CPLXMLNode *psRoot, const char *pszElement )

{
    if( psRoot == NULL || pszElement == NULL )
        return NULL;

    // If the strings starts with '=', skip it and test the root
    // If not, start testing with the next sibling
    if (pszElement[0]=='=') pszElement++;
    else psRoot=psRoot->psNext;

    for (;psRoot!=NULL;psRoot=psRoot->psNext)
        if ((psRoot->eType == CXT_Element ||
             psRoot->eType == CXT_Attribute)
             && EQUAL(pszElement,psRoot->pszValue))
            return psRoot;

    return NULL;
}

void XMLSetAttributeVal(CPLXMLNode *parent,const char* pszName,
    const double val, const char *frmt)
{
    CPLCreateXMLNode(parent,CXT_Attribute,pszName);
    CPLSetXMLValue(parent,pszName,CPLString().FormatC(val,frmt));
}

CPLXMLNode *XMLSetAttributeVal(CPLXMLNode *parent,
        const char*pszName,const ILSize &sz,const char *frmt)
{
    CPLXMLNode *node=CPLCreateXMLNode(parent,CXT_Element,pszName);
    XMLSetAttributeVal(node,"x",sz.x,frmt);
    XMLSetAttributeVal(node,"y",sz.y,frmt);
    XMLSetAttributeVal(node,"c",sz.c,frmt);
    return node;
}

/**
 *\brief Read a ColorEntry XML node, return a GDALColorEntry structure
 *
 */

GDALColorEntry GetXMLColorEntry(CPLXMLNode *p) {
    GDALColorEntry ce;
    ce.c1= static_cast<int>(getXMLNum(p,"c1",0));
    ce.c2= static_cast<int>(getXMLNum(p,"c2",0));
    ce.c3= static_cast<int>(getXMLNum(p,"c3",0));
    ce.c4= static_cast<int>(getXMLNum(p,"c4",255));
    return ce;
}

// Swap c2 and c3, converting from HSV to the GDAL supported HLS
// Useless since GDAL only handles RGBA
GDALColorEntry HSVSwap(const GDALColorEntry& cein) {
    GDALColorEntry ce(cein);
    ce.c2=ce.c3;
    ce.c3=cein.c2;
    return ce;
}

/**
 *\Brief Verify or make a file that big
 *
 * @return true if size is OK or if extend succedded
 */

int CheckFileSize(VSILFILE *ifp, GIntBig sz, GDALAccess eAccess) {
    GIntBig idxf_sz;
    VSIFSeekL(ifp,0,SEEK_END);
    idxf_sz=VSIFTellL(ifp);
    // Write an empty tile index at the end if the file seems to small
    if (( idxf_sz<sz ) && ( eAccess==GA_Update)) {
        ILIdx tidx={0,0};
        VSIFSeekL(ifp,sz-sizeof(ILIdx),SEEK_SET);
        VSIFWriteL(&tidx,sizeof(tidx),1,ifp);
        VSIFSeekL(ifp,0,SEEK_END);
        idxf_sz=VSIFTellL(ifp);
    }
    return (idxf_sz>=sz);
};
