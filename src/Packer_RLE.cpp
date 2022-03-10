/*
 * Copyright 2016-2020 Esri
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Author:  Lucian Plesea
 *
 */

//
// Implements an RLE codec packer.  The RLE uses a dedicated marker code
// This particular packer picks the least used byte value as marker,
// which makes the worst case data expansion more reasonable, at the expense
// of taking two passes over the input data
//

// For memset
#include <cstring>
#include <vector>
#include <algorithm>
#include "BitMask2D.h"

NS_ICD_USE

//
// RLE yarn codec, uses a dedicated code as marker, default value is 0xC3
// This is the C implementation, there is also a C++ one
// For yarnball compression, it performs better than using a double char marker
//
// Includes both encoder and decoder
// Worst case input:output ratio is 1:2, when the input is 1,2 or three marker codes
// For long input streams, the input:output ratio is between
// 13260.6:1 (best) and 1:1.75 (worst)
//
// Could be a byte stream filter which needs very little local storage
//

constexpr int MAX_RUN = 768 + 0xffff;
typedef unsigned char Byte;

#define UC(X) static_cast<Byte>(X)

// Encode helper function
// It returns how many times the byte at *s is repeated
// a value between 1 and min(max_count, MAX_RUN)
inline static int run_length(const Byte *s, int max_count)
{
    if (max_count > MAX_RUN)
        max_count = MAX_RUN;
    const Byte c = *s++;
    for (int count = 1; count < max_count; count++)
        if (c != *s++)
            return count;
    return max_count;
}

#define RET_NOW do { return static_cast<size_t>(next - reinterpret_cast<Byte *>(obuf)); } while(0)

//
// C compress function, returns compressed size
// len is the size of the input buffer
// caller should ensure that output buffer is at least 2 * N to be safe, 
// dropping to N * 7/4 for larger input
// If the Code is chosen to be the least present value in input, the
// output size requirement is bound by N / 256 + N
//
static size_t toYarn(const char *ibuffer, char *obuf, size_t len, Byte CODE = 0xC3) {
    Byte *next = reinterpret_cast<Byte *>(obuf);

    while (len > 0) {
        Byte b = static_cast<Byte>(*ibuffer);
        int run = run_length(reinterpret_cast<const Byte *>(ibuffer), static_cast<int>(len));

        if (run < 4) {
            // Encoded as single bytes, stored as such, CODE followed by a zero
            while (run--) {
                *next++ = b;
                if (CODE == b)
                    *next++ = 0;
                ibuffer++;
                len--;
            }
            continue;
        }

        // Encoded as a sequence
        *next++ = CODE; // Start with Marker code, always present

        if (run >= 0x300) { // Long sequence
            ibuffer += 0x300; // May be unsafe to read *ibuffer
            len -= 0x300;
            run -= 0x300;
            *next++ = 3;
            *next++ = UC(run >> 8); // Forced high count
        }
        else if (run >= 0x100) { // medium sequence, between 256 and 767
            *next++ = UC(run >> 8); // High count, could be 1 or 2
        }

        // Low count and value are always present
        *next++ = UC(run & 0xff);
        *next++ = b;
        ibuffer += run;
        len -= run;
    }
    RET_NOW;
}

//
// C decompress function, returns actual decompressed size
// Stops when either olen is reached or when ilen is exhausted
// returns the number of output bytes written
//
static size_t fromYarn(const char *ibuffer, size_t ilen, char *obuf, size_t olen, Byte CODE = 0xC3) {

    // Get a byte, after checking that it can be read, return otherwise
#define GET_BYTE(X) do {if (0 == ilen--) RET_NOW; X = UC(*ibuffer++);} while(0)

    Byte *next = reinterpret_cast<Byte *>(obuf);
    while (ilen > 0 && olen > 0) {
        Byte b;
        GET_BYTE(b);
        if (b != CODE) { // Copy single chars
            *next++ = b;
            olen--;
            continue;
        }

        // Sequence marker found, which type is it?
        GET_BYTE(b);
        if (0 == b) { // Escape sequence, emit one code
            *next++ = CODE;
            olen--;
            continue;
        }

        // Sequence
        size_t run = b;
        if (b < 4) {
            run *= 256;
            GET_BYTE(b);
            if (run == 768) { // Long sequence, b is high byte
                run += 256 * b;
                GET_BYTE(b);
            }
            run += b;
        }
        GET_BYTE(b); // the value

        // Write the sequence out, after checking that it can be done
        if (olen < run)
            RET_NOW;
        memset(next, b, run);
        next += run;
        olen -= run;
    }
    RET_NOW;

#undef GET_BYTE
}

// Returns the least used byte value from a buffer
static Byte getLeastUsed(const Byte *src, size_t len) {
    std::vector<unsigned int> hist(256, 0);
    while (len--)
        hist[*src++]++;
    return UC(std::min_element(hist.begin(), hist.end()) - hist.begin());
}

// Read from a packed source until the src is exhausted
// Returns true if all output buffer was filled, 0 otherwise
DLL_LOCAL int RLEC3Packer::load(storage_manager *src, storage_manager *dst)
{
    // Use the first char in the input buffer as marker code
    auto s = reinterpret_cast<char*>(src->buffer);
    auto d = reinterpret_cast<char*>(dst->buffer);
    auto c = static_cast<Byte>(*s++);
    return dst->size == fromYarn(s, src->size - 1, d, dst->size, c);
}

//
// Picks the least use value as the marker code and stores it first in the data
// This choice improves the worst case expansion, which becomes (1 + N / 256 + N) : N
// It also improves compression in general
// Makes best case marginally worse because the chosen code adds one byte to the output
//

DLL_LOCAL int RLEC3Packer::store(storage_manager *src, storage_manager *dst)
{
    auto s = reinterpret_cast<Byte*>(src->buffer);
    auto d = reinterpret_cast<char*>(dst->buffer);
    if (dst->size < 1 + src->size + src->size / 256)
        return 0; // Failed, destination might overflow
    Byte c = getLeastUsed(s, src->size);
    *d++ = static_cast<char>(c);
    dst->size = 1 + toYarn(reinterpret_cast<const char *>(s), d, src->size, c);
    return 1; // Success, size is in dst->size
}
