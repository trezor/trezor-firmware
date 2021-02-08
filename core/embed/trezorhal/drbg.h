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

#ifndef __TREZORHAL_DRBG_H__
#define __TREZORHAL_DRBG_H__

#include <stddef.h>
#include <stdint.h>

void drbg_init(void);
void drbg_reseed(const uint8_t *entropy, size_t len);
void drbg_generate(uint8_t *buf, size_t len);
uint32_t drbg_random32(void);
#endif
