#include "mrf_insert.h"

using namespace std;

// Size and location from handle

//void getinfo(GDALDatasetH hDS, img_info &img) {
img_info::img_info(GDALDatasetH hDS) {
    double	adfGT[6];
    GDALGetGeoTransform( hDS, adfGT );

    size.x=GDALGetRasterXSize(hDS);
    size.y=GDALGetRasterYSize(hDS);

    bbox.lx=adfGT[0];
    bbox.uy=adfGT[3];
    bbox.ux=adfGT[1]*size.x+bbox.lx;
    bbox.ly=adfGT[5]*size.y+bbox.uy;

    res.x=adfGT[1];
    res.y=adfGT[5];
}


static bool outside_bounds(const Bounds &inside,const Bounds &outside) {
    return (
        (inside.lx < outside.lx && !CPLIsEqual(inside.lx, outside.lx) ) ||
        (inside.ux > outside.ux && !CPLIsEqual(inside.ux, outside.ux) ) ||
        (inside.ly < outside.ly && !CPLIsEqual(inside.ly, outside.ly) ) ||
        (inside.uy > outside.uy && !CPLIsEqual(inside.uy, outside.uy) )
        );
}

// Insert the target in the base level
bool state::patch() {
    if (TargetName.empty())
        return false;

    // These are the same thing, the handle for the C functions, the dataset class for C++
    union {
        GDALDatasetH hDataset;
        GDALDataset *pTDS;
        GDALMRFDataset *pTarg;
    };

    union {
        GDALDatasetH hPatch;
        GDALDataset *pSDS;
    };

    CPLPushErrorHandler( CPLQuietErrorHandler );
    hDataset = GDALOpen( TargetName.c_str(), GA_Update );
    CPLPopErrorHandler();

    if( hDataset == NULL ) {
        CPLError(CE_Failure, CPLE_AppDefined,"Can't open target file %s for update",TargetName.c_str());
        return false;
    }

    try {

        // GetDescription is actually the driver ID, uppercase
        if (!EQUAL(pTDS->GetDriver()->GetDescription(),"MRF")) {
            CPLError(CE_Failure, CPLE_AppDefined,"Target file is not MRF");
            throw 1;
        }

        CPLPushErrorHandler( CPLQuietErrorHandler );
        hPatch= GDALOpen( SourceName.c_str(), GA_ReadOnly );
        CPLPopErrorHandler();

        if (hPatch == NULL ) { 
            CPLError(CE_Failure, CPLE_AppDefined,"Can't open source file %s",SourceName.c_str());
            throw 1;
        };

    } catch (int e) {
        if (e>0) GDALClose(hDataset);
        return false;
    }

    Bounds blocks_bbox;
    Bounds pix_bbox;
    int overview_count=0;
    void *buffer=NULL;

    try {

        img_info in_img(hPatch);
        img_info out_img(hDataset);
        XY factor;
        factor.x=in_img.res.x/out_img.res.x;
        factor.y=in_img.res.x/out_img.res.x;

        if (verbose>0)
            cerr << "Out " << out_img.bbox << endl << "In " << in_img.bbox << endl;

        if (outside_bounds(in_img.bbox, out_img.bbox)) {
            CPLError(CE_Failure,CPLE_AppDefined,"Input patch outside of target");
            throw 2;
        }

        // Get the first band, which always exists, use it to collect some info
        GDALRasterBand *b0=pTDS->GetRasterBand(1);
        int bands=pTDS->GetRasterCount();
        int tsz_x,tsz_y;
        b0->GetBlockSize(&tsz_x,&tsz_y);
        GDALDataType eDataType=b0->GetRasterDataType();
        overview_count=b0->GetOverviewCount();

        int pixel_size=GDALGetDataTypeSize(eDataType)/8; // Bytes per pixel per band
        int line_size=tsz_x*pixel_size; // A line has this many bytes
        int buffer_size=line_size*tsz_y; // A block size in bytes

        // tolerance of 1/1000 of the resolution
        if ( fabs(in_img.res.x - out_img.res.x) * 1000 > out_img.res.x ||
             fabs(in_img.res.y - out_img.res.y) * 1000 > out_img.res.y )
        {
            CPLError(CE_Failure,CPLE_AppDefined,"Source and target resolutions don't match");
            throw 2;
        }

        //
        // Location in target pixels
        pix_bbox.lx=int((in_img.bbox.lx-out_img.bbox.lx)/in_img.res.x+0.5);
        pix_bbox.ux=int((in_img.bbox.ux-out_img.bbox.lx)/in_img.res.x+0.5);
        // uy < ly
        pix_bbox.uy=int((in_img.bbox.uy-out_img.bbox.uy)/in_img.res.y+0.5);
        pix_bbox.ly=int((in_img.bbox.ly-out_img.bbox.uy)/in_img.res.y+0.5);
        
        if (verbose != 0)
            cerr << "Pixel location " << pix_bbox << endl 
                 << "Factor " << factor.x << "," << factor.y << endl;
        
        blocks_bbox.lx=int(pix_bbox.lx/tsz_x+0.5);
        blocks_bbox.ly=int(pix_bbox.ly/tsz_y+0.5);
        blocks_bbox.ux=int(pix_bbox.ux/tsz_x+0.5);
        blocks_bbox.uy=int(pix_bbox.uy/tsz_y+0.5);

        if (verbose != 0)
            cerr << "Blocks location " << blocks_bbox << endl;

        // Build a vector of output bands
        vector<GDALRasterBand *>src_b;
        vector<GDALRasterBand *>dst_b;

        for (int band=1;band<=bands;band++) {
            src_b.push_back(pSDS->GetRasterBand(band));
            dst_b.push_back(pTDS->GetRasterBand(band));
        }

        buffer=CPLMalloc(buffer_size); // Enough for one block

        //
        // Use the innner loop for bands, helps if output is interleaved
        //
        // Using the factor enables scaling of input
        // However, the input coverage still has to be exactly on 
        // ouput block boundaries
        //
        for (int y=blocks_bbox.uy ; y < blocks_bbox.ly; y++) {
            int src_offset_y=tsz_y*(y-blocks_bbox.uy)*factor.y+0.5;
            for (int x=blocks_bbox.lx; x < blocks_bbox.ux; x++) {
                int src_offset_x=tsz_x*(x-blocks_bbox.lx)*factor.x+0.5;
                for (int band=0; band<bands; band++) { // Counting from zero in a vector
                    // cerr << " Y block " << y << " X block " << x << endl;
                    // READ
                    src_b[band]->RasterIO( GF_Read,
                        src_offset_x,src_offset_y, // offset in input image
                        tsz_x, tsz_y, // Size in input image
                        buffer, tsz_x, tsz_y, // Buffer and size in buffer
                        eDataType, // Requested type
                        pixel_size, line_size); // Pixel and line space
                    // WRITE
                    dst_b[band]->RasterIO( GF_Write,
                        x*tsz_x,y*tsz_y, // offset in output image
                        tsz_x, tsz_y, // Size in output image
                        buffer, tsz_x, tsz_y, // Buffer and size in buffer
                        eDataType, // Requested type
                        pixel_size, line_size ); // Pixel and line space
                }
            }
        }

        CPLFree(buffer);
    } catch (int e) {
        if (e>0) GDALClose(hDataset);
        CPLFree(buffer);
        return false;
    }

    // Close input, flush output, then worry about overviews
    GDALClose(hPatch);
    GDALFlushCache(hDataset);

    // Call the patchOverview for the MRF, this recursively
    // patches the overlays
    if (overlays)
        pTarg->PatchOverviews(blocks_bbox.lx,blocks_bbox.uy,
            blocks_bbox.ux-blocks_bbox.lx,
            blocks_bbox.ly-blocks_bbox.uy,0,true);

    // Now for the upper levels
    GDALFlushCache(hDataset);
    GDALClose(hDataset);
    return true;
 }

/************************************************************************/
/*                               Usage()                                */
/************************************************************************/

static int Usage()

{
    printf( "Usage: mrf_insert [-r {nearest,average,gauss,cubic,average_mp,average_magphase,mode}]\n"
            "                  [-q] [--help-general] source_file(s) target_file\n"
            "\n"
            "  -r : choice of resampling method (default: average)\n"
            "  -q : turn off progress display\n" );
    return 1;
}

int main(int nArgc, char **papszArgv) {
    state State;
    int ret=0;

    std::vector<std::string> fnames;

    /* Check that we are running against at least GDAL 1.9 */
    /* Note to developers : if using newer API, please change the requirement */
    if (atoi(GDALVersionInfo("VERSION_NUM")) < 1900)
    {
        fprintf(stderr, "At least, GDAL >= 1.9.0 is required for this version of %s, "
                        "which was compiled against GDAL %s\n", papszArgv[0], GDAL_RELEASE_NAME);
        exit(1);
    }

    GDALAllRegister();

    //
    // Set up a reasonable large cache size, say 256MB
    // CPLSetConfigOption("GDAL_CACHEMAX","256");
    GDALSetCacheMax(256*1024*1024);
    //
    // Done before the CmdLineProcessor has looked at options, so it can be overriden by the user 
    // by setting the GDAL_CACHEMAX env, or passing it as a --config option
    //
    // See http://trac.osgeo.org/gdal/wiki/ConfigOptions
    //

    // Pick up the GDAL options
    nArgc = GDALGeneralCmdLineProcessor( nArgc, &papszArgv, 0 );
    if( nArgc < 1 )
        exit( -nArgc );


/* -------------------------------------------------------------------- */
/*      Parse commandline, set up state                                 */
/* -------------------------------------------------------------------- */


    for( int iArg = 1; iArg < nArgc; iArg++ )
    {
        if( EQUAL(papszArgv[iArg], "--utility_version") )
        {
            printf("%s was compiled against GDAL %s and is running against GDAL %s\n",
                   papszArgv[0], GDAL_RELEASE_NAME, GDALVersionInfo("RELEASE_NAME"));
            return 0;
        }
        else if( EQUAL(papszArgv[iArg],"-r") && iArg < nArgc-1 ) {
            State.setResampling(papszArgv[++iArg]);
            State.setOverlays();
        }
        else if( EQUAL(papszArgv[iArg],"-q") || EQUAL(papszArgv[iArg],"-quiet") )
            State.setProgress(GDALDummyProgress);
        else if( EQUAL(papszArgv[iArg],"-v"))
            State.setDebug(1);
        else fnames.push_back(papszArgv[iArg]);
    }

    // Need at least a target and a source
    if (fnames.size()>0)
    {
        State.setTarget(fnames[fnames.size()-1]);
        fnames.pop_back();
    }

    if(fnames.empty()) return Usage();
    
    try {

        // Each input file in sequence, as they were passed as arguments
        for (int i=0; i < fnames.size() ; i++) {
            State.setSource(fnames[i]);

            // false return means error was detected and printed, just exit
            if (!State.patch()) 
                throw 2;

        }

    } // Try, all execution
    catch (int err_ret) {
        ret=err_ret;
    };
    
    // General cleanup
    CSLDestroy( papszArgv );
    GDALDestroyDriverManager();
    return ret;
}