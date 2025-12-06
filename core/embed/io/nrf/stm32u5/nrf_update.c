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
#include <sys/systick.h>

#include "../nrf_internal.h"
#include "rust_smp.h"
#include "sha2.h"

#define IMAGE_HASH_LEN 32
#define IMAGE_TLV_SHA256 0x10

struct image_header {
  uint32_t ih_magic;
  uint32_t ih_load_addr;
  uint16_t ih_hdr_size;         /* Size of image header (bytes). */
  uint16_t ih_protect_tlv_size; /* Size of protected TLV area (bytes). */
  uint32_t ih_img_size;         /* Does not include header. */
  uint32_t ih_flags;            /* IMAGE_F_[...]. */
  nrf_app_version_t ih_ver;
  uint32_t _pad1;
} __packed;

/**
 * Read the SHA-256 image hash from the TLV trailer of the given flash slot.
 *
 * @param binary_ptr  pointer to the binary image
 * @param out_hash   Buffer of at least IMAGE_HASH_LEN bytes to receive the hash
 * @return "true" on success, "false" on failure
 */
static bool read_image_sha256(const uint8_t *binary_ptr, size_t binary_size,
                              uint8_t out_hash[IMAGE_HASH_LEN]) {
  bool ret;

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
      ret = false;  // Not enough data for TLV header
      break;
    }

    memcpy(tlv_hdr, binary_ptr + off, sizeof(tlv_hdr));

    uint16_t type = tlv_hdr[0];
    uint16_t len = tlv_hdr[1];

    if (off + sizeof(tlv_hdr) + len > binary_size) {
      ret = false;  // Not enough data for TLV value
      break;
    }

    if (type == IMAGE_TLV_SHA256) {
      if (len != IMAGE_HASH_LEN) {
        ret = false;
      } else {
        memcpy(out_hash, binary_ptr + off + sizeof(tlv_hdr), IMAGE_HASH_LEN);
        ret = true;
      }
      break;
    }

    off += sizeof(tlv_hdr) + len;
  }

  return ret;
}

/**
 * Read the image version from the image header.
 *
 * @param image_ptr  pointer to the binary image
 * @param out_version   Pointer to nrf_app_version_t to receive the version
 * @return "true" on success, "false" on failure
 */
static bool image_version_read(const uint8_t *image_ptr,
                               nrf_app_version_t *out_version) {
  struct image_header *hdr = (struct image_header *)image_ptr;

  if (image_ptr == NULL || out_version == NULL) {
    return false;
  }

  memcpy(out_version, &hdr->ih_ver, sizeof(nrf_app_version_t));

  return true;
}

/**
 * Read the image version from the nRF MCUboot via SMP serial recovery.
 *
 * @param out_version   Pointer to nrf_app_version_t to receive the version
 * @return "true" on success, "false" on failure
 */
static bool nrf_smp_version_get(nrf_app_version_t *out_version) {
  bool ret = false;

  nrf_reboot_to_bootloader();
  nrf_set_dfu_mode(true);

  if (smp_image_version_get(out_version)) {
    // Success - version string provided via SMP has been decoded and stored
    // within "out_version" variable
    ret = true;
  }

  nrf_reboot();
  nrf_set_dfu_mode(false);

  return ret;
}

/**
 * Comparison of two image versions.
 *
 * @param v1 Pointer to first nrf_app_version_t
 * @param v2 Pointer to second nrf_app_version_t
 * @return 0 when equal, 1 when v1 is greater, -1 when v2 is greater
 */
static int version_cmp(const nrf_app_version_t *v1,
                       const nrf_app_version_t *v2) {
  if (v1->major != v2->major) {
    return (v1->major < v2->major) ? -1 : 1;
  }
  if (v1->minor != v2->minor) {
    return (v1->minor < v2->minor) ? -1 : 1;
  }
  if (v1->revision != v2->revision) {
    return (v1->revision < v2->revision) ? -1 : 1;
  }
  if (v1->build_num != v2->build_num) {
    return (v1->build_num < v2->build_num) ? -1 : 1;
  }
  return 0;
}

bool nrf_update_required(const uint8_t *image_ptr, size_t image_len) {
  for (int i = 0; i < 3; i++) {
    nrf_info_t info;
    uint8_t expected_hash[SHA256_DIGEST_LENGTH];

    if (nrf_get_info(&info) == true &&
        read_image_sha256(image_ptr, image_len, expected_hash) == true) {
      return memcmp(info.hash, expected_hash, SHA256_DIGEST_LENGTH) != 0;
    }

    // Can't communicate with the App via SPI, trying SMP serial recovery over
    // UART to nRF MCUboot
    nrf_app_version_t smp_version, image_version;

    if (nrf_smp_version_get(&smp_version) == true &&
        image_version_read(image_ptr, &image_version) == true) {
      return version_cmp(&image_version, &smp_version) != 0;
    }

    systick_delay_ms(100);  // TODO: is it necessary?
  }

  // Assuming corrupted image, force update
  return true;
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

  // wait for flash to be written
  systick_delay_ms(1000);

  nrf_reboot();

  nrf_set_dfu_mode(false);

  return result;
}

#endif
#endif
