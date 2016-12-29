# Create the Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# For example, loot at Makefile.lcl.example

default:	mod_m_lookup.c mod_m_lookup.h
	apxs -c -llua -ljansson -Wc,-O0 $<
install:	mod_m_lookup.c mod_m_lookup.h
	apxs -i -llua -ljansson -c -Wc,-O0 $<