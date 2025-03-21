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

#ifndef TREZOR_RTL_H
#define TREZOR_RTL_H

// `trezor_rtl.h` consolidates common includes for implementation files
// (.c files) and provides essential types and functions.
//
// Do not include `trezor_rtl.h` in interface headers to prevent global
// namespace pollution; use `trezor_types.h` instead.

#include <trezor_types.h>

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "rtl/compiler_traits.h"
#include "rtl/error_handling.h"

#ifndef MIN_8bits
#define MIN_8bits(a, b)                  \
  ({                                     \
    typeof(a) _a = (a);                  \
    typeof(b) _b = (b);                  \
    _a < _b ? (_a & 0xFF) : (_b & 0xFF); \
  })
#endif
#ifndef MIN
#define MIN(a, b)       \
  ({                    \
    typeof(a) _a = (a); \
    typeof(b) _b = (b); \
    _a < _b ? _a : _b;  \
  })
#endif
#ifndef MAX
#define MAX(a, b)       \
  ({                    \
    typeof(a) _a = (a); \
    typeof(b) _b = (b); \
    _a > _b ? _a : _b;  \
  })
#endif

#define ARRAY_LENGTH(x) (sizeof(x) / sizeof((x)[0]))

#ifndef UNUSED
#define UNUSED(x) (void)(x)
#endif

#endif  // TREZOR_RTL_H
