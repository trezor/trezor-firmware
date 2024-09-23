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
#include "memzero.h"
#include "model.h"
#include "mpu.h"
#include "uzlib.h"

// symbols from bootloader.bin => bootloader.o
extern const void _binary_embed_bootloaders_bootloader_bin_deflated_start;
extern const void _binary_embed_bootloaders_bootloader_bin_deflated_size;

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

#define UZLIB_WINDOW_SIZE (1 << 10)

#if PRODUCTION || BOOTLOADER_QA
static void uzlib_prepare(struct uzlib_uncomp *decomp, uint8_t *window,
                          const void *src, uint32_t srcsize, void *dest,
                          uint32_t destsize) {
  memzero(decomp, sizeof(struct uzlib_uncomp));
  if (window) {
    memzero(window, UZLIB_WINDOW_SIZE);
  }
  memzero(dest, destsize);
  decomp->source = (const uint8_t *)src;
  decomp->source_limit = decomp->source + srcsize;
  decomp->dest = (uint8_t *)dest;
  decomp->dest_limit = decomp->dest + destsize;
  uzlib_uncompress_init(decomp, window, window ? UZLIB_WINDOW_SIZE : 0);
}
#endif

void check_and_replace_bootloader(void) {
#if PRODUCTION || BOOTLOADER_QA
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  // compute current bootloader hash
  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  const uint32_t bl_len = flash_area_get_size(&BOOTLOADER_AREA);
  const void *bl_data = flash_area_get_address(&BOOTLOADER_AREA, 0, bl_len);
  blake2s(bl_data, bl_len, hash, BLAKE2S_DIGEST_LENGTH);

  // don't whitelist the valid bootloaders for now
  // ensure(known_bootloader(hash, BLAKE2S_DIGEST_LENGTH), "Unknown bootloader
  // detected");

  // do we have the latest bootloader?
  if (sectrue == latest_bootloader(hash, BLAKE2S_DIGEST_LENGTH)) {
    mpu_reconfig(mode);
    return;
  }

  // replace bootloader with the latest one
  const uint32_t *data =
      (const uint32_t
           *)&_binary_embed_bootloaders_bootloader_bin_deflated_start;
  const uint32_t len =
      (const uint32_t)&_binary_embed_bootloaders_bootloader_bin_deflated_size;

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};
  uint32_t decomp_out[IMAGE_HEADER_SIZE / sizeof(uint32_t)] = {0};

  uzlib_prepare(&decomp, decomp_window, data, len, decomp_out,
                sizeof(decomp_out));

  ensure((uzlib_uncompress(&decomp) == TINF_OK) ? sectrue : secfalse,
         "Bootloader header decompression failed");

  const image_header *new_bld_hdr = read_image_header(
      (uint8_t *)decomp_out, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  ensure(new_bld_hdr == (const image_header *)decomp_out ? sectrue : secfalse,
         "Invalid embedded bootloader");

  ensure(check_image_model(new_bld_hdr), "Incompatible embedded bootloader");

  const image_header *current_bld_hdr =
      read_image_header(bl_data, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  // cannot find valid header for current bootloader, something is wrong
  ensure(current_bld_hdr == (const image_header *)bl_data ? sectrue : secfalse,
         "Invalid bootloader header");

  ensure(check_image_model(current_bld_hdr), "Incompatible bootloader found");

  if (new_bld_hdr->monotonic < current_bld_hdr->monotonic) {
    // reject downgrade
    mpu_reconfig(mode);
    return;
  }

  uint32_t board_name = get_board_name();
  if (board_name == 0 || strncmp((const char *)&board_name, "T2T1", 4) == 0) {
    // no board capabilities, assume Model T
    if ((strncmp((const char *)&new_bld_hdr->hw_model, "T2T1", 4) != 0) &&
        (new_bld_hdr->hw_model != 0)) {
      // reject non-model T bootloader
      // 0 represents pre-model check bootloader
      error_shutdown("Incompatible embedded bootloader");
    }
  }
  // at this point, due to the previous check_image_model call, we know that the
  // new_bld_hdr is
  //  meant for the same model as this firmware, so we can check the board name
  //  against the firmware hw_model.
  else if (board_name != HW_MODEL) {
    // reject incompatible bootloader
    error_shutdown("Incompatible embedded bootloader");
  }

  ensure(flash_area_erase(&BOOTLOADER_AREA, NULL), NULL);
  ensure(flash_unlock_write(), NULL);

  uint32_t offset = 0;

  do {
    uint32_t *p = decomp_out;
    uint32_t size = decomp.dest - (uint8_t *)decomp_out;
    uint32_t size_padded = FLASH_ALIGN(size);
    ensure(flash_area_write_data_padded(&BOOTLOADER_AREA, offset, p, size, 0,
                                        size_padded),
           NULL);
    offset += size_padded;
    decomp.dest = (uint8_t *)decomp_out;
  } while (uzlib_uncompress(&decomp) >= 0);

  if (offset < bl_len) {
    // fill the rest of the bootloader area with 0x00
    ensure(flash_area_write_data_padded(&BOOTLOADER_AREA, offset, NULL, 0, 0,
                                        bl_len - offset),
           NULL);
  }

  ensure(flash_lock_write(), NULL);

  mpu_reconfig(mode);
#endif
}
