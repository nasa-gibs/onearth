MODULE = mod_receive
TARGET = .libs/$(MODULE).so

C_SRC = $(MODULE).cpp
HEADER = receive_context.h

FILES = $(C_SRC) $(HEADER)

# Create a file Makefile.lcl. It should define INCLUDES and MOD_PATH
# For example on how to create Makefile.lcl see Makefile.example.lcl

include Makefile.lcl

default	: $(TARGET)

# Make it do c++
$(TARGET)	:	$(FILES)
	libtool --silent --mode=compile g++ -prefer-pic -O2 -Wall  -DLINUX -D_REENTRANT -D_GNU_SOURCE -pthread $(INCLUDES) -c -o $(MODULE).lo $(C_SRC) && touch $(MODULE).slo
	libtool --silent --mode=link g++ -o $(MODULE).la -rpath $(MOD_PATH) -module -avoid-version $(MODULE).lo

install	:	$(TARGET)
	sudo	cp $(TARGET)	$(MOD_PATH)
	sudo	cp $(HEADER)	$(HTTPD_INCLUDES_PATH)


clean	:
	rm -rf .libs *.o *.lo *.slo *.la

