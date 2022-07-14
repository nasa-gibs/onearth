MODULE = mod_convert
TARGET = .libs/$(MODULE).so

C_SRC = $(MODULE).cpp
HEADERS = 

OBJECTS = $(C_SRC:.cpp=.lo)

CXXFLAGS = -prefer-pic -O2 -Wall

DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE $(DEBUG)

FILES = $(C_SRC) $(HEADERS)

# Create a file Makefile.lcl. It should define EXTRA_INCLUDES and DEST
# For example on how to create Makefile.lcl see Makefile.example.lcl


MAKEOPT ?= Makefile.lcl
include $(MAKEOPT)

default	: $(TARGET)

# Can't use apxs to build c++ modules
# The options used here might depend on the system
#
$(TARGET)	:	$(OBJECTS)
	$(LIBTOOL) --mode=link g++ -o $(MODULE).la -rpath $(LIBEXECDIR) -module -avoid-version $^ $(LIBS)

%.lo	:	%.cpp
	$(LIBTOOL) --mode=compile g++ -std=c++11 $(CXXFLAGS) $(DEFINES) $(EXTRA_INCLUDES) -I $(EXP_INCLUDEDIR) -pthread -c -o $@ $< && touch $(@:.lo=.slo)

install	:	$(TARGET)
	$(SUDO)	$(CP) $(TARGET)	$(DEST)

clean	:
	$(RM) -r .libs *.o *.lo *.slo *.la
