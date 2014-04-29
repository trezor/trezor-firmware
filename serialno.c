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

#include <stdint.h>
#include <string.h>

#include "serialno.h"
#include "util.h"
#include "sha2.h"

#if defined(STM32F4) || defined(STM32F2)
#define UNIQUE_SERIAL_ADDR 0x1FFF7A10
#elif defined(STM32F3)
#define UNIQUE_SERIAL_ADDR 0x1FFFF7AC
#elif defined(STM32L1)
#define UNIQUE_SERIAL_ADDR 0x1FF80050
#else // STM32F1
#define UNIQUE_SERIAL_ADDR 0x1FFFF7E8
#endif

void fill_serialno_fixed(char *s)
{
	uint8_t uuid[32];
	memcpy(uuid, (uint8_t *)UNIQUE_SERIAL_ADDR, 12);
	memcpy(uuid + 12, (uint8_t *)UNIQUE_SERIAL_ADDR, 12);
	memcpy(uuid + 24, (uint8_t *)UNIQUE_SERIAL_ADDR, 8);
	sha256_Raw(uuid, 32, uuid);
	sha256_Raw(uuid, 32, uuid);
	data2hex(uuid, 12, s);
}
