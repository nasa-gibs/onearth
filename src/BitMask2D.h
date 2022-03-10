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
 * File: BitMask2D.h
 *
 * Purpose: A 2D bitmask, stored as 64bit units, with an RLE encoding.
 * Used for the JPEG-Zen extension
 *
 * Author:  Lucian Plesea 2016-2020
 */

/*

A 2D bitmask stored in 4x4 or 8x8 units
While it is a template over unit type, the only valid types are 
unsigned 16bit and unsigned 64bit

Obviously not thread safe while any bit gets modified

*/
#if !defined(BITMASK2D_H)
#define BITMASK2D_H
#include <vector>
#include <stdexcept>
#include <cstring>

// Defines the storage_manager
#include "icd_codecs.h"

#if defined(IS_BIGENDIAN)
#error Not implemented for big endian
#endif

NS_ICD_START

// A base class that provides import and export functions based on storage managers
// Default implementation is a straight copy
class Packer {
public:
    virtual ~Packer() {}
    virtual int load(storage_manager *src, storage_manager *dst)
    {
        if (dst->size < src->size)
            return false;
        memcpy(dst->buffer, src->buffer, src->size);
        dst->size -= src->size; // Adjust the destination size
        return true;
    }

    virtual int store(storage_manager *src, storage_manager *dst)
    {
        return load(src, dst);
    }
};

// integer sqrt at compile time
// N is the number, M is the number of refining iterations
template<int N, int M = 4> struct Sqrt {
    static const int value = 
        (Sqrt<N, M - 1>::value + N / Sqrt<N, M - 1>::value) / 2;
};

// End condition
template<int N> struct Sqrt<N, 0> {
    static const int value = N / 2;
};

// Round up division by N
template<unsigned int N> static int Chunks(int x) {
    return 1 + (x - 1) / N;
}

//// These exist in C++11, so we name them with upper case
//template < typename T1, typename T2 > struct Is_Same {
//    enum { value = false }; // is_same represents a bool.
//    typedef Is_Same<T1, T2> type; // to qualify as a metafunction.
//};
//
//
////// Specialization
//template < typename T > struct Is_Same<T,T> {
//    enum { value = true };
//    typedef Is_Same<T, T> type;
//};
//

// linear size of storage unit, 4 or 8
#define TGSIZE Sqrt<sizeof(T)*8>::value

template<typename T = unsigned long long> class BitMap2D {
public:
    // Initialized to all bits set
    BitMap2D(unsigned int width, unsigned int height) : _w(width), _h(height)
    {
        // Prevent creation of bitmasks using any other types

        // Uncomment these statements to enforce only 64 and 16 bit units
        // They work but generate warnings on some compilers
        // Is_Same<T, unsigned long long>::type a;
        // Is_Same<T, unsigned short>::type b;
        // if (!(a.value || b.value))
        //   throw std::out_of_range("Only bitmap units of unsigned 16 and 64 bits work");

        // Precalculate row size in storage units, for speed
        _lw = Chunks<TGSIZE>(_w);
        // Defaults to all set
        init(~(T)0);
#if defined(PACKER)
        _packer = nullptr;
#endif
    }

    int getWidth() const { return _w; }
    int getHeight() const { return _h; }

    // Size in bytes
    size_t size() const {
        return _bits.size() * sizeof(T); 
    }

    // Returns the condition of a specific bit
    bool isSet(int x, int y) const {
        return 0 != (_bits[_idx(x, y)] & _bitmask(x, y));
    }

    void set(int x, int y) {
        _bits[_idx(x, y)] |= _bitmask(x, y);
    }

    void clear(int x, int y) {
        _bits[_idx(x, y)] &= ~_bitmask(x, y);
    }

    // Set a location bit to true or false
    void assign(int x, int y, bool val = true) {
        if (val) set(x,y);
        else clear(x,y);
    }

    // Flip a bit
    void flip(int x, int y) {
        _bits[_idx(x, y)] ^= _bitmask(x, y);
    }

    // Set all units to same bit pattern by unit
    // Use init(~(T)0)) for all set
    void init(T val) {
        _bits.assign(Chunks<TGSIZE>(_w) * Chunks<TGSIZE>(_h), val);
    }

 // Support for store and load
    void set_packer(Packer *packer) { _packer = packer; }

    int store(storage_manager *dst) {
        int result;
        storage_manager src(_bits.data(), size());
        // Store the mask units in little endian format
        // Swab only does something on big endian architectures
        swab();
        if (_packer)
            result = _packer->store(&src, dst);
        else
            result = Packer().store(&src, dst);
        // Convert it back to machine order
        swab();
        return result;
    }

    int load(storage_manager *src) {
        int result;
        storage_manager dst(_bits.data(), size());
        if (_packer)
            result = _packer->load(src, &dst);
        else
            result = Packer().load(src, &dst);
        // Input is always little endian, convert it to machine order
        swab();
        return result;
    }

private:
    // unit index
    unsigned int _idx(int x, int y) const {
        return  _lw * (y / TGSIZE) + x / TGSIZE;
    }

    // one bit mask within a unit
    static T _bitmask(int x, int y) {
        return static_cast<T>(1) << (TGSIZE * (y % TGSIZE) + x % TGSIZE);
    }

// Swap bytes of storage units within the bitmap to low endian
    static void swab() {}

    // Class that provides export and import capabilities, not owned
    Packer *_packer;

    // bit storage vector
    std::vector<T> _bits;
    // width and height of bitmap
    unsigned int _w, _h;
    // Line size in linear chunks
    unsigned int _lw;
};

#undef TGSIZE

class RLEC3Packer :public Packer {
public:
    virtual int load(storage_manager *src, storage_manager *dst) override;
    virtual int store(storage_manager *src, storage_manager *dst) override;
};

NS_END

#endif
