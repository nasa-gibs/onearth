default: kmlgen.cgi

# Use the first definition if libcc is installed in the system dir
 PREFIX=/usr
#PREFIX=$(HOME)
# This should be the externaly visible host name, double quoted twice
# WEB_HOST='"map1.vis.earthdata.nasa.gov"'
#WEB_HOST='"map1.vis.earthdata.nasa.gov/twms-geo"'
WEB_HOST='"localhost:8080/Tiled-WMS"'

kmlgen.cgi : kmlgen.cpp Makefile
	$(CXX) -DHOST=$(WEB_HOST)  -o $@ $< -I $(PREFIX)/include -lcgicc
