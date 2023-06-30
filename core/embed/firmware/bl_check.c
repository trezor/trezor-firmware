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
#include "board_capabilities.h"
#include "common.h"
#include "flash.h"
#include "image.h"
#include "model.h"

// symbols from bootloader.bin => bootloader.o
extern const void _binary_embed_firmware_bootloader_bin_start;
extern const void _binary_embed_firmware_bootloader_bin_size;

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

// clang-format off
// --- BEGIN GENERATED BOOTLOADER SECTION ---
// bootloader_T1B1.bin version <unknown>
#define BOOTLOADER_T1B1_00 {0xc1, 0x01, 0xd3, 0x8a, 0x00, 0x5e, 0x4f, 0x5f, 0x87, 0x1f, 0x49, 0x78, 0x24, 0x9c, 0xf9, 0x82, 0xd1, 0x91, 0x4b, 0xa6, 0x90, 0x03, 0x9c, 0x50, 0x49, 0x61, 0x10, 0x4f, 0xee, 0xe7, 0x1d, 0x7b}
#define BOOTLOADER_T1B1_FF {0xbd, 0xb2, 0xf7, 0x62, 0xfb, 0x10, 0xbb, 0x30, 0x1f, 0x95, 0xa3, 0x12, 0x6b, 0x41, 0x1f, 0x66, 0xfc, 0x57, 0x28, 0xce, 0x7f, 0x59, 0x42, 0x6c, 0x3e, 0xed, 0xf7, 0x69, 0xbb, 0x96, 0xbd, 0x4b}
// bootloader_T2B1.bin version 2.0.5.0
#define BOOTLOADER_T2B1_00 {0xf1, 0x3d, 0x46, 0x21, 0xec, 0xf9, 0x92, 0xfb, 0x5c, 0x50, 0xaf, 0xdb, 0x55, 0x13, 0x0e, 0x7f, 0xbe, 0x5b, 0x30, 0x37, 0xc9, 0x17, 0xff, 0xf5, 0xe7, 0xd7, 0xe9, 0x1d, 0x09, 0x5c, 0xf3, 0x2a}
#define BOOTLOADER_T2B1_FF {0xa9, 0xf0, 0x63, 0xfd, 0x8a, 0xe7, 0x6c, 0x52, 0x92, 0xcb, 0x11, 0x69, 0x87, 0x79, 0x62, 0x11, 0x1e, 0x01, 0x1e, 0xf1, 0xb5, 0xd9, 0x20, 0x16, 0x4d, 0x2c, 0x16, 0x41, 0x0d, 0xa1, 0xe7, 0xc8}
// bootloader_1.bin version <unknown>
#define BOOTLOADER_1_00 {0xa5, 0x5a, 0x8b, 0x88, 0x94, 0x8a, 0x33, 0x2b, 0xed, 0x0d, 0xd9, 0x5c, 0x79, 0xd5, 0xbe, 0x0c, 0x73, 0x52, 0xaa, 0xac, 0xb3, 0x4f, 0xea, 0xd0, 0xaa, 0x88, 0x33, 0x23, 0x64, 0xab, 0x77, 0x5a}
#define BOOTLOADER_1_FF {0x50, 0x6c, 0x5f, 0xd3, 0x73, 0x7b, 0x9b, 0xb7, 0xb9, 0xbf, 0xf9, 0xfa, 0xc6, 0xb9, 0x43, 0x27, 0x8b, 0x06, 0xad, 0x3a, 0xec, 0xce, 0x35, 0xa3, 0x52, 0xc3, 0x6e, 0x9e, 0x9a, 0xb3, 0x50, 0x98}
// bootloader_T2T1_qa.bin version 2.1.0.0
#define BOOTLOADER_T2T1_QA_00 {0xce, 0xb2, 0x6d, 0xc9, 0x1d, 0x61, 0xaa, 0x91, 0x45, 0xf6, 0xc2, 0xfe, 0xf7, 0xef, 0xe7, 0xf9, 0x23, 0x24, 0xfa, 0xf5, 0x4d, 0xce, 0xb8, 0x48, 0xf5, 0xfa, 0x3b, 0x48, 0x67, 0x45, 0x73, 0xfc}
#define BOOTLOADER_T2T1_QA_FF {0xa5, 0x58, 0xf4, 0x97, 0xe8, 0x1a, 0x9d, 0xa5, 0xe6, 0x05, 0xb2, 0x3c, 0x35, 0x88, 0x01, 0x80, 0x8d, 0xe4, 0xd2, 0xc9, 0x3e, 0x4a, 0x28, 0x13, 0x67, 0xc2, 0x15, 0x61, 0xf8, 0x42, 0x06, 0x52}
// bootloader_T2T1.bin version 2.1.0.0
#define BOOTLOADER_T2T1_00 {0x16, 0x1c, 0x71, 0x92, 0xe0, 0xdb, 0x35, 0x68, 0xd3, 0xae, 0xed, 0x97, 0xc7, 0x2b, 0x24, 0xc5, 0x43, 0x4f, 0x0c, 0x3c, 0xb8, 0x16, 0x60, 0x12, 0x34, 0x10, 0x8d, 0xc1, 0xd5, 0x58, 0xb5, 0x4a}
#define BOOTLOADER_T2T1_FF {0xe0, 0xd5, 0x96, 0x9f, 0x30, 0xab, 0xfd, 0x8a, 0x7e, 0xb7, 0x63, 0xce, 0x03, 0x67, 0x4a, 0xb4, 0x3e, 0x39, 0x18, 0xab, 0x22, 0x9a, 0x3b, 0xac, 0x2a, 0x9e, 0xa7, 0xe4, 0xd3, 0x81, 0x76, 0x00}
// --- END GENERATED BOOTLOADER SECTION ---


#define CONCAT_NAME_HELPER(prefix, name, suffix) prefix##name##suffix
#define CONCAT_NAME(name, var) CONCAT_NAME_HELPER(BOOTLOADER_, name, var)


#if BOOTLOADER_QA
// QA bootloaders
    #define BOOTLOADER_00 CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _QA_00)
    #define BOOTLOADER_FF CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _QA_FF)
#else
// normal bootloaders
#define BOOTLOADER_00 CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _00)
#define BOOTLOADER_FF CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _FF)
#endif
// clang-format on

#if PRODUCTION || BOOTLOADER_QA
static secbool latest_bootloader(const uint8_t *hash, int len) {
  if (len != 32) return secfalse;

  uint8_t hash_00[] = BOOTLOADER_00;
  uint8_t hash_FF[] = BOOTLOADER_FF;

  if (0 == memcmp(hash, hash_00, 32)) return sectrue;
  if (0 == memcmp(hash, hash_FF, 32)) return sectrue;
  return secfalse;
}
#endif

void check_and_replace_bootloader(void) {
#if PRODUCTION || BOOTLOADER_QA
  // compute current bootloader hash
  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  const uint32_t bl_len = 128 * 1024;
  const void *bl_data = flash_area_get_address(&BOOTLOADER_AREA, 0, bl_len);
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

  const image_header *new_bld_hdr = read_image_header(
      (uint8_t *)data, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_IMAGE_MAXSIZE);

  ensure(new_bld_hdr == (const image_header *)data ? sectrue : secfalse,
         "Invalid embedded bootloader");

  ensure(check_image_model(new_bld_hdr), "Incompatible embedded bootloader");

  const image_header *current_bld_hdr = read_image_header(
      bl_data, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_IMAGE_MAXSIZE);

  // cannot find valid header for current bootloader, something is wrong
  ensure(current_bld_hdr == (const image_header *)bl_data ? sectrue : secfalse,
         "Invalid bootloader header");

  ensure(check_image_model(current_bld_hdr), "Incompatible bootloader found");

  if (new_bld_hdr->monotonic < current_bld_hdr->monotonic) {
    // reject downgrade
    return;
  }

  uint32_t board_name = get_board_name();
  if (board_name == 0 || strncmp((const char *)&board_name, "T2T1", 4) == 0) {
    // no board capabilities, assume Model T
    if ((strncmp((const char *)&new_bld_hdr->hw_model, "T2T1", 4) != 0) &&
        (new_bld_hdr->hw_model != 0)) {
      // reject non-model T bootloader
      // 0 represents pre-model check bootloader
      ensure(secfalse, "Incompatible embedded bootloader");
    }
  }
  // at this point, due to the previous check_image_model call, we know that the
  // new_bld_hdr is
  //  meant for the same model as this firmware, so we can check the board name
  //  against the firmware hw_model.
  else if (board_name != HW_MODEL) {
    // reject incompatible bootloader
    ensure(secfalse, "Incompatible embedded bootloader");
  }

  ensure(flash_area_erase(&BOOTLOADER_AREA, NULL), NULL);
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < len / sizeof(uint32_t); i++) {
    ensure(
        flash_area_write_word(&BOOTLOADER_AREA, i * sizeof(uint32_t), data[i]),
        NULL);
  }
  for (int i = len / sizeof(uint32_t); i < 128 * 1024 / sizeof(uint32_t); i++) {
    ensure(flash_area_write_word(&BOOTLOADER_AREA, i * sizeof(uint32_t),
                                 0x00000000),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
#endif
}
