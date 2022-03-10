cmake_minimum_required(VERSION 3.5)
cmake_policy(SET CMP0076 NEW)

project(ICD LANGUAGES CXX C)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(JP12_SOURCES
    jcapimin.c
    jcapistd.c
    jccoefct.c
    jccolor.c
    jcdctmgr.c
    jchuff.c
    jcinit.c
    jcmainct.c
    jcmarker.c
    jcmaster.c
    jcomapi.c
    jcparam.c
    jcphuff.c
    jcprepct.c
    jcsample.c
    jctrans.c
    jdapimin.c
    jdapistd.c
    jdatadst.c
    jdatasrc.c
    jdcoefct.c
    jdcolor.c
    jddctmgr.c
    jdhuff.c
    jdinput.c
    jdmainct.c
    jdmarker.c
    jdmaster.c
    jdmerge.c
    jdphuff.c
    jdpostct.c
    jdsample.c
    jdtrans.c
    jerror.c
    jfdctflt.c
    jfdctfst.c
    jfdctint.c
    jidctflt.c
    jidctfst.c
    jidctint.c
    jidctred.c
    jmemmgr.c
    jmemnobs.c
    jquant1.c
    jquant2.c
    jutils.c
)
list(TRANSFORM JP12_SOURCES PREPEND src/jpeg12-6b/)
# set_source_files_properties(${JP12_SOURCES} PROPERTIES LANGUAGE CXX)

set(JP12_HEADERS
    cderror.h
    jchuff.h
    jconfig.h
    jdct.h
    jdhuff.h
    jerror.h
    jinclude.h
    jmemsys.h
    jmorecfg.h
    jpegint.h
    jpeglib.h
    jversion.h
)
list(TRANSFORM JP12_HEADERS PREPEND src/jpeg12-6b/)

set(ICD_SOURCES
    icd_codecs.cpp
    JPEG_codec.cpp
    JPEG8.cpp
    JPEG12.cpp
    LERC_codec.cpp
    Packer_RLE.cpp
    PNG_codec.cpp
    lerc1/Lerc1Image.cpp
)
list(TRANSFORM ICD_SOURCES PREPEND src/)
list(APPEND ICD_SOURCES ${JP12_SOURCES})
# message("${ICD_SOURCES}")

set(ICD_HEADERS
    BitMask2D.h
    icd_codecs.h
    JPEG_codec.h
    lerc1/Lerc1Image.h
)
list(TRANSFORM ICD_HEADERS PREPEND src/)
list(APPEND ICD_HEADERS ${JP12_HEADERS})
# message("${ICD_HEADERS}")

find_package(JPEG REQUIRED)
find_package(PNG REQUIRED)

add_library(libicd SHARED)
if (MSVC)
add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
target_link_options(libicd PUBLIC "/NODEFAULTLIB:LIBCMT")
endif (MSVC)

target_sources(libicd PRIVATE ${ICD_SOURCES} ${ICD_HEADERS})
# target_sources(libicd PUBLIC)
set_target_properties(libicd PROPERTIES PUBLIC_HEADER icd_codecs.h)
include_directories(${JPEG_INCLUDE_DIRS} ${PNG_INCLUDE_DIRS})
target_link_libraries(libicd PRIVATE ${JPEG_LIBRARIES} ${PNG_LIBRARIES})

install(TARGETS libicd PUBLIC_HEADER)
