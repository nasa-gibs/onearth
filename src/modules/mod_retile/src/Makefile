MODULE = mod_retile

MAKEOPT ?= Makefile.lcl
include $(MAKEOPT)

C_SRC = $(MODULE).cpp
HEADERS =

FILES = $(C_SRC)
OBJECTS = $(FILES:.cpp=.lo)

CXXFLAGS = -prefer-pic -O2 -Wall
DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE $(DEBUG)

# Create Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# EXTRA_INCLUDES, includes for httpd, apr headers
# look at Makefile.lcl.example

TARGET = .libs/$(MODULE).so

# Can't use apxs to build c++ modules
# The options used here might depend on how apache was built
$(TARGET)       :       $(OBJECTS)
	$(LIBTOOL) --mode=link g++ -o $(MODULE).la -rpath $(LIBEXECDIR) -module -avoid-version $^ $(LIBS)

%.lo	:	%.cpp $(HEADERS)
	$(LIBTOOL) --mode=compile g++ -std=c++11 $(CXXFLAGS) $(DEFINES) $(EXTRA_INCLUDES) -I $(EXP_INCLUDEDIR) -pthread -c -o $@ $< && touch $(@:.lo=.slo)

install : $(TARGET)
	$(SUDO) $(CP) $(TARGET) $(DEST)

clean   :
	$(RM) -r .libs *.o *.lo *.slo *.la
