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

#ifndef PRODTEST_COMMON_H
#define PRODTEST_COMMON_H

#include <stdint.h>
#include <stdlib.h>

enum { VCP_IFACE = 0x00 };

void vcp_puts(const char *s, size_t len);
void vcp_print(const char *fmt, ...);
void vcp_println(const char *fmt, ...);
void vcp_println_hex(uint8_t *data, uint16_t len);
int get_from_hex(uint8_t *buf, uint16_t buf_len, const char *hex);

#endif
