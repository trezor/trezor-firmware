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

#ifdef SECURE_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/mpu.h>
#include <util/board_capabilities.h>
#include <util/flash.h>
#include <util/image.h>
#include "blake2s.h"
#include "memzero.h"
#include "uzlib.h"

#include <util/boot_image.h>

static secbool hash_match(const uint8_t *hash, const uint8_t *hash_00,
                          const uint8_t *hash_FF) {
  if (0 == memcmp(hash, hash_00, BLAKE2S_DIGEST_LENGTH)) return sectrue;
  if (0 == memcmp(hash, hash_FF, BLAKE2S_DIGEST_LENGTH)) return sectrue;
  return secfalse;
}

#define UZLIB_WINDOW_SIZE (1 << 10)
_Static_assert(
    UZLIB_WINDOW_SIZE >= IMAGE_HEADER_SIZE,
    "UZLIB_WINDOW_SIZE must be at least as large as IMAGE_HEADER_SIZE");
_Static_assert(
    BOOTLOADER_MAXSIZE <= IMAGE_CHUNK_SIZE,
    "BOOTLOADER_MAXSIZE must be less than or equal to IMAGE_CHUNK_SIZE");

#ifndef USE_BOOTHEADER
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

bool boot_image_check(const boot_image_t *image) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  // compute current bootloader hash
  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  const uint32_t bl_len = flash_area_get_size(&BOOTLOADER_AREA);
  const void *bl_data = flash_area_get_address(&BOOTLOADER_AREA, 0, bl_len);
  blake2s(bl_data, bl_len, hash, BLAKE2S_DIGEST_LENGTH);

  // don't whitelist the valid bootloaders for now
  // ensure(known_bootloader(hash, BLAKE2S_DIGEST_LENGTH), "Unknown bootloader
  // detected");

  // does the bootloader match?
  if (sectrue == hash_match(hash, image->hash_00, image->hash_FF)) {
    mpu_reconfig(mode);
    return false;
  }

  mpu_reconfig(mode);
  return true;
}

#ifndef USE_BOOTHEADER

void boot_image_replace(const boot_image_t *image) {
  const uint32_t bl_len = flash_area_get_size(&BOOTLOADER_AREA);
  const void *bl_data = flash_area_get_address(&BOOTLOADER_AREA, 0, bl_len);

  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};
  uint32_t decomp_out[IMAGE_HEADER_SIZE / sizeof(uint32_t)] = {0};

  uzlib_prepare(&decomp, decomp_window, image->image_ptr, image->image_size,
                decomp_out, sizeof(decomp_out));

  ensure((uzlib_uncompress(&decomp) == TINF_OK) ? sectrue : secfalse,
         "Bootloader header decompression failed");

  const image_header *new_bld_hdr = read_image_header(
      (uint8_t *)&decomp_out, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  ensure(new_bld_hdr == (const image_header *)&decomp_out ? sectrue : secfalse,
         "Invalid embedded bootloader");

  ensure(check_image_model(new_bld_hdr), "Incompatible embedded bootloader");

  ensure(check_bootloader_header_sig(new_bld_hdr),
         "Invalid embedded bootloader signature");

  const image_header *current_bld_hdr =
      read_image_header(bl_data, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  uint8_t new_bld_hash[IMAGE_HASH_DIGEST_LENGTH] = {0};
  uint8_t new_bld_hash_expected[IMAGE_HASH_DIGEST_LENGTH] = {0};

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);

  // backup new bld header values, as it will be overwritten by uzlib
  size_t header_offset = new_bld_hdr->hdrlen;
  memcpy(new_bld_hash_expected, &new_bld_hdr->hashes[0],
         IMAGE_HASH_DIGEST_LENGTH);
  uint32_t new_bld_hw_model = new_bld_hdr->hw_model;
  uint8_t new_bld_monotonic = new_bld_hdr->monotonic;

  do {
    uint8_t *p = (uint8_t *)decomp_out + header_offset;
    uint32_t size = decomp.dest - (uint8_t *)decomp_out - header_offset;
    IMAGE_HASH_UPDATE(&ctx, p, size);
    decomp.dest = (uint8_t *)decomp_out;
    header_offset =
        0;  // after the first chunk, we don't need to skip the header anymore
  } while (uzlib_uncompress(&decomp) >= 0);

  IMAGE_HASH_FINAL(&ctx, new_bld_hash);

  if (0 !=
      memcmp(new_bld_hash, new_bld_hash_expected, IMAGE_HASH_DIGEST_LENGTH)) {
    // the hash in the header does not match the computed hash
    error_shutdown("Invalid bootloader contents");
  }

  memset(&decomp, 0, sizeof(struct uzlib_uncomp));

  // cannot find valid header for current bootloader, something is wrong
  ensure(current_bld_hdr == (const image_header *)bl_data ? sectrue : secfalse,
         "Invalid bootloader header");

  ensure(check_image_model(current_bld_hdr), "Incompatible bootloader found");

  if (new_bld_monotonic < current_bld_hdr->monotonic) {
    error_shutdown("Bootloader downgrade rejected");
  }

  uint32_t board_name = get_board_name();
  if (board_name == 0 || strncmp((const char *)&board_name, "T2T1", 4) == 0) {
    // no board capabilities, assume Model T
    if ((strncmp((const char *)&new_bld_hw_model, "T2T1", 4) != 0) &&
        (new_bld_hw_model != 0)) {
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

  uzlib_prepare(&decomp, decomp_window, image->image_ptr, image->image_size,
                decomp_out, sizeof(decomp_out));

  ensure((uzlib_uncompress(&decomp) == TINF_OK) ? sectrue : secfalse,
         "Bootloader decompression failed");

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
}

#else

void boot_image_replace(const boot_image_t *image) {
  // copy new signature block to upgrade block
  // modify the footer to point the bootloader image
}

#endif

#endif
