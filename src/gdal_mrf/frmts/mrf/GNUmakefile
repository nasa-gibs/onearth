# Modified for MRF plugin

include ../../GDALmake.opt

OBJ	=	marfa_dataset.o mrf_band.o JPEG_band.o PNG_band.o ZLIB_band.o Raw_band.o Tif_band.o mrf_util.o

CPPFLAGS	:= -fPIC	$(GDAL_INCLUDE) $(CPPFLAGS)

default:	$(OBJ:.o=.$(OBJ_EXT))

clean:
	rm -rf *.o *.lo .libs/$(OBJ) .libs $(O_OBJ) gdal_mrf.so.1

install-obj:	$(O_OBJ:.o=.$(OBJ_EXT))

$(OBJ) $(O_OBJ):	marfa.h

plugin: $(OBJ)
	g++ -shared -W1,-soname,gdal_mrf.so.1 $(OBJ) -o gdal_mrf.so.1

iplugin: gdal_mrf.so.1 plugin
	cp $< $(prefix)/lib/gdalplugins/1.9/$<
