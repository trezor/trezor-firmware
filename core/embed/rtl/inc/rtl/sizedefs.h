/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef LIB_SIZEDEFS_H
#define LIB_SIZEDEFS_H

#define SIZE_2K (2 * 1024)
#define SIZE_3K (3 * 1024)
#define SIZE_8K (8 * 1024)
#define SIZE_16K (16 * 1024)
#define SIZE_24K (24 * 1024)
#define SIZE_48K (48 * 1024)
#define SIZE_64K (64 * 1024)
#define SIZE_128K (128 * 1024)
#define SIZE_192K (192 * 1024)
#define SIZE_256K (256 * 1024)
#define SIZE_320K (320 * 1024)
#define SIZE_768K (768 * 1024)
#define SIZE_2496K (2496 * 1024)
#define SIZE_3712K ((4096 - 384) * 1024)
#define SIZE_3776K ((4096 - 320) * 1024)
#define SIZE_3904K ((4096 - 192) * 1024)
#define SIZE_4032K ((4096 - 64) * 1024)
#define SIZE_2M (2 * 1024 * 1024)
#define SIZE_4M (4 * 1024 * 1024)
#define SIZE_16M (16 * 1024 * 1024)
#define SIZE_256M (256 * 1024 * 1024)
#define SIZE_512M (512 * 1024 * 1024)

// Checks if a value 'x' is a power of two.
#define IS_POWER_OF_TWO(x) (((x) != 0) && (((x) & ((x)-1)) == 0))

// Ensures at compile-time that 'x' is a power of two.
#define ENSURE_POWER_OF_TWO(x) \
  _Static_assert(IS_POWER_OF_TWO(x), "Value must be a power of two")

// Checks if 'addr' is properly aligned to 'align', which must be a
// power of two.
#define IS_ALIGNED(addr, align)    \
  ({                               \
    ENSURE_POWER_OF_TWO(align);    \
    (((addr) & ((align)-1)) == 0); \
  })

// Ensures that that 'addr' is properly aligned to 'align', which
// must be a power of two.
#define ENSURE_ALIGNMENT(addr, align) \
  _Static_assert(IS_ALIGNED(addr, align), "Address must be aligned")

// Aligns 'addr' upwards to the next boundary of 'align', which must
// be a power of two.
#define ALIGN_UP(addr, align)              \
  ({                                       \
    ENSURE_POWER_OF_TWO(align);            \
    (((addr) + (align)-1) & ~((align)-1)); \
  })

// Aligns 'addr' upwards to the next boundary of 'align', which must
// be a power of two.
//
// This version is for use in constant expressions. Use only if `ALIGN_UP`
// doesn't work in your case.
#define ALIGN_UP_CONST(addr, align) (((addr) + (align)-1) & ~((align)-1))

// Aligns 'addr' downwards to the previous boundary of 'align', which
// must be a power of two.
#define ALIGN_DOWN(addr, align) \
  ({                            \
    ENSURE_POWER_OF_TWO(align); \
    ((addr) & ~((align)-1));    \
  })

// Aligns 'addr' downwards to the previous boundary of 'align', which
// must be a power of two.
//
// This version is for use in constant expressions. Use only if `ALIGN_DOWN`
// doesn't work in your case.
#define ALIGN_DOWN_CONST(addr, align) ((addr) & ~((align)-1))

#endif  // LIB_SIZEDEFS_H
