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

#include <stdint.h>
#include <string.h>
#include "blake2s.h"
#include "common.h"
#include "flash.h"

// symbols from bootloader.bin => bootloader.o
extern const uint32_t _binary_embed_firmware_bootloader_bin_start;
extern const uint32_t _binary_embed_firmware_bootloader_bin_size;

/*
static secbool known_bootloader(const uint8_t *hash, int len) {
    if (len != 32) return secfalse;
    // bootloader-2.0.1.bin (padded with 0x00)
    if (0 == memcmp(hash,
"\x91\x37\x46\xd0\x2d\xa7\xc4\xbe\x1d\xae\xef\xb0\x9b\x4e\x31\x88\xed\x38\x23\x5e\x0e\x31\xa7\x8c\x01\xde\x4e\xcc\xc2\xd6\x36\xb3",
32)) return sectrue;
    // bootloader-2.0.1.bin (padded with 0xff)
    if (0 == memcmp(hash,
"\x2f\xdb\xde\x94\x0a\xd8\x91\x1c\xbd\x07\xb0\xba\x06\x2c\x90\x84\x02\xec\x95\x19\xde\x52\x8d\x4b\xe9\xb9\xed\x30\x71\x91\xb4\xd3",
32)) return sectrue;
    // bootloader-2.0.2.bin (padded with 0x00)
    if (0 == memcmp(hash,
"\x2e\xf7\x47\xf8\x49\x87\x1e\xc8\xc6\x01\x35\xd6\x32\xe5\x5a\xd1\x56\x18\xf8\x64\x87\xb7\xaa\x7c\x62\x0e\xc3\x0d\x25\x69\x4e\x18",
32)) return sectrue;
    // bootloader-2.0.2.bin (padded with 0xff)
    if (0 == memcmp(hash,
"\xcc\x6b\x35\xc3\x8f\x29\x5c\xbd\x7d\x31\x69\xaf\xae\xf1\x61\x01\xef\xbe\x9f\x3b\x0a\xfd\xc5\x91\x70\x9b\xf5\xa0\xd5\xa4\xc5\xe0",
32)) return sectrue;
    // bootloader-2.0.3.bin (padded with 0x00)
    if (0 == memcmp(hash,
"\xb1\x83\xd3\x31\xc7\xff\x3d\xcf\x54\x1e\x7e\x40\xf4\x9e\xc3\x53\x4c\xcc\xf3\x8c\x35\x39\x88\x81\x65\xc0\x5c\x25\xbd\xfc\xea\x14",
32)) return sectrue;
    // bootloader-2.0.3.bin (padded with 0xff)
    if (0 == memcmp(hash,
"\xab\xdb\x7d\xe2\xef\x44\x66\xa7\xb7\x1f\x2b\x02\xf3\xe1\x40\xe7\xcd\xf2\x8e\xc0\xbb\x33\x04\xce\x0d\xa5\xca\x02\x57\xb6\xd4\x30",
32)) return sectrue; return secfalse;
}
*/

static secbool latest_bootloader(const uint8_t *hash, int len) {
  if (len != 32) return secfalse;
  // bootloader.bin (padded with 0x00)
  if (0 ==
      memcmp(hash,
             "\xb1\x83\xd3\x31\xc7\xff\x3d\xcf\x54\x1e\x7e\x40\xf4\x9e\xc3\x53"
             "\x4c\xcc\xf3\x8c\x35\x39\x88\x81\x65\xc0\x5c\x25\xbd\xfc\xea\x14",
             32))
    return sectrue;
  // bootloader.bin (padded with 0xff)
  if (0 ==
      memcmp(hash,
             "\xab\xdb\x7d\xe2\xef\x44\x66\xa7\xb7\x1f\x2b\x02\xf3\xe1\x40\xe7"
             "\xcd\xf2\x8e\xc0\xbb\x33\x04\xce\x0d\xa5\xca\x02\x57\xb6\xd4\x30",
             32))
    return sectrue;
  return secfalse;
}

void check_and_replace_bootloader(void) {
  // compute current bootloader hash
  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  const uint32_t bl_len = 128 * 1024;
  const void *bl_data = flash_get_address(FLASH_SECTOR_BOOTLOADER, 0, bl_len);
  blake2s(bl_data, bl_len, hash, BLAKE2S_DIGEST_LENGTH);

  // don't whitelist the valid bootloaders for now
  // ensure(known_bootloader(hash, BLAKE2S_DIGEST_LENGTH), "Unknown bootloader
  // detected");

  // do we have the latest bootloader?
  if (sectrue == latest_bootloader(hash, BLAKE2S_DIGEST_LENGTH)) {
    return;
  }

  // replace bootloader with the latest one
  const uint32_t *data =
      (const uint32_t *)&_binary_embed_firmware_bootloader_bin_start;
  const uint32_t len =
      (const uint32_t)&_binary_embed_firmware_bootloader_bin_size;
  ensure(flash_erase(FLASH_SECTOR_BOOTLOADER), NULL);
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < len / sizeof(uint32_t); i++) {
    ensure(flash_write_word(FLASH_SECTOR_BOOTLOADER, i * sizeof(uint32_t),
                            data[i]),
           NULL);
  }
  for (int i = len / sizeof(uint32_t); i < 128 * 1024 / sizeof(uint32_t); i++) {
    ensure(flash_write_word(FLASH_SECTOR_BOOTLOADER, i * sizeof(uint32_t),
                            0x00000000),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
}
