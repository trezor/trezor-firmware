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

#ifndef LIB_ASSERT_H
#define LIB_ASSERT_H

// This file overrides the standard `assert` macro to
// save space in flash memory.
//
// This file will be included instead of the standard assert.h
// as it is passed to the compiler with -include before the
// paths to the standard libraries.
//
// Our custom assert macro eliminates printing of the
// expression and prints only a short file name and line number.

#ifdef __cplusplus
extern "C" {
#endif

#ifndef NDEBUG

void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line);

#define assert(expr) \
  ((expr) ? (void)0 : __fatal_error("Assert", __FILE_NAME__, __LINE__))

#else

#define assert(expr) ((void)0)

#endif

#ifdef __cplusplus
}
#endif

#endif  // LIB_ASSERT_H
