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

#include <string.h>

#include "ed25519-donna/ed25519.h"

#include "common.h"
#include "flash.h"
#include "image.h"
#include "model.h"

const uint8_t BOOTLOADER_KEY_M = 2;
const uint8_t BOOTLOADER_KEY_N = 3;
static const uint8_t * const BOOTLOADER_KEYS[] = {
#if !PRODUCTION
    /*** DEVEL/QA KEYS  ***/
    (const uint8_t *)"\xd7\x59\x79\x3b\xbc\x13\xa2\x81\x9a\x82\x7c\x76\xad\xb6\xfb\xa8\xa4\x9a\xee\x00\x7f\x49\xf2\xd0\x99\x2d\x99\xb8\x25\xad\x2c\x48",
    (const uint8_t *)"\x63\x55\x69\x1c\x17\x8a\x8f\xf9\x10\x07\xa7\x47\x8a\xfb\x95\x5e\xf7\x35\x2c\x63\xe7\xb2\x57\x03\x98\x4c\xf7\x8b\x26\xe2\x1a\x56",
    (const uint8_t *)"\xee\x93\xa4\xf6\x6f\x8d\x16\xb8\x19\xbb\x9b\xeb\x9f\xfc\xcd\xfc\xdc\x14\x12\xe8\x7f\xee\x6a\x32\x4c\x2a\x99\xa1\xe0\xe6\x71\x48",
#else
    MODEL_BOOTLOADER_KEYS
#endif
};

static secbool compute_pubkey(uint8_t sig_m, uint8_t sig_n,
                              const uint8_t *const *pub, uint8_t sigmask,
                              ed25519_public_key res) {
  if (0 == sig_m || 0 == sig_n) return secfalse;
  if (sig_m > sig_n) return secfalse;

  // discard bits higher than sig_n
  sigmask &= ((1 << sig_n) - 1);

  // remove if number of set bits in sigmask is not equal to sig_m
  if (__builtin_popcount(sigmask) != sig_m) return secfalse;

  ed25519_public_key keys[sig_m];
  int j = 0;
  for (int i = 0; i < sig_n; i++) {
    if ((1 << i) & sigmask) {
      memcpy(keys[j], pub[i], 32);
      j++;
    }
  }

  return sectrue * (0 == ed25519_cosi_combine_publickeys(res, keys, sig_m));
}

const image_header *read_image_header(const uint8_t *const data,
                                      const uint32_t magic,
                                      const uint32_t maxsize) {
  const image_header *hdr = (const image_header *)data;

  if (hdr->magic != magic) {
    return NULL;
  }
  if (hdr->hdrlen != IMAGE_HEADER_SIZE) {
    return NULL;
  }

  // TODO: expiry mechanism needs to be ironed out before production or those
  // devices won't accept expiring bootloaders (due to boardloader write
  // protection).
  // lowest bit is used for breaking compatibility between old TT bootloaders
  // and non TT images
  //  which is evaluated in check_image_model function
  if ((hdr->expiry & 0xFFFFFFFE) != 0) return secfalse;

  if (hdr->codelen > (maxsize - hdr->hdrlen)) return secfalse;
  if ((hdr->hdrlen + hdr->codelen) < 4 * 1024) return secfalse;
  if ((hdr->hdrlen + hdr->codelen) % 512 != 0) return secfalse;

  return hdr;
}

secbool check_image_model(const image_header *const hdr) {
  // abusing expiry field to break compatibility of non-TT images with existing
  // bootloaders/boardloaders
#ifdef TREZOR_MODEL_T
  if (hdr->expiry == 0 && hdr->hw_model == 0 && hdr->hw_revision == 0) {
    // images for model TT older than this check
    return sectrue;
  }
#else
  if ((hdr->expiry & 0x01) == 0) {
    // for models other than TT, expiry == 0 is unacceptable, as the image will
    // run on bootloaders older that this check
    return secfalse;
  }
#endif

#ifndef TREZOR_EMULATOR
  if (hdr->hw_model != HW_MODEL) {
    return secfalse;
  }
  if (hdr->hw_revision != HW_REVISION) {
    return secfalse;
  }
#endif

  return sectrue;
}

void get_image_fingerprint(const image_header *const hdr, uint8_t *const out) {
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (uint8_t *)hdr, IMAGE_HEADER_SIZE - IMAGE_SIG_SIZE);
  for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
    IMAGE_HASH_UPDATE(&ctx, (const uint8_t *)"\x00", 1);
  }
  IMAGE_HASH_FINAL(&ctx, out);
}

secbool check_image_header_sig(const image_header *const hdr, uint8_t key_m,
                               uint8_t key_n, const uint8_t *const *keys) {
  // check header signature

  uint8_t fingerprint[32];
  get_image_fingerprint(hdr, fingerprint);

  ed25519_public_key pub;
  if (sectrue != compute_pubkey(key_m, key_n, keys, hdr->sigmask, pub))
    return secfalse;

  return sectrue *
         (0 == ed25519_sign_open(fingerprint, IMAGE_HASH_DIGEST_LENGTH, pub,
                                 *(const ed25519_signature *)hdr->sig));
}

secbool __wur read_vendor_header(const uint8_t *const data,
                                 vendor_header *const vhdr) {
  memcpy(&vhdr->magic, data, 4);
  if (vhdr->magic != 0x565A5254) return secfalse;  // TRZV

  memcpy(&vhdr->hdrlen, data + 4, 4);
  if (vhdr->hdrlen > 64 * 1024) return secfalse;

  memcpy(&vhdr->expiry, data + 8, 4);
  if (vhdr->expiry != 0) return secfalse;

  vhdr->origin = data;

  memcpy(&vhdr->version, data + 12, 2);

  memcpy(&vhdr->vsig_m, data + 14, 1);
  memcpy(&vhdr->vsig_n, data + 15, 1);
  memcpy(&vhdr->vtrust, data + 16, 2);

  if (vhdr->vsig_n > MAX_VENDOR_PUBLIC_KEYS) {
    return secfalse;
  }

  for (int i = 0; i < vhdr->vsig_n; i++) {
    vhdr->vpub[i] = data + 32 + i * 32;
  }
  for (int i = vhdr->vsig_n; i < MAX_VENDOR_PUBLIC_KEYS; i++) {
    vhdr->vpub[i] = 0;
  }

  memcpy(&vhdr->vstr_len, data + 32 + vhdr->vsig_n * 32, 1);

  vhdr->vstr = (const char *)(data + 32 + vhdr->vsig_n * 32 + 1);

  vhdr->vimg = data + 32 + vhdr->vsig_n * 32 + 1 + vhdr->vstr_len;
  // align to 4 bytes
  vhdr->vimg += (-(uintptr_t)vhdr->vimg) & 3;

  memcpy(&vhdr->sigmask, data + vhdr->hdrlen - IMAGE_SIG_SIZE, 1);

  memcpy(vhdr->sig, data + vhdr->hdrlen - IMAGE_SIG_SIZE + 1,
         IMAGE_SIG_SIZE - 1);

  return sectrue;
}

secbool check_vendor_header_sig(const vendor_header *const vhdr, uint8_t key_m,
                                uint8_t key_n, const uint8_t *const *keys) {
  if (vhdr == NULL) {
    return secfalse;
  }

  // check header signature

  uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, vhdr->origin, vhdr->hdrlen - IMAGE_SIG_SIZE);
  for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
    IMAGE_HASH_UPDATE(&ctx, (const uint8_t *)"\x00", 1);
  }
  IMAGE_HASH_FINAL(&ctx, hash);

  ed25519_public_key pub;
  if (sectrue != compute_pubkey(key_m, key_n, keys, vhdr->sigmask, pub))
    return secfalse;

  return sectrue *
         (0 == ed25519_sign_open(hash, IMAGE_HASH_DIGEST_LENGTH, pub,
                                 *(const ed25519_signature *)vhdr->sig));
}

secbool check_vendor_header_keys(const vendor_header *const vhdr) {
  return check_vendor_header_sig(vhdr, BOOTLOADER_KEY_M, BOOTLOADER_KEY_N,
                                 BOOTLOADER_KEYS);
}

void vendor_header_hash(const vendor_header *const vhdr, uint8_t *hash) {
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t *)vhdr->vstr, vhdr->vstr_len);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t *)"Trezor Vendor Header", 20);
  IMAGE_HASH_FINAL(&ctx, hash);
}

secbool check_single_hash(const uint8_t *const hash, const uint8_t *const data,
                          int len) {
  uint8_t s_c[IMAGE_HASH_DIGEST_LENGTH] = {0};

  IMAGE_HASH_CALC(data, len, s_c);

  return sectrue * (0 == memcmp(s_c, hash, IMAGE_HASH_DIGEST_LENGTH));
}

secbool check_image_contents(const image_header *const hdr, uint32_t firstskip,
                             const flash_area_t *area) {
  if (0 == area) {
    return secfalse;
  }

  // Check the firmware integrity, calculate and compare hashes
  size_t offset = IMAGE_CODE_ALIGN(firstskip);
  size_t end_offset = offset + hdr->codelen;

  // Check area between headers and code
  uint32_t padding_size = offset - firstskip;
  const uint8_t *addr =
      (uint8_t *)flash_area_get_address(area, firstskip, padding_size);
  for (size_t i = 0; i < padding_size; i++) {
    if (*addr != 0) {
      return secfalse;
    }
  }

  while (offset < end_offset) {
    size_t bytes_to_check = MIN(IMAGE_CHUNK_SIZE - (offset % IMAGE_CHUNK_SIZE),
                                end_offset - offset);

    const void *data = flash_area_get_address(area, offset, bytes_to_check);
    if (!data) {
      return secfalse;
    }

    size_t hash_offset = (offset / IMAGE_CHUNK_SIZE) * 32;
    if (sectrue !=
        check_single_hash(hdr->hashes + hash_offset, data, bytes_to_check)) {
      return secfalse;
    }

    offset += bytes_to_check;
  }

  // Check the padding to the end of the area
  end_offset = flash_area_get_size(area);

  if (offset < end_offset) {
    // Use the first byte in the checked area as the expected padding byte
    // Firmware is always padded with 0xFF, while the bootloader might be
    // padded with 0x00 as well
    uint8_t expected_byte = *(
        (const uint8_t *)flash_area_get_address(area, offset, sizeof(uint8_t)));

    if (expected_byte != 0x00 && expected_byte != 0xFF) {
      return secfalse;
    }

    uint32_t expected_word = expected_byte << 24 | expected_byte << 16 |
                             expected_byte << 8 | expected_byte;

    while (offset < end_offset) {
      size_t bytes_to_check = MIN(
          IMAGE_CHUNK_SIZE - (offset % IMAGE_CHUNK_SIZE), end_offset - offset);
      size_t words_to_check = bytes_to_check / sizeof(uint32_t);
      size_t single_bytes_to_check = bytes_to_check % sizeof(uint32_t);

      const uint8_t *bytes = (const uint8_t *)flash_area_get_address(
          area, offset, single_bytes_to_check);
      if (!bytes) {
        return secfalse;
      }

      for (size_t i = 0; i < single_bytes_to_check; i++) {
        if (bytes[i] != expected_byte) {
          return secfalse;
        }
      }

      offset += single_bytes_to_check;

      const uint32_t *data = (const uint32_t *)flash_area_get_address(
          area, offset, bytes_to_check - single_bytes_to_check);
      if (!data) {
        return secfalse;
      }

      for (size_t i = 0; i < words_to_check; i++) {
        if (data[i] != expected_word) {
          return secfalse;
        }
      }

      offset += words_to_check * sizeof(uint32_t);
    }
  }

  return sectrue;
}

secbool check_firmware_header(const uint8_t *header, size_t header_size,
                              firmware_header_info_t *info) {
  // parse and check vendor header
  vendor_header vhdr;
  if (sectrue != read_vendor_header(header, &vhdr)) {
    return secfalse;
  }
  if (sectrue != check_vendor_header_keys(&vhdr)) {
    return secfalse;
  }

  // parse and check image header
  const image_header *ihdr;
  if ((ihdr = read_image_header(header + vhdr.hdrlen, FIRMWARE_IMAGE_MAGIC,
                                FIRMWARE_IMAGE_MAXSIZE)) == NULL) {
    return secfalse;
  }
  if (sectrue !=
      check_image_header_sig(ihdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub)) {
    return secfalse;
  }

  // copy vendor string
  info->vstr_len = MIN(sizeof(info->vstr), vhdr.vstr_len);
  if (info->vstr_len > 0) {
    memcpy(info->vstr, vhdr.vstr, info->vstr_len);
  }

  // copy firmware version
  info->ver_major = ihdr->version & 0xFF;
  info->ver_minor = (ihdr->version >> 8) & 0xFF;
  info->ver_patch = (ihdr->version >> 16) & 0xFF;
  info->ver_build = (ihdr->version >> 24) & 0xFF;

  // calculate and copy the image fingerprint
  get_image_fingerprint(ihdr, info->fingerprint);

  // calculate hash of both vendor and image headers
  IMAGE_HASH_CALC(header, vhdr.hdrlen + ihdr->hdrlen, info->hash);

  return sectrue;
}
