APXS=apxs

TARGETS= .libs/mod_wms.so .libs/mod_twms.so twms_tool
default	: $(TARGETS)

module	:	.libs/mod_wms.so .libs/mod_twms.so

.libs/mod_wms.so	: mod_wms.c cache.h
	$(APXS) -c mod_wms.c -lm -lsqlite3

.libs/mod_twms.so	: mod_twms.c cache.h
	$(APXS) -c mod_twms.c

twms_tool	: twms_tool.cpp twms_tool.h
	$(CXX) -DLINUX -O2 $(INCLUDE) -o $@ $< $(LDFLAGS) -lgdal $(LIBS)

clean	:
	rm -rf .libs mod_{twms,wms}.{*o,la}  twms_tool
