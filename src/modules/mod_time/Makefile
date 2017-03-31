C_SRC = mod_time.cpp
FILES = $(C_SRC)

DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE

# Create the ../Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# INCLUDES, the gcc include commands for httpd, apr headers

include Makefile.lcl
TARGET = .libs/mod_time.so

# Can't use apxs to build c++ modules
# The options used here might depend on how apache was built
$(TARGET)       :       $(FILES)
	libtool --silent --mode=compile g++ -prefer-pic -O0 -g -Wall $(DEFINES) $(INCLUDES)  -pthread -c -o mod_time.lo $(C_SRC) && touch mod_time.slo
	libtool --silent --mode=link g++ -o mod_time.la -rpath $(MOD_PATH) -ljansson -module -avoid-version mod_time.lo

install : $(TARGET)
	sudo cp $(TARGET) $(MOD_PATH)

clean   :
	rm -rf .libs *.{o,lo,slo,la}

