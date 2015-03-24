default: kmlgen.cgi

# Use the first definition if libcc is installed in the system dir
 PREFIX=/usr
#PREFIX=$(HOME)
# This should be the externaly visible host name, double quoted twice

WEB_HOST='"localhost/twms-geo"'

kmlgen.cgi : kmlgen.cpp Makefile
	$(CXX) -DHOST=$(WEB_HOST)  -o $@ $< -I $(PREFIX)/include -lcgicc
