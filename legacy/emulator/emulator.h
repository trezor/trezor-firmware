/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

#ifndef __EMULATOR_H__
#define __EMULATOR_H__

#if EMULATOR

#include "strl.h"

#include <stddef.h>

void emulatorPoll(void);
void emulatorRandom(void *buffer, size_t size);

void emulatorSocketInit(void);
size_t emulatorSocketRead(int *iface, void *buffer, size_t size,
                          int timeout_ms);
size_t emulatorSocketWrite(int iface, const void *buffer, size_t size);

#endif

#endif
