MAKEOPT ?= Makefile.lcl
include $(MAKEOPT)

INCLUDES += -I $(PREFIX)/include
LIBDIR = $(PREFIX)/lib
LIBS = -lbrunslidec-c -lbrunslienc-c

TARGET = .libs/mod_brunsli.so

default: $(TARGET)

$(TARGET)	: mod_brunsli.c
	$(APXS) -c $(INCLUDES) -L $(LIBDIR) $(LIBS) $<

clean:
	$(RM) -r mod_brunsli.lo mod_brunsli.la mod_brunsli.slo .libs

install: $(TARGET)
	$(SUDO) $(CP) $< $(DEST)
