/*
 * This file is part of the TREZOR project.
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

#include "fastflash.h"
#include "util.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

extern uint8_t __bootloader_loadaddr__[];
extern uint8_t __bootloader_runaddr__[];
extern uint8_t __bootloader_size__[];

void load_bootloader(void)
{
	memcpy(__bootloader_runaddr__, __bootloader_loadaddr__, (size_t) __bootloader_size__);
}

void __attribute__((noreturn)) run_bootloader(void)
{
	load_vector_table((const vector_table_t *) __bootloader_runaddr__);
}
