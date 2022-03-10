/*
* JPEG_codec.h
*
* Shared code for AHTSE JPEG codec
*
* (C) Lucian Plesea 2019-2020
*/

#if !defined(JPEG_CODEC_H)
#define JPEG_CODEC_H

#include "icd_codecs.h"
#include "BitMask2D.h"
#include <setjmp.h>

NS_ICD_START

// Could be used for short int, so make it a template
template<typename T> static int apply_mask(BitMap2D<> *bm, T *ps, int nc = 3, int line_stride = 0) {
    int w = bm->getWidth();
    int h = bm->getHeight();

    // line_stride of zero means packed buffer
    if (line_stride == 0)
        line_stride = w * nc;
    else
        line_stride /= sizeof(T); // Convert from bytes to type stride

    // Count the corrections
    int count = 0;
    for (int y = 0; y < h; y++) {
        T *s = ps + y * line_stride;
        for (int x = 0; x < w; x++) {
            if (bm->isSet(x, y)) { // Should be non-zero
                for (int c = 0; c < nc; c++, s++) {
                    if (*s == 0) {
                        *s = 1;
                        count++;
                    }
                }
            }
            else { // Should be zero
                for (int c = 0; c < nc; c++, s++) {
                    if (*s != 0) {
                        *s = 0;
                        count++;
                    }
                }
            }
        }
    }
    return count;
}

DLL_LOCAL const char *jpeg8_stride_decode(codec_params &params, storage_manager &src, void *buffer);
DLL_LOCAL const char *jpeg8_encode(jpeg_params &params, storage_manager &src, storage_manager &dst);

DLL_LOCAL const char *jpeg12_stride_decode(codec_params &params, storage_manager &src, void *buffer);
DLL_LOCAL const char *jpeg12_encode(jpeg_params &params, storage_manager &src, storage_manager &dst);

NS_END
#endif
