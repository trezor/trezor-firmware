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

#include <sec/board_capabilities.h>
#include <sec/monoctr.h>
#include <sys/mpu.h>
#include <util/boot_image.h>
#include <util/flash.h>
#include <util/image.h>

#include "blake2s.h"
#include "memzero.h"

#ifdef USE_BOOT_UCB
#include <util/boot_header.h>
#include <util/boot_ucb.h>
#else
#include "uzlib.h"
#endif

#ifndef USE_BOOT_UCB

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

bool boot_image_check(const boot_image_t *image) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

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

void boot_image_replace(const boot_image_t *image) {
  const uint32_t bl_len = flash_area_get_size(&BOOTLOADER_AREA);
  const void *bl_data = flash_area_get_address(&BOOTLOADER_AREA, 0, bl_len);

  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

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

bool boot_image_check(const boot_image_t *image) {
  if (image->image_size < sizeof(boot_header_auth_t)) {
    // Invalid image size, must be at least the size of the header
    return false;
  }

  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

  boot_header_auth_t *cur_hdr = (boot_header_auth_t *)BOOTLOADER_START;
  boot_header_auth_t *new_hdr = (boot_header_auth_t *)image->image_ptr;

  bool diff = (cur_hdr->header_size != new_hdr->header_size) ||
              (memcmp(cur_hdr, new_hdr, cur_hdr->header_size) != 0);

  mpu_restore(mode);

  return diff;
}

void boot_image_replace(const boot_image_t *image) {
  uint32_t header_address = (uint32_t)image->image_ptr;

  // Check that image is big enough to hold the header at least
  ensure(sectrue * (image->image_size >= sizeof(boot_header_auth_t)),
         "Bootloader image too small");

  // Read bootloader header
  const boot_header_auth_t *hdr = boot_header_auth_get(header_address);
  ensure((hdr != NULL) * sectrue, "Invalid bootloader header");

  // Check the image is big enough to hold both header and code
  ensure(sectrue * (hdr->header_size + hdr->code_size <= image->image_size),
         "Bootloader image too small");

  // Check monotonic version

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

  const boot_header_auth_t *old_hdr = boot_header_auth_get(BOOTLOADER_START);

  ensure((old_hdr != NULL) * sectrue, "Invalid current bootloader header");

  uint8_t min_monotonic_version = old_hdr->monotonic_version;

  mpu_restore(mpu_mode);

  ensure(sectrue * (hdr->monotonic_version >= min_monotonic_version),
         "Bootloader downgrade rejected");

  uint32_t code_address = (uint32_t)image->image_ptr + hdr->header_size;

  // Calculate the Merkle root from the header and the code
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, code_address, &merkle_root);

  // Check whether the new bootloader is properly signed
  ensure(boot_header_check_signature(hdr, &merkle_root),
         "Invalid bootloader signature");

  // Write to update control block
  ensure(boot_ucb_write(header_address, code_address),
         "Failed to write boot UCB");
}

#endif

#endif
