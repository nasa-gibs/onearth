


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



// twms_tool.cpp : Defines the entry point for the console application.
//

// For windows, this file should exist but be empty on Linux
#include "stdafx.h"
#include "cache.h"

#if defined(LINUX)
#include "twms_tool.h"
#endif

using namespace std;

void PrintUsage() {
    fprintf(stdout,"TWMS configuration tool\n"
        "twms_tool [MODE] [OPTION]... [INPUT] [OUTPUT]\n"
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
        "       <IndexFileName> Defaults to mrf basename + .idx\n"
        "       <DataFileName>  Default to mrf basename + compression dependent extension\n"
        "  <GeoTags>\n"
        "       <BoundingBox> minx,miny,maxx,maxy [-180,-90,180,90]\n"
        "  <TWMS>\n"
        "       <Levels> Defaults to all\n"
        "       <EmptyInfo> size,offset [0,0]\n"
        "       <Pattern> One or more, enclose in <!CDATA[[ ]]>, the first one is used for pattern generation\n"
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
    int whole_size_x,whole_size_y,tile_size_x,tile_size_y;
    int orientation;
    int bands;
    double cov_lx,cov_ly,cov_ux,cov_uy;
    long long int empty_size,empty_offset;
    string h_format;
    string data_fname,idx_fname;
    mrf_data(const char *ifname);
    void mrf2cache(ostream &out);
    void mrf2cachex(ostream &ofname);
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
    ofname.write((char *)&total_size,sizeof(total_size));
    ofname.write((char *)&count,sizeof(count));

    // String offset from base pointer
    int string_offset= sizeof(Caches) + count*sizeof(WMSCache) + levels.size()*sizeof(WMSlevel);

    // Adjust the offsets and write each cache in sequence
    for (int i=0;i<count;i++) {
        caches[i].pattern+=string_offset;
        caches[i].prefix+=string_offset;
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

    c.orientation=orientation;
    c.signature=sig;

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
        level.levelx=(cov_ux - cov_lx) * (tile_size_x << i) / whole_size_x;
        level.levely=(cov_uy - cov_ly) * (tile_size_y << i) / whole_size_y;
        level.xcount=(whole_size_x - 1) / (tile_size_x << i) + 1;
        level.ycount=(whole_size_y - 1) / (tile_size_y << i) + 1;
        level.index_add=offset;
        // These two are string pointers, will be adjusted later
        level.dfname+=cfg.string_insert(data_fname);
        level.ifname+=cfg.string_insert(idx_fname);
        cfg.levels.push_back(level);
        cfg.total_size+=sizeof(WMSlevel);

        // Add the size of the index at this level to the next level offset
        offset+=static_cast<long long>(16)* level.xcount * level.ycount;
    }

    cfg.caches.push_back(c);
    cfg.count++;
    cfg.total_size+=sizeof(WMSCache);

    if (verbose) cerr << "Total size went to " << cfg.total_size << endl;
}

mrf_data::mrf_data(const char *ifname) :valid(false) {

    CPLXMLNode *input=XMLParseFile(ifname);
    if (!input) return;

    try {
        // List of signatures for different compression schemes
        // The tiff is not quite right, it depends on endianess, this one is for big endian
        const int sig_jpg=-2555936, sig_png=-1991255785, tif_sig=1296891946;
        if (!input) throw("Can't read input");
        CPLXMLNode *raster=CPLGetXMLNode(input,"Raster");
        if (!raster) throw("Can't find the Raster node");
        orientation=EQUAL(CPLGetXMLValue(raster,"Orientation","TL"),"TL")?0:1;

        stringstream(CPLGetXMLValue(raster,"Size.x","1")) >> whole_size_x;
        stringstream(CPLGetXMLValue(raster,"Size.y","1")) >> whole_size_y;
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
        } else if (compression=="TIFF") {
            dat_ext=".ptf";
            sig=tif_sig;
            h_format="Content-type: image/tiff";
        }

        idx_fname=CPLGetXMLValue(input,"Rsets.IndexFileName",ifname);
        if (idx_fname==string(ifname)&&idx_fname.size()>4)
            idx_fname.replace(idx_fname.size()-4,4,".idx");

        data_fname=CPLGetXMLValue(input,"Rsets.DataFileName",ifname);
        if (data_fname==string(ifname)&&data_fname.size()>4)
            data_fname.replace(data_fname.size()-4,4,dat_ext);
        if (idx_fname=="-" || data_fname=="-")
            throw (CPLString("Need data and index file names, under <Rsets><IndexFileName> or <Rsets><DataFileName>"));
        if (string::npos!=data_fname.find(".unknown_ext"))
            throw (CPLString().Printf("Can't guess extension for data file compressed as %s, please provide <Rsets><DataFilename>",
            compression.c_str()));

        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.minx","-180")) >> cov_lx;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.maxx","180")) >> cov_ux;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.miny","-90")) >> cov_ly;
        stringstream(CPLGetXMLValue(input,"GeoTags.BoundingBox.maxy","90")) >> cov_uy;

        // Figure out the number of levels
        int szx=whole_size_x, szy=whole_size_y;

        // If the mode is uniform and there is no override, calculate levels, otherwise 1
        levels=1;
        if (EQUAL(CPLGetXMLValue(input,"Rsets.model",""),"uniform")) {
            while (1<pcount(szx,tile_size_x)*pcount(szy,tile_size_y)) {
                // Next level, round size up
                levels++;
                szx=(szx>>1)+(szx&1); // same as szx/2+szx%2, divide by 2 with round up
                szy=(szy>>1)+(szy&1);
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
    }
    catch (CPLString message) {
        CPLDestroyXMLNode(input);
        cerr << "Error :" << message << endl;
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
    out << setprecision(16) ;

    long long offset=0;
    for (int i=0;i<levels;i++) {
        out << tile_size_x << "," << tile_size_y << " // Page size for this level\n";
        out << cov_lx << "," << cov_ly << "," << cov_ux << "," << cov_uy << " // Coverage area\n";
        out << (cov_ux - cov_lx) * (tile_size_x << i) / whole_size_x << "," <<
            (cov_uy - cov_ly) * (tile_size_y << i) / whole_size_y << " // Tile size \n";
        out << data_fname << endl;
        out << idx_fname << " " << offset << endl;
        offset+=static_cast<long long>(16)*((whole_size_x-1)/(tile_size_x << i) +1) *
            ((whole_size_y-1)/(tile_size_y << i) +1);
        out << empty_offset << "," << empty_size << endl;
    }

}

const char *FMT="%.16g";

void mrf_data::mrf2cachex(ostream &out) {
    CPLXMLNode *cache=CPLCreateXMLNode(0,CXT_Element,"TWMS_Cache");

    CPLXMLNode *plist=CPLCreateXMLNode(cache,CXT_Element,"Patterns");
    for (vector<CPLString>::iterator i=patt.begin(); i!=patt.end(); i++)
        CPLCreateXMLNode(CPLCreateXMLNode(plist,CXT_Element,"pattern"),
        CXT_Literal,CPLString().Printf("<![CDATA[%s]]>",i->c_str()).c_str());

    CPLCreateXMLNode(CPLCreateXMLNode(cache,CXT_Element,"Levels"),
        CXT_Text,CPLString().Printf("%d",levels));

    CPLCreateXMLNode(CPLCreateXMLNode(cache,CXT_Element,"HTMLHeader"),
        CXT_Text,CPLString().Printf("%d",levels));

    CPLCreateXMLNode(CPLCreateXMLNode(cache,CXT_Element,"Magic"),
        CXT_Text,CPLString().Printf("%d",sig));

    CPLCreateXMLNode(CPLCreateXMLNode(cache,CXT_Element,"BinaryOrientation"),
        CXT_Text,CPLString().Printf("%d",orientation));

    long long int offset=0;
    for (int i=0;i<levels;i++) {
        CPLXMLNode *level=CPLCreateXMLNode(cache,CXT_Element,"Level");
        CPLXMLNode *Size=CPLCreateXMLNode(level,CXT_Element,"TileSize");
        CPLCreateXMLNode(CPLCreateXMLNode(Size,CXT_Attribute,"x"),
            CXT_Text,CPLString().Printf("%d",tile_size_x).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(Size,CXT_Attribute,"y"),
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
            CXT_Text,CPLString().FormatC((cov_ux - cov_lx) * (tile_size_x << i) / whole_size_x,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(TileRes,CXT_Attribute,"y"),
            CXT_Text,CPLString().FormatC((cov_uy - cov_ly) * (tile_size_y << i) / whole_size_y,FMT).c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"DataFileName"),CXT_Text,data_fname.c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"IndexFileName"),CXT_Text,idx_fname.c_str());
        CPLCreateXMLNode(CPLCreateXMLNode(level,CXT_Element,"IndexOffset"),
            CXT_Text,CPLString().Printf("%lld",offset).c_str());
        offset+=static_cast<long long>(16)*((whole_size_x-1)/(tile_size_x << i) +1) *
            ((whole_size_y-1)/(tile_size_y << i) +1);

        CPLXMLNode *empty=CPLCreateXMLNode(level,CXT_Element,"EmptyInfo");
        CPLCreateXMLNode(CPLCreateXMLNode(empty,CXT_Attribute,"size"),
            CXT_Text,CPLString().Printf("%lld",empty_size));
        CPLCreateXMLNode(CPLCreateXMLNode(empty,CXT_Attribute,"offset"),
            CXT_Text,CPLString().Printf("%lld",empty_offset));
    }

    char *text=CPLSerializeXMLTree(cache);
    cout << text;
    CPLFree(text);

    CPLDestroyXMLNode(cache);
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
};

void mrf2cache(vector<mrf_data> &in, opts &o) {
    ostream *out;
    ofstream of;
    if (EQUAL(o.ofname.c_str(),"-")) out=&cout;
    else {
        of.open(o.ofname.c_str());
        if (!of.is_open()) {
            cerr << "Can't open output file " << o.ofname << endl;
            exit(1);
        }
        out=&of;
    }

    if (o.xml) {
        for (vector<mrf_data>::iterator i=in.begin();i!=in.end();i++)
            i->mrf2cachex(*out);
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

    while ((opt=getopt(argc, argv,"pchxb")) != -1) {
        switch(opt) {
        case 'p' :
            o.mode=PATTERN;
            break;
        case 'c' :
            o.mode=CONF;
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
    // Single input is input file name
    if (optind==argc-1)
        input.push_back(mrf_data(argv[optind++]));
    while (optind<argc-1)
        input.push_back(mrf_data(argv[optind++]));
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
