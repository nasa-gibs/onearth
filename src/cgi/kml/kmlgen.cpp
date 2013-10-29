/*
* Copyright (c) 2002-2013, California Institute of Technology.
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
 *  Generate a top level KML for a specific day, or a range of days
 * 
 *
 */

#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cgicc/Cgicc.h>

using namespace std;
using namespace cgicc;

// #define ifs(X,Y) if (cgi_param(X)) { Y }
#define ifs(X,Y) if (CGI.getElement(X) != CGI.getElements().end()) { Y }
#define cgi_param(X) CGI.getElement(X)->getValue()

typedef struct {
  int year;
  int month;
  int day;
  int ord_day; // Numerical day
} date_rec;

typedef struct {
  date_rec now;
  date_rec period;
  int	repeats;
} time_interval;

string ord_time(const date_rec &time) {
  ostringstream s;
  s << setfill('0') << setw(((time.year+1900)<0)?5:4) << time.year + 1900 ;
  s << setw(3) << time.ord_day ;
  return s.str();
}

string iso_time(const date_rec &time) {
  ostringstream s;
  s << setfill('0') << setw(((time.year+1900)<0)?5:4) << time.year + 1900 ;
  s << "-" << setw(2) << time.month << "-" << setw(2) << time.day ;
  return s.str();
}

inline int is_leap(int year) {
  int i=year+1900;
  return ((i%4)?0:((i%400)?((i%100)?1:0):1));
}

// Calculate the ordinal day 
bool to_ordinal_date(date_rec &date) {
  static int moffset[13]={0,0,31,59,90,120,151,181,212,243,273,304,334};
  date.ord_day=date.day+moffset[date.month]+((date.month>2)?is_leap(date.year):0);
  return true;
}

// Adjust month/day from ordinal date
bool from_ordinal_date(date_rec &date) {
  static int moffset[13]={0,0,31,59,90,120,151,181,212,243,273,304,334};
  static int leapmoffset[13]={0,0,31,60,91,121,152,182,213,244,274,305,335};
  int *mo=(is_leap(date.year)==1)?leapmoffset:moffset;
  for (int m=12;m>0;m--) 
    if (date.ord_day>mo[m]) {
      date.month=m;
      date.day=date.ord_day-mo[m];
      break;
    }
  return true;
}

// Add the period to the day
void adjust_date(date_rec &the_date, date_rec &period) {
  // Adjust the year
  the_date.year+=period.year;
  // Adjust the month, and the year
  the_date.month+=period.month;
  while (the_date.month>12) {
    the_date.year++;
    the_date.month-=12;
  }
  // Calculate the ordinal date before adding days
  to_ordinal_date(the_date);
  the_date.ord_day+=period.day;
  // Now adjust the year again
  while (((the_date.ord_day>366)&&(1==is_leap(the_date.year)))||
	 ((the_date.ord_day>365)&&(0==is_leap(the_date.year))))
    the_date.ord_day-=365+is_leap(the_date.year++);
  // And calculate the month from the new ordinal
  from_ordinal_date(the_date);
}

// From oopweb.com
void Tokenize(const string& str,
                      vector<string>& tokens,
                      const string& delimiters = " ")
{
    // Skip delimiters at beginning.
    string::size_type lastPos = str.find_first_not_of(delimiters, 0);
    // Find first "non-delimiter".
    string::size_type pos     = str.find_first_of(delimiters, lastPos);

    while (string::npos != pos || string::npos != lastPos)
    {
        // Found a token, add it to the vector.
        tokens.push_back(str.substr(lastPos, pos - lastPos));
        // Skip delimiters.  Note the "not_of"
        lastPos = str.find_first_not_of(delimiters, pos);
        // Find next "non-delimiter"
        pos = str.find_first_of(delimiters, lastPos);
    }
}

// Function to parse a period in ISO time format

bool parse_period(string &period, date_rec &date) {
 
  string::size_type LastPos=1; 
  char delimiters[]="YMDW";
  string::size_type pos=period.find_first_of(delimiters, LastPos);

  while (string::npos != pos || string::npos != LastPos) {
    int value=atoi(period.substr(LastPos,pos-LastPos).c_str());
    switch (period[pos]) {
      case 'Y' : date.year=value; break;
      case 'M' : date.month=value; break;
      case 'W' : date.day=value*7; break;
      case 'D' : date.day=value;
    }
    LastPos = period.find_first_not_of(delimiters, pos);
    pos = period.find_first_of(delimiters, LastPos);
  }
  return true;
}


// Function to parse one simple ISO 8610 time record
bool parse_one_time(string time,date_rec &date) {
  vector<string> tokens;
  Tokenize(time,tokens,"-");
  date.year=date.month=date.day=0;
  
  if (1==tokens.size()) { // basic format
    int bc=0;
    if ('-'==time[0]) bc=1;
    date.year=atoi(time.substr(0,4+bc).c_str());
    date.month=atoi(time.substr(4+bc,2).c_str());
    date.day=atoi(time.substr(6+bc,2).c_str());
  } else {
    date.year=atoi(tokens[0].c_str());
    date.month=atoi(tokens[1].c_str());
    if (3==tokens.size())
      date.day=atoi(tokens[2].c_str());
  }
  date.year-=1900; // tm standard
  to_ordinal_date(date);
  tokens.clear();
  return true;
}


// Function to parse an ISO record, with periods and repeat counts
bool parse_time(string &time, time_interval &date) {
  date.repeats=0;
  vector<string> tokens;
  Tokenize(time,tokens,"/");

  try {
    if (1==tokens.size()) {
      date.repeats=0;
      parse_one_time(tokens[0],date.now);
    } else if (3==tokens.size()) {
      if (tokens[0].find("R")) throw 2;
      date.repeats=atoi(tokens[0].c_str()+1);
      parse_one_time(tokens[1],date.now);
      if (tokens[2].find("P")) throw 3;
      parse_period(tokens[2],date.period);
    } else throw 1;
  } catch (int er) {
    switch (er) {
      case 1: cerr << "ISO time record malformed " << tokens.size() << endl; break;
      case 2: cerr << "ISO repeated interval parsing error\n";  break;
      case 3: cerr << "ISO repeated interval period parsing error\n";  break;
      default: break;
    return false;
   }
  }
  tokens.clear();
  return true;
};

struct kml_params {
  string layers;
  date_rec day;
  string time_stamp;
};

// Adds the internal data to a KML body
void kml_day(string &body, kml_params &kp) {
  string ts(kp.time_stamp);
  date_rec day(kp.day);
  string layers=kp.layers;

  body+="<Folder>\n";
  if (ts.size()&&(ts.find("|")!=string::npos))
    body+="<TimeSpan><begin>" + ts.substr(0,ts.find("|")) + "</begin><end>"
        + ts.substr(ts.find("|")+1,ts.size()) + "</end></TimeSpan>";
  body+="<NetworkLink><visibility>1</visibility>\n";
  body+="<name>" + iso_time(day) + " " + layers + "</name>\n";
  body+="<Region>\n<LatLonBox><north>90</north><south>-90</south><east>108</east><west>-180</west></LatLonBox>\n"
	"<Lod><minLodPixels>0</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod>\n"
	"</Region>\n";
  body+="<Link><href>http://" HOST "/twms.cgi?request=GetMap&amp;layers=";
  body+=layers;
  body+="&amp;srs=EPSG:4326&amp;format=application/vnd.google-earth.kml+xml&amp;styles=&amp;time=";
  body+=iso_time(day);
  body+="&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90</href>\n"
	"<viewRefreshMode>onRegion</viewRefreshMode></Link></NetworkLink>\n";

  body+="<NetworkLink><visibility>1</visibility>\n";
  body+="<name>" + iso_time(day) + "_" + layers + "</name>\n";
  body+="<Region><LatLonBox><north>90</north><south>-90</south><east>180</east><west>108</west></LatLonBox>\n"
	"<Lod><minLodPixels>0</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>\n";
  body+="<Link><href>http://" HOST "/twms.cgi?request=GetMap&amp;layers=";
  body+=layers;
  body+="&amp;srs=EPSG:4326&amp;format=application/vnd.google-earth.kml+xml&amp;styles=&amp;time=";
  body+=iso_time(day);
  body+="&amp;width=512&amp;height=512&amp;bbox=108,-198,396,90</href>\n"
	"<viewRefreshMode>onRegion</viewRefreshMode></Link></NetworkLink></Folder>\n";
}

void kml_bday(string &body, const date_rec &day) {
  string now(iso_time(day));
  kml_params kp;
  kp.day=day;
  kp.layers="daily_planet";
  kp.time_stamp=string(now + "T00:00:00Z|" + now + "T11:59:59Z");
  kml_day(body,kp);
  kp.layers="daily_afternoon";
  kp.time_stamp=string(now + "T12:00:01Z|" + now + "T23:59:59Z");

//  kml_day(body, day, string("daily_planet")   ,string(now + "T00:00:01Z|" + now + "T11:59:59Z"));
//  kml_day(body, day, string("daily_afternoon"),string(now + "T12:00:00Z|" + now + "T23:59:59Z"));
}

int main(int argc, char **argv)

{
  string body("");
  string layers("");
  string times("");
  string request("");
  string meta_path("/lcs/raschal04/tellus/");
  time_interval date={0};

  // cgi_init();
  // cgi_process_form();

  // The CgiCC object
  Cgicc CGI;

  ifs("layers", layers=cgi_param("layers"););
  ifs("time", times=cgi_param("time"););
  ifs("request", request=cgi_param("request"););

  if (times.size()) parse_time(times,date);

  // Is this a request for metadata ?
  if (request.size()) { // This is not longer working
    if ( (request.find("scenes")!=string::npos) && layers.size() && times.size() ) { // Yes it is
      string metafile_name("");
      char buffer[1024];
      body+="Content-type: text/plain\n\n";
      // This is the file name
      metafile_name=meta_path+(layers.find("daily_planet")?"MYD02":"MOD02")+ord_time(date.now)+"_.pjg.geo";
      fstream metafile(metafile_name.c_str(),fstream::in);
      if (metafile.is_open())
      while (metafile.getline(buffer,sizeof(buffer))) { 
	string line(buffer);
        if (string::npos!=line.find("QKM.A")) body+=line+"\n";
      }
    } // If not, the data should deal with it
  } else if (layers.size() && times.size() ) {
    body+="Content-type: application/vnd.google-earth.kml+xml\n\n";
    body+="<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<kml xmlns=\"http://earth.google.com/kml/2.1\">\n<Document>\n<name>";
    body+=times + " " + layers + " coverage </name>\n"
	"<description>Automatically generated NASA GIBS KML coverage.</description>"
	"<Style id=\"HC\"><ListStyle>\n"
	"<listItemType>checkHideChildren</listItemType>\n"
	"</ListStyle></Style>\n"
	"<Region>\n"
	"<LatLonBox>\n"
	"<north>90</north><south>-90</south>\n"
	"<east>180</east><west>-180</west>\n"
	"</LatLonBox>\n"
	"<Lod><minLodPixels>0</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod>\n"
	"</Region>\n<Folder>\n";
    if (date.repeats==0)
      if (string::npos==layers.find("daily_both")) {
        kml_params kp;
        kp.layers=layers;
        kp.day=date.now;
	kp.time_stamp="";
	// kml_day(body,date.now,layers);
	kml_day(body,kp);
      } else 
	kml_bday(body,date.now);
    else for (int i=0;i<date.repeats;i++) 
      if (string::npos==layers.find("daily_both")) {
	kml_params kp;
        kp.layers=layers;
	kp.day=date.now;
	string now(iso_time(date.now));
	adjust_date(date.now,date.period);
	now+="|"+iso_time(date.now);
	// cerr << now << endl;
	kp.time_stamp=now;
	kml_day(body,kp);
      } else {
	kml_bday(body,date.now);
	adjust_date(date.now,date.period);
      }
    body+="<styleUrl>#HC</styleUrl>\n"
	  "</Folder>\n</Document></kml>\n" ;
  } else {
    body="Content-type: text/HTML\n\n";
    body+="Usage error, check parameters\n";
    body+=" They should be : layers=<name>\n";
    body+="                  time=YYYY-MM-DD\n";
  }
  puts(body.c_str());
  return 0;
}
