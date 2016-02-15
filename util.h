/*
 * This file is part of the TREZOR project.
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

#ifndef __UTIL_H_
#define __UTIL_H_

#include <stdint.h>

void delay(uint32_t wait);

// converts uint32 to hexa (8 digits)
void uint32hex(uint32_t num, char *str);

// converts data to hexa
void data2hex(const void *data, uint32_t len, char *str);

// read protobuf integer and advance pointer
uint32_t readprotobufint(uint8_t **ptr);

// halt execution (or do an endless loop)
void __attribute__((noreturn)) system_halt(void);
// reset system
void __attribute__((noreturn)) system_reset(void);

#endif
