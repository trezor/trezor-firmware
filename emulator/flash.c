/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include <string.h>
#include <assert.h>
#include <stdbool.h>

#include "memory.h"

void flash_lock(void) {}
void flash_unlock(void) {}

void flash_clear_status_flags(void) {}

void flash_lock_option_bytes(void) {}
void flash_unlock_option_bytes(void) {}

void flash_program_option_bytes(uint32_t data) {
	(void) data;
}

static ssize_t sector_to_offset(uint8_t sector) {
	switch (sector) {
	case 0:
		return 0x0;
	case 1:
		return 0x4000;
	case 2:
		return 0x8000;
	case 3:
		return 0xC000;
	case 4:
		return 0x10000;
	case 5:
		return 0x20000;
	case 6:
		return 0x40000;
	case 7:
		return 0x60000;
	case 8:
		return 0x80000;
	default:
		return -1;
	}
}

static void *sector_to_address(uint8_t sector) {
	ssize_t offset = sector_to_offset(sector);
	if (offset < 0) {
		return NULL;
	}

	return (void *) FLASH_PTR(FLASH_ORIGIN + offset);
}

static ssize_t sector_to_size(uint8_t sector) {
	ssize_t start = sector_to_offset(sector);
	if (start < 0) {
		return -1;
	}

	ssize_t end = sector_to_offset(sector + 1);
	if (end < 0) {
		return -1;
	}

	return end - start;
}

void flash_erase_sector(uint8_t sector, uint32_t program_size) {
	(void) program_size;

	void *address = sector_to_address(sector);
	if (address == NULL) {
		return;
	}

	ssize_t size = sector_to_size(sector);
	if (size < 0) {
		return;
	}

	memset(address, 0xFF, size);
}

void flash_erase_all_sectors(uint32_t program_size) {
	(void) program_size;

	memset(emulator_flash_base, 0xFF, FLASH_TOTAL_SIZE);
}

void flash_program_word(uint32_t address, uint32_t data) {
	*(volatile uint32_t *)FLASH_PTR(address) = data;
}

void flash_program_byte(uint32_t address, uint8_t data) {
	*(volatile uint8_t *)FLASH_PTR(address) = data;
}

static bool flash_locked = true;
void svc_flash_unlock(void) {
	assert (flash_locked);
	flash_locked = false;
}
void svc_flash_program(uint32_t size) {
	(void) size;
	assert (!flash_locked);
}
void svc_flash_erase_sector(uint16_t sector) {
	assert (!flash_locked);
	assert (sector >= FLASH_META_SECTOR_FIRST &&
			sector <= FLASH_META_SECTOR_LAST);
	flash_erase_sector(sector, 3);
}
uint32_t svc_flash_lock(void) {
	assert (!flash_locked);
	flash_locked = true;
	return 0;
}
