MODULE = mod_receive
TARGET = .libs/$(MODULE).so

C_SRC = $(MODULE).cpp
HEADER = receive_context.h

FILES = $(C_SRC) $(HEADER)

DEFINES = $(DEBUG) -DLINUX -D_REENTRANT -D_GNU_SOURCE

# Create a file Makefile.lcl. It should define EXTRA_INCLUDES and MOD_PATH
# For example on how to create Makefile.lcl see Makefile.example.lcl
MAKEOPT ?= Makefile.lcl
include $(MAKEOPT)

default	: $(TARGET)

# Make it do c++
$(TARGET)	:	$(FILES)
	$(LIBTOOL) --silent --mode=compile g++ -prefer-pic -O2 -Wall $(DEFINES) -pthread $(EXTRA_INCLUDES) -c -o mod_receive.lo $(C_SRC) && touch mod_receive.slo
	$(LIBTOOL) --silent --mode=link g++ -o mod_receive.la -rpath $(LIBEXECDIR) -module -avoid-version mod_receive.lo

install	:	$(TARGET) $(HEADER)
	$(SUDO)	$(CP) $< $(DEST)
	$(SUDO)	$(CP) $(HEADER) $(EXP_INCLUDEDIR)

clean	:
	$(RM) -rf .libs *.o *.lo *.slo *.la
