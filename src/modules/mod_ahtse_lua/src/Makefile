# Create the Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# For example, loot at Makefile.lcl.example

include Makefile.lcl

MODULE = mod_ahtse_lua
C_SRC = $(MODULE).cpp
FILES = $(C_SRC)
OBJECTS = $(FILES:.cpp=.lo)

DEFINES := $(DEFINES) -DLINUX -D_REENTRANT -D_GNU_SOURCE

TARGET = .libs/$(MODULE).so

$(TARGET)	:	$(OBJECTS)
	libtool --mode=link g++ -o $(MODULE).la -rpath $(MOD_PATH) -module -avoid-version $(LIBS) $^

%.lo	:	%.cpp $(MODULE).h
	libtool --mode=compile g++ -std=c++0x -prefer-pic -O2 -Wall $(DEFINES) $(INCLUDES) -pthread -c -o $@ $< && touch $(@:.lo=.slo)

# Only do this when httpd is not running
install :       $(TARGET)
	cp $(TARGET) $(MOD_PATH)

clean	:
	rm -rf .libs *.o *.la *.slo *.lo

