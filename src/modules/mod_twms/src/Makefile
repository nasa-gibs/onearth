MODULE = mod_twms
C_SRC = $(MODULE).cpp
FILES = $(C_SRC)
OBJECTS = $(FILES:.cpp=.lo)

DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE

LIBS =

# Create Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# INCLUDES, includes for httpd, apr headers
# For example look at Makefile.lcl.example

include Makefile.lcl
TARGET = .libs/$(MODULE).so

# Can't use apxs to build c++ modules
# The options used here might depend on how apache was built
$(TARGET)       :       $(OBJECTS)
	libtool --mode=link g++ -o $(MODULE).la -rpath $(MOD_PATH) -module -avoid-version $^ $(LIBS)

%.lo	:	%.cpp
	libtool --mode=compile g++ -std=c++0x -prefer-pic -O2 -Wall $(DEFINES) $(INCLUDES) -pthread -c -o $@ $< && touch $(@:.lo=.slo)

install : $(TARGET)
	cp $(TARGET) $(MOD_PATH)

clean   :
	rm -rf .libs *.o *.lo *.slo *.la
