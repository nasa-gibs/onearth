default: kmlgen.cgi

# Use the first definition if libcc is installed in the system dir
 PREFIX=/usr
#PREFIX=$(HOME)
# This should be the externaly visible host name, double quoted twice

ifndef WEB_HOST
	WEB_HOST='"localhost/twms"'
endif

kmlgen.cgi : kmlgen.cpp Makefile
	$(CXX) -DHOST='"$(WEB_HOST)"'  -o $@ $< -I $(PREFIX)/include -lcgicc
