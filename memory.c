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

#include <libopencm3/stm32/flash.h>
#include <stdint.h>
#include "memory.h"
#include "sha2.h"

#define OPTION_BYTES_1 ((uint64_t *)0x1FFFC000)
#define OPTION_BYTES_2 ((uint64_t *)0x1FFFC008)

void memory_protect(void)
{
	//                     set RDP level 2                   WRP for sectors 0 and 1
	if ((((*OPTION_BYTES_1) & 0xFFFF) == 0xCCFF) && (((*OPTION_BYTES_2) & 0xFFFF) == 0xFFFC)) {
		return; // already set up correctly - bail out
	}
	flash_unlock_option_bytes();
	//                                WRP +    RDP
	flash_program_option_bytes(0xFFFC0000 + 0xCCFF);
	flash_lock_option_bytes();
}

int memory_bootloader_hash(uint8_t *hash)
{
	sha256_Raw((const uint8_t *)FLASH_BOOT_START, FLASH_BOOT_LEN, hash);
	sha256_Raw(hash, 32, hash);
	return 32;
}
