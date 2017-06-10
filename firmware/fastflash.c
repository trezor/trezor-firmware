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

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <libopencm3/cm3/scb.h>

extern uint32_t __bootloader_loadaddr__[];
extern uint32_t __bootloader_runaddr__[];
extern uint8_t __bootloader_size__[];

void load_bootloader() {
	memcpy(__bootloader_runaddr__, __bootloader_loadaddr__, (size_t) __bootloader_size__);
}

void run_bootloader() {
	// Relocate vector tables
	SCB_VTOR = (uint32_t) __bootloader_runaddr__;

	// Set stack pointer
	__asm__ volatile("msr msp, %0":: "r" (__bootloader_runaddr__[0]));

	// Jump to address
	((void (*)(void))(__bootloader_runaddr__[1]))();

	while (true);
}
