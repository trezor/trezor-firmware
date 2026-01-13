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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "ed25519-donna/ed25519.h"

#include <sec/image.h>
#include <sys/bootutils.h>
#include <sys/flash.h>

#ifdef STM32F4
_Static_assert(BOOTLOADER_VECTBL_OFFSET == IMAGE_HEADER_SIZE,
               "BOOTLOADER_VECTBL_OFFSET must match IMAGE_HEADER_SIZE");
#endif

_Static_assert(VENDOR_HEADER_MAX_SIZE + IMAGE_HEADER_SIZE <= IMAGE_CHUNK_SIZE,
               "The size of the firmware headers must be less than or equal to "
               "IMAGE_CHUNK_SIZE");

const uint8_t BOARDLOADER_KEY_M = 2;
const uint8_t BOARDLOADER_KEY_N = 3;
static const uint8_t * const BOARDLOADER_KEYS[] = {
#if !PRODUCTION
  (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
  (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
  (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
#else
    MODEL_BOARDLOADER_KEYS
#endif
};

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

#ifdef USE_SECMON_VERIFICATION
const uint8_t SECMON_KEY_M = 2;
const uint8_t SECMON_KEY_N = 3;
static const uint8_t * const SECMON_KEYS[] = {
#if !PRODUCTION
  /*** DEVEL/QA KEYS  ***/
  (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
  (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
  (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
#else
    MODEL_SECMON_KEYS
#endif
};
#endif

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
  if ((hdr->expiry & 0xFFFFFFFE) != 0) return NULL;

  if (hdr->codelen > (maxsize - hdr->hdrlen)) return NULL;
  if ((hdr->hdrlen + hdr->codelen) < 4 * 1024) return NULL;
  if ((hdr->hdrlen + hdr->codelen) % 512 != 0) return NULL;

  return hdr;
}

secbool check_image_model(const image_header *const hdr) {
  // abusing expiry field to break compatibility of non-TT images with existing
  // bootloaders/boardloaders
#ifdef TREZOR_MODEL_T2T1
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

#ifdef USE_SECMON_VERIFICATION
const secmon_header_t *read_secmon_header(const uint8_t *const data,
                                          const uint32_t maxsize) {
  const secmon_header_t *hdr = (const secmon_header_t *)data;

  if (hdr->magic != SECMON_IMAGE_MAGIC) {
    return NULL;
  }
  if (hdr->hdrlen != SECMON_HEADER_SIZE) {
    return NULL;
  }

  if (hdr->codelen > (maxsize - hdr->hdrlen)) return secfalse;
  if ((hdr->hdrlen + hdr->codelen) < 4 * 1024) return secfalse;
  if ((hdr->hdrlen + hdr->codelen) % 512 != 0) return secfalse;

  return hdr;
}

secbool check_secmon_model(const secmon_header_t *const hdr) {
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

void get_secmon_fingerprint(const secmon_header_t *const hdr,
                            uint8_t *const out) {
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (uint8_t *)hdr, SECMON_HEADER_SIZE - IMAGE_SIG_SIZE);
  for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
    IMAGE_HASH_UPDATE(&ctx, (const uint8_t *)"\x00", 1);
  }
  IMAGE_HASH_FINAL(&ctx, out);
}

secbool check_secmon_header_sig(const secmon_header_t *const hdr) {
  // check header signature

  uint8_t fingerprint[32];
  get_secmon_fingerprint(hdr, fingerprint);

  ed25519_public_key pub;
  if (sectrue != compute_pubkey(SECMON_KEY_M, SECMON_KEY_N, SECMON_KEYS,
                                hdr->sigmask, pub))
    return secfalse;

  return sectrue *
         (0 == ed25519_sign_open(fingerprint, IMAGE_HASH_DIGEST_LENGTH, pub,
                                 *(const ed25519_signature *)hdr->sig));
}

#ifdef SECURE_MODE
secbool check_secmon_contents(const secmon_header_t *const hdr,
                              size_t code_offset, const flash_area_t *area) {
  if (0 == area) {
    return secfalse;
  }

  // Check the secmon integrity, calculate and compare hash
  const void *data = flash_area_get_address(
      area, code_offset + SECMON_HEADER_SIZE, hdr->codelen);
  if (!data) {
    return secfalse;
  }

  if (sectrue != check_single_hash(hdr->hash, data, hdr->codelen)) {
    return secfalse;
  }

  return sectrue;
}
#endif  // SECURE_MODE

#endif  // USE_SECMON_VERIFICATION

secbool __wur read_vendor_header(const uint8_t *const data,
                                 vendor_header *const vhdr) {
  memcpy(&vhdr->magic, data, 4);
  if (vhdr->magic != 0x565A5254) return secfalse;  // TRZV

  memcpy(&vhdr->hdrlen, data + 4, 4);
  if (vhdr->hdrlen > VENDOR_HEADER_MAX_SIZE) return secfalse;

  memcpy(&vhdr->expiry, data + 8, 4);
  if (vhdr->expiry != 0) return secfalse;

  vhdr->origin = data;

  memcpy(&vhdr->version, data + 12, 2);

  memcpy(&vhdr->vsig_m, data + 14, 1);
  memcpy(&vhdr->vsig_n, data + 15, 1);
  memcpy(&vhdr->vtrust, data + 16, 2);
  memcpy(&vhdr->hw_model, data + 18, 4);
  memcpy(&vhdr->fw_type, data + 22, 1);

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

secbool check_vendor_header_model(const vendor_header *const vhdr) {
#ifdef TREZOR_MODEL_T2T1
  if (vhdr->hw_model == 0) {
    // vendor headers for model T have this field set to 0
    return sectrue;
  }
#endif
  if (vhdr->hw_model == HW_MODEL) {
    return sectrue;
  }

  return secfalse;
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

#ifdef KERNEL_MODE
secbool check_image_contents(const image_header *const hdr, uint32_t firstskip,
                             const flash_area_t *area) {
  if (0 == area) {
    return secfalse;
  }

  // Check the firmware integrity, calculate and compare hashes

  // check hashes of image chunks
  // we hash the image including the padding to the end of the area
  size_t offset = firstskip;
  size_t end_offset = offset + hdr->codelen;

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
#endif  // KERNEL_MODE

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
                                FIRMWARE_MAXSIZE)) == NULL) {
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

secbool check_bootloader_header_sig(const image_header *const hdr) {
  return check_image_header_sig(hdr, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N,
                                BOARDLOADER_KEYS);
}
