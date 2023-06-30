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

#include "blake2s.h"
#include "ed25519-donna/ed25519.h"

#include "common.h"
#include "flash.h"
#include "image.h"

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
  BLAKE2S_CTX ctx;
  blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  blake2s_Update(&ctx, hdr, IMAGE_HEADER_SIZE - IMAGE_SIG_SIZE);
  for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
    blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
  }
  blake2s_Final(&ctx, out, BLAKE2S_DIGEST_LENGTH);
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
         (0 == ed25519_sign_open(fingerprint, BLAKE2S_DIGEST_LENGTH, pub,
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

  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  BLAKE2S_CTX ctx;
  blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  blake2s_Update(&ctx, vhdr->origin, vhdr->hdrlen - IMAGE_SIG_SIZE);
  for (int i = 0; i < IMAGE_SIG_SIZE; i++) {
    blake2s_Update(&ctx, (const uint8_t *)"\x00", 1);
  }
  blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

  ed25519_public_key pub;
  if (sectrue != compute_pubkey(key_m, key_n, keys, vhdr->sigmask, pub))
    return secfalse;

  return sectrue *
         (0 == ed25519_sign_open(hash, BLAKE2S_DIGEST_LENGTH, pub,
                                 *(const ed25519_signature *)vhdr->sig));
}

void vendor_header_hash(const vendor_header *const vhdr, uint8_t *hash) {
  BLAKE2S_CTX ctx;
  blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  blake2s_Update(&ctx, vhdr->vstr, vhdr->vstr_len);
  blake2s_Update(&ctx, "Trezor Vendor Header", 20);
  blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);
}

secbool check_single_hash(const uint8_t *const hash, const uint8_t *const data,
                          int len) {
  uint8_t h[BLAKE2S_DIGEST_LENGTH];
  blake2s(data, len, h, BLAKE2S_DIGEST_LENGTH);
  return sectrue * (0 == memcmp(h, hash, BLAKE2S_DIGEST_LENGTH));
}
//
secbool check_image_contents(const image_header *const hdr, uint32_t firstskip,
                             const flash_area_t *area) {
  if (0 == area) {
    return secfalse;
  }

  const void *data =
      flash_area_get_address(area, firstskip, IMAGE_CHUNK_SIZE - firstskip);
  if (!data) {
    return secfalse;
  }
  int remaining = hdr->codelen;
  if (sectrue !=
      check_single_hash(hdr->hashes, data,
                        MIN(remaining, IMAGE_CHUNK_SIZE - firstskip))) {
    return secfalse;
  }

  remaining -= IMAGE_CHUNK_SIZE - firstskip;

  int chunk = 1;

  while (remaining > 0) {
    data = flash_area_get_address(area, chunk * IMAGE_CHUNK_SIZE,
                                  IMAGE_CHUNK_SIZE);
    if (!data) {
      return secfalse;
    }
    if (sectrue != check_single_hash(hdr->hashes + chunk * 32, data,
                                     MIN(remaining, IMAGE_CHUNK_SIZE))) {
      return secfalse;
    }
    chunk++;
    remaining -= IMAGE_CHUNK_SIZE;
  }

  return sectrue;
}
