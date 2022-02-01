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

#ifndef __COMPILER_TRAITS_H__
#define __COMPILER_TRAITS_H__

/*
 * Avoid accidental build with gcc versions having broken stack protector.
 * Affected versions range 9.2.1 - 10.2.0
 */
#if defined(__GNUC__) && !defined(__llvm__)

#define GCC_VERSION \
  (__GNUC__ * 10000 + __GNUC_MINOR__ * 100 + __GNUC_PATCHLEVEL__)

#if !EMULATOR && GCC_VERSION >= 90201 && GCC_VERSION <= 100200
#pragma message \
    "Only remove this GCC check if you are sure your compiler is patched or not used for production."
#error \
    "ARM GCC versions 9.2.1 - 10.2.0 have broken stack smash protector, aborting build."
#endif
#endif

#endif
