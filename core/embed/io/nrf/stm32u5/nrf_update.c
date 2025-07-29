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

#ifdef KERNEL_MODE
#ifdef USE_SMP

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/nrf.h>

#include "../nrf_internal.h"
#include "rust_smp.h"
#include "sha2.h"
#include "sys/systick.h"

#define IMAGE_HASH_LEN 32
#define IMAGE_TLV_SHA256 0x10

struct image_version {
  uint8_t iv_major;
  uint8_t iv_minor;
  uint16_t iv_revision;
  uint32_t iv_build_num;
} __packed;

struct image_header {
  uint32_t ih_magic;
  uint32_t ih_load_addr;
  uint16_t ih_hdr_size;         /* Size of image header (bytes). */
  uint16_t ih_protect_tlv_size; /* Size of protected TLV area (bytes). */
  uint32_t ih_img_size;         /* Does not include header. */
  uint32_t ih_flags;            /* IMAGE_F_[...]. */
  struct image_version ih_ver;
  uint32_t _pad1;
} __packed;

/**
 * Read the SHA-256 image hash from the TLV trailer of the given flash slot.
 *
 * @param binary_ptr  pointer to the binary image
 * @param out_hash   Buffer of at least IMAGE_HASH_LEN bytes to receive the hash
 * @return 0 on success, or a negative errno on failure
 */
static int read_image_sha256(const uint8_t *binary_ptr, size_t binary_size,
                             uint8_t out_hash[IMAGE_HASH_LEN]) {
  int rc;

  /* Read header to get image_size and hdr_size */
  struct image_header *hdr = (struct image_header *)binary_ptr;

  uint32_t img_size = hdr->ih_img_size;
  uint32_t hdr_size = hdr->ih_hdr_size;
  uint32_t tvl1_size = hdr->ih_protect_tlv_size;

  /* Compute start of TLV trailer */
  off_t off = 0 + hdr_size + img_size + tvl1_size + 4;

  /* Scan TLVs until we find the SHA-256 entry */
  while (true) {
    uint16_t tlv_hdr[2];

    if (off + sizeof(tlv_hdr) > binary_size) {
      rc = -1;  // Not enough data for TLV header
      break;
    }

    memcpy(tlv_hdr, binary_ptr + off, sizeof(tlv_hdr));

    uint16_t type = tlv_hdr[0];
    uint16_t len = tlv_hdr[1];

    if (off + sizeof(tlv_hdr) + len > binary_size) {
      rc = -1;  // Not enough data for TLV value
      break;
    }

    if (type == IMAGE_TLV_SHA256) {
      if (len != IMAGE_HASH_LEN) {
        rc = -1;
      } else {
        memcpy(out_hash, binary_ptr + off + sizeof(tlv_hdr), IMAGE_HASH_LEN);
        rc = 0;
      }
      break;
    }

    off += sizeof(tlv_hdr) + len;
  }

  return rc;
}

bool nrf_update_required(const uint8_t *image_ptr, size_t image_len) {
  nrf_info_t info = {0};

  uint16_t try_cntr = 0;
  while (!nrf_get_info(&info)) {
    nrf_reboot();
    systick_delay_ms(500);
    try_cntr++;
    if (try_cntr > 3) {
      // Assuming corrupted image, but we could also check comm with MCUboot
      return true;
    }
  }

  uint8_t expected_hash[SHA256_DIGEST_LENGTH] = {0};

  read_image_sha256(image_ptr, image_len, expected_hash);

  return memcmp(info.hash, expected_hash, SHA256_DIGEST_LENGTH) != 0;
}

bool nrf_update(const uint8_t *image_ptr, size_t image_len) {
  nrf_reboot_to_bootloader();
  nrf_set_dfu_mode(true);

  uint8_t sha256[SHA256_DIGEST_LENGTH] = {0};

  SHA256_CTX ctx;
  sha256_Init(&ctx);
  sha256_Update(&ctx, image_ptr, image_len);
  sha256_Final(&ctx, sha256);

  uint8_t try_cntr = 0;

  bool result = false;
  do {
    result = smp_upload_app_image(image_ptr, image_len, sha256,
                                  SHA256_DIGEST_LENGTH);
    try_cntr++;
  } while (!result && try_cntr < 3);

  nrf_reboot();

  nrf_set_dfu_mode(false);

  return result;
}

#endif
#endif
