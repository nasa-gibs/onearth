/*
* Copyright (c) 2002-2015, California Institute of Technology.
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



// oe_create_cache_config.cpp : Defines the entry point for the console application.
// version 1.2.2

// For windows, this file should exist but be empty on Linux
#include "stdafx.h"
#include "cache.h"
#include <algorithm>
#include <dirent.h>

#if defined(LINUX)
#include "oe_create_cache_config.h"
#endif

using namespace std;

void PrintUsage() {
    fprintf(stdout,"OnEarth cache configuration tool\n"
        "oe_create_cache_config [MODE] [OPTION]... [INPUT] [OUTPUT]\n"
        "   MODE can be one of:\n"
        "       h : Help (default)\n"
        "       c : Configuration\n"
        "       p : TiledWMSPattern\n\n"
        "\n\n"
        "   Options:\n\n"
        "   x : With mode c, generate XML\n"
        "   b : With mode c, generate binary\n"
        "       x and b are mutually exclusive\n"
        "\n"
        "   INPUT and OUTPUT default to stdin and stdout respectively\n"
        "\n\n"
        "  Options in the MRF header:\n"
        "  <Raster>\n"
        "       <Size> - x, y [1,1]\n"
        "       <PageSize> - x, y and c [512,512,1]\n"
        "       <Orientation> - TL or BL, only TL works\n"
        "       <Compression> - [PNG]\n"
        "  <Rsets>\n"
        "       checks model=uniform attribute for levels\n"
        "       checks scale=N attribute for powers of overviews\n"
        "       <IndexFileName> Defaults to mrf basename + .idx\n"
        "       <DataFileName>  Default to mrf basename + compression dependent extension\n"
        "  <GeoTags>\n"
        "       <BoundingBox> minx,miny,maxx,maxy [-180,-90,180,90]\n"
        "  <TWMS>\n"
        "       <Levels> Defaults to all\n"
        "       <EmptyInfo> size,offset [0,0]\n"
        "       <Pattern> One or more, enclose in <!CDATA[[ ]]>, the first one is used for pattern generation\n"
        "       <Time> One or more, ISO 8601 time range for the product layer\n"
        );
}

inline long long pcount(long long tsz, long long psz) {return (tsz-1)/psz+1;}

/* Reads stdin to a string.  Disregard the EOL markers, works fine for XML */
// Could this be done using rdbuf?
void ReadSTDIN(CPLString &s) {
    string input_line;
    while (cin) {
        getline(cin,input_line);
        s.append(input_line);
    }
}


CPLXMLNode *XMLParseFile(const char *ifname) {
    if (strcmp(ifname,"-"))
        return CPLParseXMLFile(ifname);
    else {
        CPLString s;
        ReadSTDIN(s);
        return CPLParseXMLString(s.c_str());
    }
}


// Keep these copy safe
struct server_config {
    int count;
    int total_size;
    int strings_size;
    vector<WMSlevel> levels;
    vector<WMSCache> caches;
    vector<string>  strings;
    vector<int>  s_off;
    int string_add(string &s);
    int string_insert(string &s);
    void dump(ostream &ofname);
};

class mrf_data {
public:
    bool valid;
    CPLString pattern;
    vector<CPLString> patt;
    int levels,sig;
    int scale;
    int whole_size_x,whole_size_y,tile_size_x,tile_size_y;
    int orientation;
    int bands;
    int zlevels;
    double cov_lx,cov_ly,cov_ux,cov_uy;
    long long int empty_size,empty_offset;
    string h_format;
    string data_fname,idx_fname,zidx_fname;
    vector<string> time_period;
    mrf_data(const char *ifname);
    void mrf2cache(ostream &out);
    void mrf2cachex(ostream &ofname, CPLXMLNode &cache);
    void mrf2cacheb(server_config &cfg, bool verbose=false);
    void mrf2patterns(const char *ofname);
};

/*\brief add a string to the list of strings
*/
int server_config::string_add(string &s) {
    s_off.push_back(strings_size);
    strings.push_back(s);
    // Keep track of how many chars we have, including the null at the end
    strings_size+=s.size()+1;
    return s_off[s_off.size()-1];
}

/*\brief add a string, only if it doesn't exist already
*/
int server_config::string_insert(string &s) {
    int ret=0;
    for (int i=0;i<strings.size();i++) {
        if (strings[i]==s) {
            ret=s_off[i];
            break;
        }
    }
    if (0!=ret) return ret;
    else return string_add(s);
}

/*\brief generates the binary configuration file, including adjusting the necessary pointers
*/
void server_config::dump(ostream &ofname) {
    total_size+=sizeof(Caches)+strings_size;
    // size and count in the first two ints

    //.write method requires pointer value.
    //typecasting into char array pointer
    ofname.write((char *)&total_size,sizeof(total_size));
    ofname.write((char *)&count,sizeof(count));

    // String offset from base pointer
    int string_offset= sizeof(Caches) + count*sizeof(WMSCache) + levels.size()*sizeof(WMSlevel);

    // Adjust the offsets and write each cache in sequence
    for (int i=0;i<count;i++) {
        caches[i].pattern+=string_offset;
        caches[i].prefix+=string_offset;
        caches[i].time_period+=string_offset;
        caches[i].zidxfname+=string_offset;
        // The levelt_offset is relative to each particular cache
        caches[i].levelt_offset+=sizeof(WMSCache)*(count-i);
        ofname.write((char *)&caches[i],sizeof(WMSCache));
    }

    // Adjust the pointers and write each level in sequence
    for (int i=0;i<levels.size();i++) {
        levels[i].dfname+=string_offset;
        levels[i].ifname+=string_offset;
        ofname.write((char *)&levels[i],sizeof(WMSlevel));
    }

    for (int i=0;i<strings.size();i++)
        ofname.write(strings[i].c_str(),strings[i].size()+1);
}

/*\brief add the current mrf to the server config
*
*
*/

void mrf_data::mrf2cacheb(server_config &cfg, bool verbose) {
	if (!valid) return;
    if (verbose)  cerr << "Cache # " << cfg.count << endl
        << "Matches " << patt[0] << endl 
        << "Level count " << levels << endl;


    WMSCache c={0};

    // It is essential that the patterns get added and not inserted,
    // since they have to be sequential
    // There is always at least one pattern defined, the one we point to
    c.num_patterns=1;
    c.pattern+=cfg.string_add(patt[0]);
    for (int i=1;i<patt.size();i++) {
        cfg.string_add(patt[i]);
        c.num_patterns++;
    }

    c.levels=levels;
    // levelt is the offset between the cache pointer and the first level belonging to this cache
    // this is just the later part, we'll add the cache component when we dump the configuration
    c.levelt_offset = sizeof(WMSlevel)*cfg.levels.size();
    // This is the offset within strings, will be adjusted later
    c.prefix += cfg.string_insert( h_format.append("\n\n") );

    c.zlevels=zlevels;
    c.zidxfname += cfg.string_insert(zidx_fname);

    c.orientation=orientation;
    c.signature=sig;

    c.num_periods = 1;
    c.time_period += cfg.string_add(time_period[time_period.size()-1]);
    for (int i=time_period.size()-2;i>=0;i--) {
        cfg.string_add(time_period[i]);
        c.num_periods++;
    }

    long long offset=0;
    // Use a zero levels mrf for blocking access
    for (int i=0;i<levels;i++) {
        WMSlevel level={0};

        level.psizex=tile_size_x;
        level.psizey=tile_size_y;
        level.X0=cov_lx;
        level.X1=cov_ux;
        level.Y0=cov_ly;
        level.Y1=cov_uy;
        level.empty_record.offset=empty_offset;
        level.empty_record.size  =empty_size;
        level.levelx=(cov_ux - cov_lx) * (tile_size_x * pow(scale,i)) / whole_size_x;
        level.levely=(cov_uy - cov_ly) * (tile_size_y * pow(scale,i)) / whole_size_y;
        level.xcount=(whole_size_x - 1) / (tile_size_x * pow(scale,i)) + 1;
        level.ycount=(whole_size_y - 1) / (tile_size_y * pow(scale,i)) + 1;
        level.index_add=offset;
        // These two are string pointers, will be adjusted later
        level.dfname+=cfg.string_insert(data_fname);
        level.ifname+=cfg.string_insert(idx_fname);

        cfg.levels.push_back(level);
        cfg.total_size+=sizeof(WMSlevel);

        // Add the size of the index at this level to the next level offset
        if (zlevels > 0) {
        	offset+=static_cast<long long>(16)* level.xcount * level.ycount * zlevels;
        } else {
        	offset+=static_cast<long long>(16)* level.xcount * level.ycount;
        }
    }

    cfg.caches.push_back(c);
    cfg.count++;
    cfg.total_size+=sizeof(WMSCache);

    if (verbose) cerr << "Total size went to " << cfg.total_size << endl;
}

mrf_data::mrf_data(const char *ifname) :valid(false) {

    CPLXMLNode *input=XMLParseFile(ifname);

    try {
        // List of signatures for different compression schemes
        // The tiff is not quite right, it depends on endianess, this one is for big endian
        const int sig_jpg=-2555936, sig_png=-1991255785, tif_sig=1296891946;
        if (!input) throw CPLString().Printf("Can't read input %s", ifname);
        CPLXMLNode *raster=CPLGetXMLNode(input,"Raster");
        if (!raster) throw CPLString().Printf("Can't find the Raster node in %s", ifname);
        orientation=EQUAL(CPLGetXMLValue(raster,"Orientation","TL"),"TL")?0:1;

        stringstream(CPLGetXMLValue(raster,"Size.x","1")) >> whole_size_x;
        stringstream(CPLGetXMLValue(raster,"Size.y","1")) >> whole_size_y;
        stringstream(CPLGetXMLValue(raster,"Size.z","0")) >> zlevels;
        stringstream(CPLGetXMLValue(raster,"PageSize.x","512")) >> tile_size_x;
        stringstream(CPLGetXMLValue(raster,"PageSize.y","512")) >> tile_size_y;
        stringstream(CPLGetXMLValue(raster,"PageSize.c","1")) >> bands;

        string compression(CPLGetXMLValue(raster,"Compression","PNG"));
        // A guess for the data file extension
        string dat_ext(".unknown_ext");
        if (compression=="PNG") {
            dat_ext=".ppg";
            sig=sig_png;
            h_format="Content-type: image/png";
        } else if (compression=="JPEG") {
            dat_ext=".pjg";
            sig=sig_jpg;
            h_format="Content-type: image/jpeg";
        } else if (compression=="TIF") {
            dat_ext=".ptf";
            sig=tif_sig;
            h_format="Content-type: image/tiff";
        } else if (compression=="LERC") {
            dat_ext=".lrc";
            sig=0;
            h_format="Content-type: image/lerc";
        } else if (compression=="PBF") {
            dat_ext=".pvt";
            sig=0;
            h_format="Content-type: application/x-protobuf;type=mapbox-vector";
        } else if (compression=="MVT") {
            dat_ext=".pvt";
            sig=0;
            h_format="Content-type: application/vnd.mapbox-vector-tile";
        }

        idx_fname=CPLGetXMLValue(input,"Rsets.IndexFileName",ifname);
        if (idx_fname==string(ifname)&&idx_fname.size()>4)
            idx_fname.replace(idx_fname.size()-4,4,".idx");

        data_fname=CPLGetXMLValue(input,"Rsets.DataFileName",ifname);
        if (data_fname==string(ifname)&&data_fname.size()>4)
            data_fname.replace(data_fname.size()-4,4,dat_ext);

        if (zlevels > 0) {
			zidx_fname=CPLGetXMLValue(input,"Rsets.ZIndexFileName",ifname);
			if (zidx_fname==string(ifname)&&zidx_fname.size()>4)
				zidx_fname.replace(zidx_fname.size()-4,4,".zdb");
        }

        if (idx_fname=="-" || data_fname=="-")
            throw (CPLString().Printf("Need data and index file names, under <Rsets><IndexFileName> or <Rsets><DataFileName>"));
        if (string::npos!=data_fname.find(".unknown_ext"))
            throw (CPLString().Printf("Can't guess extension for data file compressed as %s, please provide <Rsets><DataFilename>",
            compression.c_str()));

        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.minx","-180")) >> cov_lx;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.maxx","180")) >> cov_ux;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.miny","-90")) >> cov_ly;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.maxy","90")) >> cov_uy;

        // Let the user set the powers between overviews
        if (CPLGetXMLNode(input,"Rsets.scale"))
            stringstream(CPLGetXMLValue(input,"Rsets.scale","2")) >> scale;
        else
            scale = 2;

        // Figure out the number of levels
        int szx=whole_size_x, szy=whole_size_y;

        // If the mode is uniform and there is no override, calculate levels, otherwise 1
        levels=1;
        if (EQUAL(CPLGetXMLValue(input,"Rsets.model",""),"uniform")) {
            while (1<pcount(szx,tile_size_x)*pcount(szy,tile_size_y)) {
                // Next level, round size up
                levels++;
                szx = (szx-1)/scale + 1;
                szy = (szy-1)/scale + 1;
            }
        };

        // Let the user override the number of levels
        if (CPLGetXMLNode(input,"TWMS.Levels"))
            stringstream(CPLGetXMLValue(input,"TWMS.Levels","-1")) >> levels;

        stringstream(CPLGetXMLValue(input,"TWMS.EmptyInfo.size","0")) >> empty_size;
        stringstream(CPLGetXMLValue(input,"TWMS.EmptyInfo.offset","0")) >> empty_offset;

        CPLXMLNode *pat=CPLGetXMLNode(input,"TWMS.Pattern");

        if (!pat) throw CPLString().Printf(
            "Can't find <TWMS><Pattern> in %s",ifname);

        while (pat!=0) {
            patt.push_back(CPLGetXMLValue(pat,0,0));
            pat=CPLGetXMLNode(pat->psNext,"=Pattern");
        }

        CPLXMLNode *time_node=CPLGetXMLNode(input,"TWMS.Time");
        if (!time_node) // add default value
        	time_period.push_back(CPLGetXMLValue(time_node,0,"1970-01-01/2099-12-31/P1D"));
        while (time_node!=0) {
        	time_period.push_back(CPLGetXMLValue(time_node,0,"1970-01-01/2099-12-31/P1D"));
        	time_node=CPLGetXMLNode(time_node->psNext,"=Time");
        }
        sort(time_period.begin(), time_period.end());

    }
    catch (CPLString message) {
        CPLDestroyXMLNode(input);
        cerr << "ERROR: " << message << endl;
        return;
    }
    valid=true;
    return;
}

void mrf_data::mrf2cache(ostream &out) {
    if (!valid) return;

    for (int i=0; i<patt.size()-1; i++)
        out << "+" << patt[i] << endl;

    out << patt[patt.size()-1] << endl;
    out << levels << endl << h_format << endl << sig << endl << orientation << endl; 
    out << zlevels << endl;
    if (zlevels>0) {
        out << zidx_fname << endl;
    };
    out << setprecision(16) ;

    long long offset=0;
    for (int i=0;i<levels;i++) {
        out << tile_size_x << "," << tile_size_y << " // Page size for this level\n";
        out << cov_lx << "," << cov_ly << "," << cov_ux << "," << cov_uy << " // Coverage area\n";
        out << (cov_ux - cov_lx) * (tile_size_x * pow(scale,i)) / whole_size_x << "," <<
            (cov_uy - cov_ly) * (tile_size_y * pow(scale,i)) / whole_size_y << " // Tile size \n";
        out << data_fname << endl;
        out << idx_fname << " " << offset << endl;
        offset+=static_cast<long long>(16)*((whole_size_x-1)/(tile_size_x * pow(scale,i)) +1) *
            ((whole_size_y-1)/(tile_size_y * pow(scale,i)) +1);
        out << empty_offset << "," << empty_size << endl;
    }

}

const char *FMT="%.16g";

void mrf_data::mrf2cachex(ostream &out, CPLXMLNode &cache) {
    CPLXMLNode *layer=CPLCreateXMLNode(&cache,CXT_Element,"Layer");

    CPLXMLNode *plist=CPLCreateXMLNode(layer,CXT_Element,"Patterns");
    for (vector<CPLString>::iterator i=patt.begin(); i!=patt.end(); i++)
        CPLCreateXMLNode(CPLCreateXMLNode(plist,CXT_Element,"Pattern"),
        CXT_Literal,CPLString().Printf("<![CDATA[%s]]>",i->c_str()).c_str());

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"HTMLHeader"),
        CXT_Text,CPLString().Printf("%d",levels));

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"HTMLFormat"),
        CXT_Text,h_format.c_str());

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"Signature"),
        CXT_Text,CPLString().Printf("%d",sig));

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"BinaryOrientation"),
        CXT_Text,CPLString().Printf("%d",orientation));

    CPLXMLNode *LayerSize=CPLCreateXMLNode(layer,CXT_Element,"LayerSize");
    CPLCreateXMLNode(CPLCreateXMLNode(LayerSize,CXT_Attribute,"x"),
        CXT_Text,CPLString().Printf("%d",whole_size_x).c_str());
    CPLCreateXMLNode(CPLCreateXMLNode(LayerSize,CXT_Attribute,"y"),
        CXT_Text,CPLString().Printf("%d",whole_size_y).c_str());

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"Bands"),
        CXT_Text,CPLString().Printf("%d",bands));

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"Scale"),
        CXT_Text,CPLString().Printf("%d",scale));

    CPLXMLNode *tlist=CPLCreateXMLNode(layer,CXT_Element,"TimePeriods");
    for (vector<string>::iterator i=time_period.begin(); i!=time_period.end(); i++)
        CPLCreateXMLNode(CPLCreateXMLNode(tlist,CXT_Element,"TimePeriod"),
        CXT_Text,CPLString().Printf("%s",i->c_str()));

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"Levels"),
        CXT_Text,CPLString().Printf("%d",levels));

    CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"ZLevels"),
        CXT_Text,CPLString().Printf("%d",zlevels));

    if (zlevels > 0) {
        CPLCreateXMLNode(CPLCreateXMLNode(layer,CXT_Element,"ZIndexFileName"),CXT_Text,zidx_fname.c_str());
    }

    long long int offset=0;
    for (int i=0;i<levels;i++) {
        CPLXMLNode *level=CPLCreateXMLNode(layer,CXT_Element,"Level");
        CPLXMLNode *TileSize=CPLCreateXMLNode(level,CXT_Element,"TileSize");
        CPLCreateXMLNode(CPLCreateXMLNode(TileSize,CXT_Attribute,"x"),
            CXT_Text,CPLString().Printf("%d",tile_size_x).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(TileSize,CXT_Attribute,"y"),
            CXT_Text,CPLString().Printf("%d",tile_size_y).c_str());
        CPLXMLNode *Bbox=CPLCreateXMLNode(level,CXT_Element,"BoundingBox");
        CPLCreateXMLNode(CPLCreateXMLNode(Bbox,CXT_Attribute,"xmin"),
            CXT_Text,CPLString().FormatC(cov_lx,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(Bbox,CXT_Attribute,"ymin"),
            CXT_Text,CPLString().FormatC(cov_ly,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(Bbox,CXT_Attribute,"xmax"),
            CXT_Text,CPLString().FormatC(cov_ux,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(Bbox,CXT_Attribute,"ymax"),
            CXT_Text,CPLString().FormatC(cov_uy,FMT).c_str());
        CPLXMLNode *TileRes=CPLCreateXMLNode(level,CXT_Element,"TileResolution");
        CPLCreateXMLNode(CPLCreateXMLNode(TileRes,CXT_Attribute,"x"),
            CXT_Text,CPLString().FormatC((cov_ux - cov_lx) * (tile_size_x * pow(scale,i)) / whole_size_x,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(TileRes,CXT_Attribute,"y"),
            CXT_Text,CPLString().FormatC((cov_uy - cov_ly) * (tile_size_y * pow(scale,i)) / whole_size_y,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"DataFileName"),CXT_Text,data_fname.c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"IndexFileName"),CXT_Text,idx_fname.c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"IndexOffset"),
            CXT_Text,CPLString().Printf("%lld",offset).c_str());
        offset+=static_cast<long long>(16)*((whole_size_x-1)/(tile_size_x * pow(scale,i)) +1) *
            ((whole_size_y-1)/(tile_size_y * pow(scale,i)) +1);

        CPLXMLNode *empty=CPLCreateXMLNode(level,CXT_Element,"EmptyInfo");
        CPLCreateXMLNode(CPLCreateXMLNode(empty,CXT_Attribute,"size"),
            CXT_Text,CPLString().Printf("%lld",empty_size));
        CPLCreateXMLNode(CPLCreateXMLNode(empty,CXT_Attribute,"offset"),
            CXT_Text,CPLString().Printf("%lld",empty_offset));
    }
}

// Generate XML for patterns.
void mrf_data::mrf2patterns(const char *ofname) {
    if (!valid) return;

    CPLXMLNode *GTS_patterns;
    CPLXMLNode **ppn=&GTS_patterns;
    // Resolutions, in map units per tile
    double resx=(cov_ux-cov_lx)/whole_size_x*tile_size_x;
    double resy=(cov_uy-cov_ly)/whole_size_y*tile_size_y;
    for (int i=0;i<levels;i++) {
        *ppn=CPLCreateXMLNode(0,CXT_Element,"TilePattern");
        // Build the string from tokens, looking for the bbox
        bool tset=false;
        char **papszTokens=CSLTokenizeString2(patt[0],"&",FALSE);
        CPLString pat("<![CDATA[");
        for (char **pptoken=papszTokens; *pptoken!=0 ; pptoken++, pat+='&') {
            if (EQUALN("bbox=",*pptoken,5)) {
                double local_xM=cov_lx+resx;
                double local_ym=cov_uy-resy;
                // Copy the bbox and equal then insert the proper values
                pat.append(*pptoken,5);
                pat+=CPLString().FormatC(cov_lx,FMT)+","
                    +CPLString().FormatC(local_ym,FMT)+","
                    +CPLString().FormatC(local_xM,FMT)+","
                    +CPLString().FormatC(cov_uy,FMT);
            } else if (EQUALN("time=",*pptoken,5)) {
                tset=true;
                pat.append(*pptoken,5);
                pat.append("${time}");
            } else {
                pat.append(*pptoken);
            }
        }
        CSLDestroy(papszTokens);

        if (tset&&patt.size()>1) {
            // Replace the last ampersand with a space
            tset=false;
            pat.replace(pat.size()-1,1," ");
            papszTokens=CSLTokenizeString2(patt[1],"&",FALSE);
            for (char **pptoken=papszTokens; *pptoken!=0 ; pptoken++, pat+='&') {
                if (EQUALN("bbox=",*pptoken,5)) {
                    double local_xM=cov_lx+resx;
                    double local_ym=cov_uy-resy;
                    // Copy the bbox and equal then insert the proper values
                    pat.append(*pptoken,5);
                    pat+=CPLString().FormatC(cov_lx,FMT)+","
                        +CPLString().FormatC(local_ym,FMT)+","
                        +CPLString().FormatC(local_xM,FMT)+","
                        +CPLString().FormatC(cov_uy,FMT);
                } else if (EQUALN("time=",*pptoken,5)) {
                    tset=true;
                    pat.append(*pptoken,5);
                    pat.append("${time}");
                } else {
                    pat.append(*pptoken);
                }
            }
            CSLDestroy(papszTokens);
        }

        // Replace the last ampersand with double square brackets
        pat.replace(pat.size()-1,1,"]]>");

        // This is precise, double float math
        resx*=2;resy*=2;

        CPLCreateXMLNode(*ppn,CXT_Literal,pat);
        ppn=&((*ppn)->psNext);
    }
    if (EQUAL(ofname,"-")) {
        char *text=CPLSerializeXMLTree(GTS_patterns);
        cout << text;
        CPLFree(text);
    } else
        CPLSerializeXMLTreeToFile(GTS_patterns,ofname);
    CPLDestroyXMLNode(GTS_patterns);
}

typedef enum {CONF, PATTERN} md;

struct opts{
    string ofname;
    bool xml;
    bool binary;
    md mode;
    bool directory;
};

void mrf2cache(vector<mrf_data> &in, opts &o) {
    ostream *out;
    ofstream of;
    //If no output file, stdout
    if (EQUAL(o.ofname.c_str(),"-")) out=&cout;
    else {
        //Open file
        of.open(o.ofname.c_str());
        if (!of.is_open()) {
            cerr << "Can't open output file " << o.ofname << endl;
            exit(1);
        }
        out=&of;
    }

    if (o.xml) {
    	CPLXMLNode *cache=CPLCreateXMLNode(0,CXT_Element,"Cache");
        for (vector<mrf_data>::iterator i=in.begin();i!=in.end();i++) {
            i->mrf2cachex(*out, *cache);
        }
        char *text=CPLSerializeXMLTree(cache);
        *out << text;
        CPLFree(text);
        CPLDestroyXMLNode(cache);
    } else if (o.binary) {
        server_config cfg={0};
        for (vector<mrf_data>::iterator i=in.begin();i!=in.end();i++)
            i->mrf2cacheb(cfg);
        cfg.dump(*out);
    } else {
        // Print the number of layers, then all the strings in sequence
        *out << in.size() << endl;
        for (vector<mrf_data>::iterator i=in.begin();i!=in.end();i++)
            i->mrf2cache(*out);
    }
}

int main(int argc, char* argv[])
{
    opts o={"-",false,CONF};

    int opt;

    while ((opt=getopt(argc, argv,"pchxbd")) != -1) {
        switch(opt) {
        case 'p' :
            o.mode=PATTERN;
            break;
        case 'c' :
            o.mode=CONF;
            break;
        case 'd' :
            o.directory=true;
            break;
        case 'x' :
            o.binary=false;
            o.xml=true;
            break;
        case 'b' : 
            o.xml=false;
            o.binary=true;
            break;
        case 'h' :
        case '?' :
            PrintUsage();
            exit(1);
        }
    };

    if (argc==1) {
        PrintUsage();
        exit(1);
    }

    vector<mrf_data> input;
    if (optind==argc)
        input.push_back(mrf_data("-"));
    if (o.directory==true) {
        DIR* dirFile = opendir(argv[optind]);
        if (dirFile)
        {
           struct dirent* hFile;
           while (( hFile = readdir(dirFile)) != NULL )
           {
              if ( !strcmp( hFile->d_name, "."  )) continue;
              if ( !strcmp( hFile->d_name, ".." )) continue;
              if ( strstr( hFile->d_name, ".mrf" )) {
                 // printf( "Using: %s\n", hFile->d_name);
                 char filepath[strlen(argv[optind])+strlen(hFile->d_name)+2];
                 *filepath = '\0';
                 strcpy(filepath,argv[optind]);
                 strcat(filepath,"/");
                 input.push_back(mrf_data(strcat(filepath,hFile->d_name)));
              }
           }
           closedir(dirFile);
        }
        optind++;
    } else {
		// Single input is input file name
		if (optind==argc-1)
			input.push_back(mrf_data(argv[optind++]));
		while (optind<argc-1)
			input.push_back(mrf_data(argv[optind++]));
    }
    if (optind<argc)
        o.ofname=argv[optind++];

    if (o.mode==PATTERN) {
        if (input.size()!=1) {
            cerr << "Only one input allowed for -p option\n";
            PrintUsage();
            exit(1);
        }
        input[0].mrf2patterns(o.ofname.c_str());
        return 0;
    }

    // This handles everything, but we need another flag, to directly produce binary config
    mrf2cache(input,o);

    return 0;
}
