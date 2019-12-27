/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __TREZOR_H__
#define __TREZOR_H__

#include <stdint.h>
#include "version.h"

#define STR(X) #X
#define VERSTR(X) STR(X)

#ifndef DEBUG_LINK
#define DEBUG_LINK 0
#endif

#ifndef DEBUG_LOG
#define DEBUG_LOG 0
#endif

/* Screen timeout */
extern uint32_t system_millis_lock_start;

#endif
