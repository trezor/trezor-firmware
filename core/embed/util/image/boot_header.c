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

#include <rtl/sizedefs.h>
#include <util/boot_header.h>
#include <util/image_hash_conf.h>

#include <../vendor/sphincsplus/ref/api.h>

#include <version.h>

#ifdef BOOTLOADER
extern const uint8_t _bootloader_code_size;

__attribute__((section(".header"))) const boot_header_t g_bootloader_header = {
    .sig =
        {
            .magic = BOOTHEADER_MAGIC_TRZQ,
            .hw_model = HW_MODEL,
            .hw_revision = HW_REVISION,
            .version =
                {
                    .major = VERSION_MAJOR,
                    .minor = VERSION_MINOR,
                    .patch = VERSION_PATCH,
                    .build = VERSION_BUILD,
                },
            .fix_version =
                {
                    .major = FIX_VERSION_MAJOR,
                    .minor = FIX_VERSION_MINOR,
                    .patch = FIX_VERSION_PATCH,
                    .build = FIX_VERSION_BUILD,
                },
            .monotonic_version = BOOTLOADER_MONOTONIC_VERSION,
            .header_size = sizeof(boot_header_t),
            .code_size = (uint32_t)&_bootloader_code_size,
        },
};
#endif

#if PRODUCTION

#error Production keys are not defined.

#else
// Development public keys
static const uint8_t BOOTLOADER_PQ_KEY[2][32] = {
    {0xec, 0x01, 0xe6, 0x02, 0x63, 0x02, 0x4f, 0x7e, 0x71, 0x72, 0x80,
     0x13, 0xb7, 0x31, 0xf7, 0xba, 0x12, 0x99, 0xf5, 0x18, 0xc2, 0x7b,
     0xa3, 0xed, 0x8f, 0x4a, 0x21, 0x99, 0x74, 0x12, 0x7c, 0x62},
    {0x8a, 0xf8, 0x87, 0x80, 0x85, 0x94, 0x6e, 0xd8, 0xb1, 0x16, 0xbd,
     0x24, 0xc0, 0xf2, 0xaa, 0xc4, 0x8b, 0x7e, 0x8f, 0x11, 0xbf, 0x06,
     0x87, 0x25, 0xcc, 0xfb, 0xb1, 0x52, 0xab, 0xf7, 0xa4, 0xcd}};
#endif  // PRODUCTION

secbool boot_header_check_signature(const boot_header_t* header,
                                    const boot_header_fingerprint_t* fp) {
  // Get the signature indices based on the signature mask
  _Static_assert(ARRAY_LENGTH(BOOTLOADER_PQ_KEY) <= 3);
  int sig1_idx = header->uns.sigmask & (1 << 0) ? 0 : 1;
  int sig2_idx = header->uns.sigmask & (1 << 2) ? 2 : 1;

  // There must be two different signatures to verify
  if (sig1_idx == sig2_idx) {
    return secfalse;
  }

  if (sig1_idx >= ARRAY_LENGTH(BOOTLOADER_PQ_KEY) ||
      sig2_idx >= ARRAY_LENGTH(BOOTLOADER_PQ_KEY)) {
    return secfalse;
  }

  int result;

  // Verify 1st signature
  result = crypto_sign_verify(header->uns.signature1,
                              sizeof(header->uns.signature1), fp->bytes,
                              sizeof(fp->bytes), BOOTLOADER_PQ_KEY[sig1_idx]);
  if (result != 0) {
    return secfalse;
  }

  // Verify 2nd signature
  result = crypto_sign_verify(header->uns.signature2,
                              sizeof(header->uns.signature2), fp->bytes,
                              sizeof(fp->bytes), BOOTLOADER_PQ_KEY[sig2_idx]);
  if (result != 0) {
    return secfalse;
  }

  return sectrue;
}

const boot_header_t* boot_header_check_integrity(uint32_t address) {
  boot_header_t* hdr = (boot_header_t*)address;

  // Check if the header starts with the magic
  if (hdr->sig.magic != BOOT_HEADER_MAGIC_TRZQ) {
    return NULL;
  }

  // Check if the header is aligned to 8K boundary (flash page size)
  if (!IS_ALIGNED(hdr->sig.header_size, SIZE_8K)) {
    return NULL;
  }

  // Check if the header size is in reasonable limits
  if (hdr->sig.header_size >= SIZE_64K) {
    return NULL;
  }

  // Check if bootloader code size is withing reasonable limits
  if (hdr->sig.code_size < SIZE_8K ||
      hdr->sig.code_size > BOOT_HEADER_CODE_MAXSIZE) {
    return NULL;
  }

  // Check if merkle path fits into the array in the header
  if (hdr->uns.merkle_path_len > BOOT_HEADER_MERKLE_PATH_MAX_LEN) {
    return NULL;
  }

  return hdr;
}

void boot_header_calc_fingerprint(const boot_header_t* hdr,
                                  uint32_t code_address,
                                  boot_header_fingerprint_t* fp) {
  IMAGE_HASH_CTX ctx;

  // Hash the signed part of the header
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)&hdr->sig, sizeof(hdr->sig));
  size_t code_size = hdr->sig.code_size;
  IMAGE_HASH_FINAL(&ctx, fp->bytes);

  size_t max_chunk_size = 256 * 1024;  // TODO: where does this value come from?

  // Hash the bootloader code
  for (size_t ofs = 0; ofs < hdr->sig.code_size; ofs += max_chunk_size) {
    const uint8_t* chunk_ptr = (const uint8_t*)(code_address + ofs);
    size_t chunk_size = MIN(max_chunk_size, code_size - ofs);
    IMAGE_HASH_INIT(&ctx);
    IMAGE_HASH_UPDATE(&ctx, fp->bytes, sizeof(fp->bytes));
    IMAGE_HASH_UPDATE(&ctx, chunk_ptr, chunk_size);
    IMAGE_HASH_FINAL(&ctx, fp->bytes);
  }

  // Add the Merkle path nodes to the hash
  for (size_t i = 0; i < hdr->uns.merkle_path_len; i++) {
    const uint8_t* node = hdr->uns.merkle_path[i];
    IMAGE_HASH_INIT(&ctx);
    if (memcmp(fp, node, sizeof(fp->bytes)) < 0) {
      IMAGE_HASH_UPDATE(&ctx, node, sizeof(fp->bytes));
      IMAGE_HASH_UPDATE(&ctx, fp->bytes, sizeof(fp->bytes));
    } else {
      IMAGE_HASH_UPDATE(&ctx, fp->bytes, sizeof(fp->bytes));
      IMAGE_HASH_UPDATE(&ctx, node, sizeof(fp->bytes));
    }
    IMAGE_HASH_FINAL(&ctx, fp->bytes);
  }
}

secbool boot_header_check_model(const boot_header_t* hdr) {
  if (hdr->sig.hw_model != HW_MODEL) {
    return secfalse;
  }

  if (hdr->sig.hw_revision != HW_REVISION) {
    return secfalse;
  }

  return sectrue;
}

#endif  // SECURE_MODE
