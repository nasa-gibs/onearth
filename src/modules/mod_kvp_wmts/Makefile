# Create the Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# For example, loot at Makefile.lcl.example

include Makefile.lcl

default:	mod_kvp_wmts.c mod_kvp_wmts.h
	apxs -c -Wc,-O0 $<
install :       ./.libs/mod_kvp_wmts.so
	sudo    cp ./.libs/mod_kvp_wmts.so    $(MOD_PATH)

