TARGET=.libs/mod_oems.so
C_SRC = mod_oems.cpp
FILES = $(C_SRC)
INCLUDES = -I /usr/include/httpd -I /usr/include/apr-1 -I /usr/include/libxml2
MOD_PATH = /usr/lib64/httpd/modules/

default	: $(TARGET)
$(TARGET) : $(FILES)
	libtool --silent --mode=compile g++ -prefer-pic -O2 -Wall  -DLINUX -D_REENTRANT -D_GNU_SOURCE -pthread $(INCLUDES) -c -o mod_oems.lo $(C_SRC) && touch mod_oems.slo
	libtool --silent --mode=link g++ -o mod_oems.la -rpath $(MOD_PATH) -module -avoid-version -lxml2 mod_oems.lo

install	:	$(TARGET)
	cp $(TARGET)	$(MOD_PATH)

clean	:
	rm -rf .libs *.{o,lo,slo,la}