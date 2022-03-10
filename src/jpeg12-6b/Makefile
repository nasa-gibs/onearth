TARGET= libjpeg12.o

C_SRC = jcapimin.c jcapistd.c jccoefct.c jccolor.c jcdctmgr.c jchuff.c \
	jcinit.c jcmainct.c jcmarker.c jcmaster.c jcomapi.c jcparam.c \
	jcphuff.c jcprepct.c jcsample.c jctrans.c jdapimin.c jdapistd.c \
	jdatadst.c jdatasrc.c jdcoefct.c jdcolor.c jddctmgr.c jdhuff.c \
	jdinput.c jdmainct.c jdmarker.c jdmaster.c jdmerge.c jdphuff.c \
	jdpostct.c jdsample.c jdtrans.c jerror.c jfdctflt.c jfdctfst.c \
	jfdctint.c jidctflt.c jidctfst.c jidctint.c jidctred.c jquant1.c \
	jquant2.c jutils.c jmemmgr.c jmemnobs.c

CXXFLAGS = -O2 -fPIC $(DEBUG)

OBJECTS = $(C_SRC:.c=.o)

default : $(TARGET)

%.o	:	%.c
	$(CC) $(CXXFLAGS) $(DEFINES) -c $< -o $@

libjpeg12.o	:	$(OBJECTS)
	$(LD) -r -o $@ $^

clean	:
	$(RM) $(OBJECTS) $(TARGET)
