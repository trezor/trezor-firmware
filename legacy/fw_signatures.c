/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>

#include "ecdsa.h"
#include "fw_signatures.h"
#include "memory.h"
#include "memzero.h"
#include "secbool.h"
#include "secp256k1.h"
#include "sha2.h"

const uint32_t FIRMWARE_MAGIC_NEW = 0x465a5254;  // TRZF

/*
 * There are 3 schemes in history of T1, for clarity naming:
 *
 * - v1 - previously called "old" with TRZR magic header (no longer here)
 * - v2 - previously called "new" with TRZF magic header
 * - v3 - the latest scheme using Trezor's SignMessage and VerifyMessage
 *   style signatures
 *
 * See `debug_signing/README.md` and the scripts there for signatures debug.
 *
 * Latest scheme v3 ref: https://github.com/trezor/trezor-firmware/issues/2513
 */
#define PUBKEYS_V3 3
#define PUBKEYS_V2 5

#if DEBUG_T1_SIGNATURES || BOOTLOADER_QA

// Make build explode if combining debug sigs with production
#if PRODUCTION
#error "Can't have production device with debug keys! Build aborted"
#endif

// These are **only** for debugging signatures with SignMessage
// Use this mnemonic for testing signing:
// "table table table table table table table table table table table advance"
// the "SignMessage"-style public keys, third signing scheme
// See legacy/debug_signing/README.md
static const uint8_t * const pubkey_v3[PUBKEYS_V3] = {
        (const uint8_t *)"\x03\x73\x08\xe1\x40\x77\x16\x1c\x36\x5d\xea\x0f\x5c\x80\xaa\x6c\x5d\xba\x34\x71\x9e\x82\x5b\xd2\x3a\xe5\xf7\xe7\xd2\x98\x8a\xdb\x0f",
        (const uint8_t *)"\x03\x9c\x1b\x24\x60\xe3\x43\x71\x2e\x98\x2e\x07\x32\xe7\xed\x17\xf6\x0d\xe4\xc9\x33\x06\x5b\x71\x70\xd9\x9c\x6e\x7f\xe7\xcc\x7f\x4b",
        (const uint8_t *)"\x03\x15\x2b\x37\xfd\xf1\x26\x11\x12\x74\xc8\x94\xc3\x48\xdc\xc9\x75\xb5\x7c\x11\x5e\xe2\x4c\xeb\x19\xb5\x19\x0a\xc7\xf7\xb6\x51\x73",
};

// the "new", or second signing scheme keys

/*
 Debug private keys for v2 (previously called "new") scheme
 corresponding to pubkeys below as python hexstring array:

 ['4444444444444444444444444444444444444444444444444444444444444444',
  '4545454545454545454545454545454545454545454545454545454545454545',
  'bfc4bca9c9c228a16639d3503d999a733a439210b64cebe757a4fd03ca46a5c8',
  '5518381d95e93e8eb68a294354989906e3828f36b4556a2ad85d8333294eb1b7',
  '1d1d34168760dec092c9ff89377d8659076d2dfd95e0281719c15f90d067e211']
 */

static const uint8_t * const pubkey_v2[PUBKEYS_V2] = {
    (const uint8_t *)"\x03\x2c\x0b\x7c\xf9\x53\x24\xa0\x7d\x05\x39\x8b\x24\x01\x74\xdc\x0c\x2b\xe4\x44\xd9\x6b\x15\x9a\xa6\xc7\xf7\xb1\xe6\x68\x68\x09\x91",
    (const uint8_t *)"\x02\xed\xab\xbd\x16\xb4\x1c\x83\x71\xb9\x2e\xf2\xf0\x4c\x11\x85\xb4\xf0\x3b\x6d\xcd\x52\xba\x9b\x78\xd9\xd7\xc8\x9c\x8f\x22\x11\x45",
    (const uint8_t *)"\x03\x66\x5f\x66\x0a\x50\x52\xbe\x7a\x95\x54\x6a\x02\x17\x90\x58\xd9\x3d\x3e\x08\xa7\x79\x73\x49\x14\x59\x43\x46\x07\x5b\xb0\xaf\xd4",
    (const uint8_t *)"\x03\x66\x63\x5d\x99\x94\x17\xb6\x55\x66\x86\x6c\x65\x63\x0d\x97\x7a\x7a\xe7\x23\xfe\x5f\x6c\x4c\xd1\x7f\xa0\x0f\x08\x8b\xa1\x84\xc1",
    (const uint8_t *)"\x03\xf3\x6c\x7d\x0f\xb6\x15\xad\xa4\x3d\x71\x88\x58\x0f\x15\xeb\xda\x22\xd6\xf6\xb9\xb1\xa9\x2b\xff\x16\xc6\x93\x77\x99\xdc\xbc\x66"
    };

#else  // DEBUG_T1_SIGNATURES is now 0
// These public keys are production keys
// - used in production devices

// the "SignMessage"-style public keys, third signing scheme
static const uint8_t * const pubkey_v3[PUBKEYS_V3] = {
        (const uint8_t *)"\x03\x23\x00\xc1\xbb\x45\x39\xfc\xbf\xca\x25\x90\xbd\xa3\xdd\x20\x93\x82\x6f\x4a\xe4\x37\xbd\xde\xcc\x1a\x2e\x72\x52\x07\x64\xff\x7a",
        (const uint8_t *)"\x02\x33\xba\xea\xeb\xc9\x4a\x2a\x3e\x8b\x11\xf3\x9a\x71\x33\xdb\xf4\x27\xbe\x29\x2f\xcb\xce\xb8\x87\xd7\x1e\xf5\x1e\x85\x39\x5a\x19",
        (const uint8_t *)"\x03\x57\x09\x1f\xa2\x54\xb5\x52\x33\xd0\xbb\x4c\x48\xe1\x06\xc9\x1b\x92\xfd\x07\x88\xeb\xed\x9d\x3a\x91\x67\x19\xf4\x4c\x76\xc0\x15"
};

// the "new", or second signing scheme keys
static const uint8_t * const pubkey_v2[PUBKEYS_V2] = {
        (const uint8_t *)"\x02\xd5\x71\xb7\xf1\x48\xc5\xe4\x23\x2c\x38\x14\xf7\x77\xd8\xfa\xea\xf1\xa8\x42\x16\xc7\x8d\x56\x9b\x71\x04\x1f\xfc\x76\x8a\x5b\x2d",
        (const uint8_t *)"\x03\x63\x27\x9c\x0c\x08\x66\xe5\x0c\x05\xc7\x99\xd3\x2b\xd6\xba\xb0\x18\x8b\x6d\xe0\x65\x36\xd1\x10\x9d\x2e\xd9\xce\x76\xcb\x33\x5c",
        (const uint8_t *)"\x02\x43\xae\xdb\xb6\xf7\xe7\x1c\x56\x3f\x8e\xd2\xef\x64\xec\x99\x81\x48\x25\x19\xe7\xef\x4f\x4a\xa9\x8b\x27\x85\x4e\x8c\x49\x12\x6d",
        (const uint8_t *)"\x02\x87\x7c\x39\xfd\x7c\x62\x23\x7e\x03\x82\x35\xe9\xc0\x75\xda\xb2\x61\x63\x0f\x78\xee\xb8\xed\xb9\x24\x87\x15\x9f\xff\xed\xfd\xf6",
        (const uint8_t *)"\x03\x73\x84\xc5\x1a\xe8\x1a\xdd\x0a\x52\x3a\xdb\xb1\x86\xc9\x1b\x90\x6f\xfb\x64\xc2\xc7\x65\x80\x2b\xf2\x6d\xbd\x13\xbd\xf1\x2c\x31"
};
#endif

#define FLASH_META_START 0x08008000
#define FLASH_META_CODELEN (FLASH_META_START + 0x0004)
#define FLASH_META_SIGINDEX1 (FLASH_META_START + 0x0008)
#define FLASH_META_SIGINDEX2 (FLASH_META_START + 0x0009)
#define FLASH_META_SIGINDEX3 (FLASH_META_START + 0x000A)
#define FLASH_OLD_APP_START 0x08010000
#define FLASH_META_SIG1 (FLASH_META_START + 0x0040)
#define FLASH_META_SIG2 (FLASH_META_START + 0x0080)
#define FLASH_META_SIG3 (FLASH_META_START + 0x00C0)

/*
 * 0x18 in message prefix is coin info, 0x20 is the length of hash
 * that follows.
 * See `core/src/apps/bitcoin/sign_message.py`.
 */
#define VERIFYMESSAGE_PREFIX \
  ("\x18"                    \
   "Bitcoin Signed Message:\n\x20")
#define PREFIX_LENGTH (sizeof(VERIFYMESSAGE_PREFIX) - 1)
#define SIGNED_LENGTH (PREFIX_LENGTH + 32)

void compute_firmware_fingerprint(const image_header *hdr, uint8_t hash[32]) {
  image_header copy = {0};
  memcpy(&copy, hdr, sizeof(image_header));
  memzero(copy.sig1, sizeof(copy.sig1));
  memzero(copy.sig2, sizeof(copy.sig2));
  memzero(copy.sig3, sizeof(copy.sig3));
  copy.sigindex1 = 0;
  copy.sigindex2 = 0;
  copy.sigindex3 = 0;
  sha256_Raw((const uint8_t *)&copy, sizeof(image_header), hash);
}

void compute_firmware_fingerprint_for_verifymessage(const image_header *hdr,
                                                    uint8_t hash[32]) {
  uint8_t prefixed_header[SIGNED_LENGTH] = VERIFYMESSAGE_PREFIX;
  uint8_t header_hash[32];
  uint8_t hash_before_double_hashing[32];
  compute_firmware_fingerprint(hdr, header_hash);
  memcpy(prefixed_header + PREFIX_LENGTH, header_hash, sizeof(header_hash));
  sha256_Raw(prefixed_header, sizeof(prefixed_header),
             hash_before_double_hashing);
  // We need to do hash the previous result again because SignMessage
  // computes it this way, see `core/src/apps/bitcoin/sign_message.py`
  sha256_Raw(hash_before_double_hashing, sizeof(hash_before_double_hashing),
             hash);
}

bool firmware_present_new(void) {
  const image_header *hdr =
      (const image_header *)FLASH_PTR(FLASH_FWHEADER_START);
  if (hdr->magic != FIRMWARE_MAGIC_NEW) return false;
  // we need to ignore hdrlen for now
  // because we keep reset_handler ptr there
  // for compatibility with older bootloaders
  // after this is no longer necessary, let's uncomment the line below:
  // if (hdr->hdrlen != FLASH_FWHEADER_LEN) return false;
  if (hdr->codelen > FLASH_APP_LEN) return false;
  if (hdr->codelen < 4096) return false;

  return true;
}

int signatures_ok(const image_header *hdr, uint8_t store_fingerprint[32],
                  secbool use_verifymessage) {
  uint8_t hash[32] = {0};
  // which set of public keys depend on scheme
  const uint8_t *const *pubkey_ptr = NULL;
  uint8_t pubkeys = 0;
  if (use_verifymessage == sectrue) {
    pubkey_ptr = pubkey_v3;
    compute_firmware_fingerprint_for_verifymessage(hdr, hash);
    pubkeys = PUBKEYS_V3;
  } else {
    pubkey_ptr = pubkey_v2;
    compute_firmware_fingerprint(hdr, hash);
    pubkeys = PUBKEYS_V2;
  }

  if (store_fingerprint) {
    memcpy(store_fingerprint, hash, 32);
  }

  if (hdr->sigindex1 < 1 || hdr->sigindex1 > pubkeys)
    return SIG_FAIL;  // invalid index
  if (hdr->sigindex2 < 1 || hdr->sigindex2 > pubkeys)
    return SIG_FAIL;  // invalid index
  if (use_verifymessage != sectrue) {
    if (hdr->sigindex3 < 1 || hdr->sigindex3 > pubkeys) {
      return SIG_FAIL;  // invalid index
    }
  } else if (hdr->sigindex3 != 0) {
    return SIG_FAIL;
  }

  if (hdr->sigindex1 == hdr->sigindex2) return SIG_FAIL;  // duplicate use
  if (hdr->sigindex1 == hdr->sigindex3) return SIG_FAIL;  // duplicate use
  if (hdr->sigindex2 == hdr->sigindex3) return SIG_FAIL;  // duplicate use

  if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex1 - 1],
                               hdr->sig1, hash)) {  // failure
    return SIG_FAIL;
  }
  if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex2 - 1],
                               hdr->sig2, hash)) {  // failure
    return SIG_FAIL;
  }
  if (use_verifymessage != sectrue) {
    if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex3 - 1],
                                 hdr->sig3, hash))  // failure
    {
      return SIG_FAIL;
    }
  } else {
    for (unsigned int i = 0; i < sizeof(hdr->sig3); i++) {
      if (hdr->sig3[i] != 0) {
        return SIG_FAIL;
      }
    }
  }

  return SIG_OK;
}

int signatures_match(const image_header *hdr, uint8_t store_fingerprint[32]) {
  int result = 0;
  // Return success if v3 ("verify message") or the v2 ("new") style matches.
  // Use XOR to always force computing both signatures to avoid potential
  // timing side channels.
  // Return only the hash for the v2 computation so that it is
  // the same shown in previous bootloader.
  result ^= signatures_ok(hdr, store_fingerprint, secfalse);
  result ^= signatures_ok(hdr, NULL, sectrue);
  if (result != SIG_OK) {
    return SIG_FAIL;
  }
  return SIG_OK;
}

int mem_is_empty(const uint8_t *src, uint32_t len) {
  for (uint32_t i = 0; i < len; i++) {
    if (src[i]) return 0;
  }
  return 1;
}

int check_firmware_hashes(const image_header *hdr) {
  uint8_t hash[32] = {0};
  // check hash of the first code chunk
  sha256_Raw(FLASH_PTR(FLASH_APP_START), (64 - 1) * 1024, hash);
  if (0 != memcmp(hash, hdr->hashes, 32)) return SIG_FAIL;
  // check remaining used chunks
  uint32_t total_len = FLASH_FWHEADER_LEN + hdr->codelen;
  int used_chunks = total_len / FW_CHUNK_SIZE;
  if (total_len % FW_CHUNK_SIZE > 0) {
    used_chunks++;
  }
  for (int i = 1; i < used_chunks; i++) {
    sha256_Raw(FLASH_PTR(FLASH_FWHEADER_START + (64 * i) * 1024), 64 * 1024,
               hash);
    if (0 != memcmp(hdr->hashes + 32 * i, hash, 32)) return SIG_FAIL;
  }
  // check unused chunks
  for (int i = used_chunks; i < 16; i++) {
    if (!mem_is_empty(hdr->hashes + 32 * i, 32)) return SIG_FAIL;
  }
  // all OK
  return SIG_OK;
}
