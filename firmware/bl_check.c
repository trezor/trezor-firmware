/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
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
#include <libopencm3/stm32/flash.h>
#include "bl_data.h"
#include "memory.h"
#include "layout.h"
#include "gettext.h"
#include "util.h"

int known_bootloader(int r, const uint8_t *hash) {
	if (r != 32) return 0;
	if (0 == memcmp(hash, "\xbf\x72\xe2\x5e\x2c\x2f\xc1\xba\x57\x04\x50\xfa\xdf\xb6\x6f\xaa\x5a\x71\x6d\xcd\xc0\x33\x35\x88\x55\x7b\x77\x54\x0a\xb8\x7e\x98", 32)) return 1;  // 1.2.0a
	if (0 == memcmp(hash, "\x77\xb8\xe2\xf2\x5f\xaa\x8e\x8c\x7d\x9f\x5b\x32\x3b\x27\xce\x05\x6c\xa3\xdb\xc2\x3f\x56\xc3\x7e\xe3\x3f\x97\x7c\xa6\xeb\x4d\x3e", 32)) return 1;  // 1.2.0b
	if (0 == memcmp(hash, "\xc4\xc3\x25\x39\xb4\xa0\x25\xa8\xe7\x53\xa4\xc4\x62\x64\x28\x59\x11\xa4\x5f\xcb\x14\xf4\x71\x81\x79\xe7\x11\xb1\xce\x99\x05\x24", 32)) return 1;  // 1.2.5
	if (0 == memcmp(hash, "\x42\x59\x66\x94\xa0\xf2\x9d\x1e\xc2\x35\x71\x29\x2d\x54\x39\xd8\x2f\xa1\x8c\x07\x37\xcb\x10\x7e\x98\xf6\x1e\xf5\x93\x4d\xe7\x16", 32)) return 1;  // 1.3.0a
	if (0 == memcmp(hash, "\x3a\xcf\x2e\x51\x0b\x0f\xe1\x56\xb5\x58\xbb\xf7\x9c\x7e\x48\x5e\xb0\x26\xe5\xe0\x8c\xb4\x4d\x15\x2d\x44\xd6\x4e\x0c\x6a\x41\x37", 32)) return 1;  // 1.3.0b
	if (0 == memcmp(hash, "\x15\x85\x21\x5b\xc6\xe5\x5a\x34\x07\xa8\xb3\xee\xe2\x79\x03\x4e\x95\xb9\xc4\x34\x00\x33\xe1\xb6\xae\x16\x0c\xe6\x61\x19\x67\x15", 32)) return 1;  // 1.3.1
	if (0 == memcmp(hash, "\x76\x51\xb7\xca\xba\x5a\xae\x0c\xc1\xc6\x5c\x83\x04\xf7\x60\x39\x6f\x77\x60\x6c\xd3\x99\x0c\x99\x15\x98\xf0\xe2\x2a\x81\xe0\x07", 32)) return 1;  // 1.3.2
	// note to those verifying these values: bootloader versions above this comment are aligned/padded to 32KiB with trailing 0xFF bytes and versions below are padded with 0x00.
	//                                       for more info, refer to "make -C bootloader align" and "firmware/bl_data.py".
	if (0 == memcmp(hash, "\x8c\xe8\xd7\x9e\xdf\x43\x0c\x03\x42\x64\x68\x6c\xa9\xb1\xd7\x8d\x26\xed\xb2\xac\xab\x71\x39\xbe\x8f\x98\x5c\x2a\x3c\x6c\xae\x11", 32)) return 1;  // 1.3.3
	if (0 == memcmp(hash, "\x63\x30\xfc\xec\x16\x72\xfa\xd3\x0b\x42\x1b\x60\xf7\x4f\x83\x9a\x39\x39\x33\x45\x65\xcb\x70\x3b\x2b\xd7\x18\x2e\xa2\xdd\xa0\x19", 32)) return 1;  // 1.4.0
	return 0;
}

void check_bootloader(void)
{
#if MEMORY_PROTECT
	uint8_t hash[32];
	int r = memory_bootloader_hash(hash);

	if (!known_bootloader(r, hash)) {
		layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Unknown bootloader", "detected.", NULL, "Unplug your TREZOR", "contact our support.", NULL);
		shutdown();
	}

	if (is_mode_unprivileged()) {
		return;
	}

	if (r == 32 && 0 == memcmp(hash, bl_hash, 32)) {
		// all OK -> done
		return;
	}

	// ENABLE THIS AT YOUR OWN RISK
	// ATTEMPTING TO OVERWRITE BOOTLOADER WITH UNSIGNED FIRMWARE MAY BRICK
	// YOUR DEVICE.

	layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Overwriting bootloader", NULL, NULL, "DON'T UNPLUG", "YOUR TREZOR", NULL);

	// unlock sectors
	memory_write_unlock();

	// replace bootloader
	flash_unlock();
	for (int i = FLASH_BOOT_SECTOR_FIRST; i <= FLASH_BOOT_SECTOR_LAST; i++) {
		flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
	}
	for (int i = 0; i < FLASH_BOOT_LEN / 4; i++) {
		const uint32_t *w = (const uint32_t *)(bl_data + i * 4);
		flash_program_word(FLASH_BOOT_START + i * 4, *w);
	}
	flash_lock();

	// show info and halt
	layoutDialog(&bmp_icon_info, NULL, NULL, NULL, _("Update finished"), _("successfully."), NULL, _("Please reconnect"), _("the device."), NULL);
	shutdown();
#endif
}
