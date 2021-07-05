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

#ifndef __TREZORHAL_COMMON_H__
#define __TREZORHAL_COMMON_H__

#include "secbool.h"

void __fatal_error(const char *expr, const char *msg, const char *file,
                   int line, const char *func);
void error_shutdown(const char *line1, const char *line2, const char *line3,
                    const char *line4);

#define ensure(expr, msg) \
  (((expr) == sectrue)    \
       ? (void)0          \
       : __fatal_error(#expr, msg, __FILE__, __LINE__, __func__))

#define hal_delay(ms) (void)ms;

#endif
