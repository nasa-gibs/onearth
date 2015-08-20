APXS=apxs

TARGETS= .libs/mod_onearth.so .libs/mod_twms.so oe_create_cache_config
default	: $(TARGETS)

module	:	.libs/mod_onearth.so .libs/mod_twms.so

.libs/mod_onearth.so	: mod_onearth.c cache.h
	$(APXS) -c mod_onearth.c -lm -lsqlite3

.libs/mod_twms.so	: mod_twms.c cache.h
	$(APXS) -c mod_twms.c

oe_create_cache_config	: oe_create_cache_config.cpp oe_create_cache_config.h
	$(CXX) -DLINUX -O2 $(INCLUDE) -o $@ $< $(LDFLAGS) -lgdal $(LIBS)

clean	:
	rm -rf .libs mod_{twms,onearth}.{*o,la}  oe_create_cache_config
