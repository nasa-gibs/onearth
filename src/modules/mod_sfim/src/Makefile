# Create the Makefile.lcl, which should define
# MOD_PATH, the folder where the apache module should reside
# For example, loot at Makefile.lcl.example

include Makefile.lcl

default:	mod_sfim.c mod_sfim.h
	apxs -c $<
install :       ./.libs/mod_sfim.so
	cp ./.libs/mod_sfim.so    $(MOD_PATH)

