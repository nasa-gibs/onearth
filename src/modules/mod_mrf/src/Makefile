MODULE = mod_mrf
TARGET = .libs/$(MODULE).so
C_SRC = $(MODULE).cpp

DEFINES = -DLINUX -D_REENTRANT -D_GNU_SOURCE $(DEBUG)

# Create the ../Makefile.lcl, which should define
# DEST, the folder where the apache module should reside
# INCLUDES, the gcc include commands for httpd, apr headers
# LIBTOOL, DEBUG ...

MAKEOPT ?= Makefile.lcl
include $(MAKEOPT)

# Can't use apxs to build c++ modules
# The options used here might depend on how apache was built

default	:	$(TARGET)

$(TARGET)       :       $(C_SRC)
	$(LIBTOOL) --silent --mode=compile g++ -std=c++11 -prefer-pic -O2 -Wall $(DEFINES) $(EXTRA_INCLUDES) -I $(EXP_INCLUDEDIR) -pthread -c -o $(MODULE).lo $< && touch $(MODULE).slo
	$(LIBTOOL) --silent --mode=link g++ -std=c++11 -o $(MODULE).la -rpath $(LIBEXECDIR) -module -avoid-version $(MODULE).lo

install : $(TARGET)
	$(SUDO) $(CP) $(TARGET) $(DEST)

clean   :
	$(RM) -r .libs *.{o,lo,slo,la}
