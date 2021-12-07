include Makefile.lcl

C_SRC = mod_reproject.cpp JPEG_codec.cpp PNG_codec.cpp
HEADER = mod_reproject.h

FILES = $(C_SRC)
OBJECTS = $(FILES:.cpp=.lo)

DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE $(DEBUG)

LIBS = -ljpeg -lpng -lstdc++

# Create Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# INCLUDES, includes for httpd, apr headers
# For example look at Makefile.lcl.example

TARGET = .libs/mod_reproject.so

# Can't use apxs to build c++ modules
# The options used here might depend on how apache was built
$(TARGET)       :       $(OBJECTS)
	$(LIBTOOL) --mode=link g++ -o mod_reproject.la -rpath $(DEST) -module -avoid-version $^ $(LIBS)

%.lo	:	%.cpp $(HEADER)
	$(LIBTOOL) --mode=compile g++ -std=c++0x -prefer-pic -O2 -Wall $(DEFINES) $(INCLUDES) -pthread -c -o $@ $< && touch $(@:.lo=.slo)

install : $(TARGET)
	cp $(TARGET) $(DEST)

clean   :
	rm -rf .libs *.o *.lo *.slo *.la