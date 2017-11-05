/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include <stdint.h>
#include <string.h>

#include <libopencm3/stm32/desig.h>

#include "serialno.h"
#include "util.h"
#include "sha2.h"

void fill_serialno_fixed(char *s)
{
	uint32_t uuid[8];
	desig_get_unique_id(uuid);
	sha256_Raw((const uint8_t *)uuid, 12, (uint8_t *)uuid);
	sha256_Raw((const uint8_t *)uuid, 32, (uint8_t *)uuid);
	data2hex(uuid, 12, s);
}
