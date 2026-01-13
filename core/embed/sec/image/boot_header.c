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
#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>

#include <../vendor/sphincsplus/ref/api.h>
#include <ed25519-donna/ed25519.h>

#include <version.h>

#ifdef BOOTLOADER
extern const uint8_t _bootloader_code_size;

typedef union {
  boot_header_auth_t hdr;
  uint8_t raw[BOOT_HEADER_MAXSIZE];
} boot_header_padded_t;

__attribute__((section(".header")))
const boot_header_padded_t g_bootloader_header = {
    .hdr = {
        .magic = BOOT_HEADER_MAGIC_TRZQ,
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
        .min_prev_version =
            {
                .major = 0,
                .minor = 0,
                .patch = 0,
                .build = 0,
            },
        .monotonic_version = BOOTLOADER_MONOTONIC_VERSION,
        // The sigmask field is properly initialized later by headertool_pq
        // (= 0 => no keys used for signature verification; prevents booting)
        .sigmask = 0,
        .header_size = BOOT_HEADER_MAXSIZE,
        // The authenticated part size is calculated for a zero-length Merkle
        // proof, since the Merkle proof is not known at compile time.
        // headertool_pq must update this value later when adding the Merkle
        // proof to the header.
        .auth_size = BOOT_HEADER_MAXSIZE - sizeof(boot_header_merkle_proof_t) -
                     sizeof(boot_header_unauth_t),
        .code_size = (uint32_t)&_bootloader_code_size,
        .storage_address = STORAGE_1_START,
    }};
#endif

static const uint8_t * const BOARDLOADER_PQ_KEYS[] = {
#if !PRODUCTION
    (const uint8_t*) "\xec\x01\xe6\x02\x63\x02\x4f\x7e\x71\x72\x80\x13\xb7\x31\xf7\xba\x12\x99\xf5\x18\xc2\x7b\xa3\xed\x8f\x4a\x21\x99\x74\x12\x7c\x62",
    (const uint8_t*) "\x8a\xf8\x87\x80\x85\x94\x6e\xd8\xb1\x16\xbd\x24\xc0\xf2\xaa\xc4\x8b\x7e\x8f\x11\xbf\x06\x87\x25\xcc\xfb\xb1\x52\xab\xf7\xa4\xcd",
#else
    MODEL_BOARDLOADER_PQ_KEYS
#endif
};

static const uint8_t * const BOARDLOADER_EC_KEYS[] = {
#if !PRODUCTION
    (const uint8_t*) "\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
    (const uint8_t*) "\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
#else
    MODEL_BOARDLOADER_EC_KEYS
#endif
};

secbool boot_header_check_signature(const boot_header_auth_t* hdr,
                                    const merkle_proof_node_t* merkle_root) {
  // Get the signature indices based on the signature mask
  _Static_assert(ARRAY_LENGTH(BOARDLOADER_PQ_KEYS) <= 3);
  _Static_assert(ARRAY_LENGTH(BOARDLOADER_EC_KEYS) ==
                 ARRAY_LENGTH(BOARDLOADER_PQ_KEYS));

  uint8_t sigmask = hdr->sigmask;
  uint8_t sigmask_inv = 0;  // FIH

  const boot_header_unauth_t* sig = boot_header_unauth_get(hdr);

  for (int sig_idx = 0; sig_idx < ARRAY_LENGTH(sig->ec_signature); sig_idx++) {
    // Get the index of the public key in the signature mask
    int key_idx = __builtin_ctz(sigmask);
    if (key_idx >= ARRAY_LENGTH(BOARDLOADER_PQ_KEYS)) {
      return secfalse;
    }

    // Hash of the Merkle root and the SLH signature
    uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];
    IMAGE_HASH_CTX ctx;
    IMAGE_HASH_INIT(&ctx);
    IMAGE_HASH_UPDATE(&ctx, merkle_root->bytes, sizeof(merkle_root->bytes));
    IMAGE_HASH_UPDATE(&ctx, sig->slh_signature[sig_idx],
                      sizeof(sig->slh_signature[sig_idx]));
    IMAGE_HASH_FINAL(&ctx, hash);

    // Verify EC signature - do it before we verify the PQC signature
    int ec_result =
        ed25519_sign_open(hash, sizeof(hash), BOARDLOADER_EC_KEYS[key_idx],
                          sig->ec_signature[sig_idx]);

    if (ec_result != 0) {
      return secfalse;
    }

    // Verify the PQC signature
    int pq_result = crypto_sign_verify(
        sig->slh_signature[sig_idx], sizeof(sig->slh_signature[sig_idx]),
        merkle_root->bytes, sizeof(merkle_root->bytes),
        BOARDLOADER_PQ_KEYS[key_idx]);

    if (pq_result != 0) {
      return secfalse;
    }

    // Mark the key as used
    sigmask &= ~(1 << key_idx);
    sigmask_inv |= (1 << key_idx);
  }

  if (sigmask != 0 || sigmask_inv != hdr->sigmask) {  // FIH
    // There were more than BOOT_HEADER_SIGNATURE_COUNT public key bits
    // set or some of the public keys in the original sigmask were not used.
    return secfalse;
  }

  return sectrue;
}

static size_t boot_header_merkle_proof_size(
    const boot_header_merkle_proof_t* proof) {
  return sizeof(boot_header_merkle_proof_t) +
         proof->node_count * sizeof(proof->nodes[0]);
}

static const boot_header_merkle_proof_t* boot_header_get_merkle_proof(
    const boot_header_auth_t* hdr) {
  // Check if the merkle_proof.path_len field is within the header
  if (hdr->auth_size + sizeof(boot_header_merkle_proof_t) > hdr->header_size) {
    return NULL;
  }

  // Merkle proof is located right after the authenticated part of the header
  boot_header_merkle_proof_t* proof =
      (boot_header_merkle_proof_t*)((uintptr_t)hdr + hdr->auth_size);

  // Check if the path length is in reasonable limits
  if (proof->node_count > BOOT_HEADER_MERKLE_PROOF_MAXLEN) {
    return NULL;
  }

  size_t proof_size = boot_header_merkle_proof_size(proof);

  // Check if the Merkle proof is completely within the header
  if (hdr->auth_size + proof_size > hdr->header_size) {
    return NULL;
  }

  return proof;
}

const boot_header_auth_t* boot_header_auth_get(uint32_t address) {
  boot_header_auth_t* hdr = (boot_header_auth_t*)address;

  // Check if the header starts with the magic
  if (hdr->magic != BOOT_HEADER_MAGIC_TRZQ) {
    return NULL;
  }

  // Check if the header size (= bootloader code offset) is aligned to 8K
  // boundary (flash page size)
  if (!IS_ALIGNED(hdr->header_size, SIZE_8K) || hdr->header_size == 0) {
    return NULL;
  }

  // Check if the header size is in reasonable limits
  if (hdr->header_size >= SIZE_64K) {
    return NULL;
  }

  // Check if the authenticated part size is within the header size
  if (hdr->auth_size >= hdr->header_size) {
    return NULL;
  }

  // Check if the size of the authenticated part is at least the size of the
  // authenticated boot header structure. This condition prevents updating
  // to an image whose authenticated part is smaller than the current
  // authenticated boot header structure.
  if (hdr->auth_size < sizeof(boot_header_auth_t)) {
    return NULL;
  }

  // Check if bootloader code size is within reasonable limits
  if (hdr->code_size < SIZE_8K) {
    return NULL;
  }

  // Check if the hardware model and revision match
  if (hdr->hw_model != HW_MODEL || hdr->hw_revision != HW_REVISION) {
    return secfalse;
  }

  // Check if the header contains a valid Merkle proof
  if (NULL == boot_header_get_merkle_proof(hdr)) {
    return NULL;
  }

  // Check if the header contains a valid unauthenticated part
  if (NULL == boot_header_unauth_get(hdr)) {
    return NULL;
  }

  return hdr;
}

const boot_header_unauth_t* boot_header_unauth_get(
    const boot_header_auth_t* hdr) {
  const boot_header_merkle_proof_t* proof = boot_header_get_merkle_proof(hdr);

  if (proof == NULL) {
    // If the Merkle proof is invalid, the unauthenticated part cannot
    // be valid either
    return NULL;
  }

  size_t proof_size = boot_header_merkle_proof_size(proof);

  // Unauthenticated part is located right after the Merkle proof
  boot_header_unauth_t* unauth =
      (boot_header_unauth_t*)((uintptr_t)proof + proof_size);

  // Check if the unauthenticated part is within the header
  if (hdr->auth_size + proof_size + sizeof(boot_header_unauth_t) >
      hdr->header_size) {
    return NULL;
  }

  return unauth;
}

void boot_header_calc_merkle_root(const boot_header_auth_t* hdr,
                                  uint32_t code_address,
                                  merkle_proof_node_t* root) {
  IMAGE_HASH_CTX ctx;

  static const uint8_t prefix0[] = {0x00};
  static const uint8_t prefix1[] = {0x01};

  // Hash the bootloader code
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)code_address, hdr->code_size);
  IMAGE_HASH_FINAL(&ctx, root->bytes);

  // Hash the authenticated part of the header
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)hdr, hdr->auth_size);
  IMAGE_HASH_UPDATE(&ctx, root->bytes, sizeof(root->bytes));
  IMAGE_HASH_FINAL(&ctx, root->bytes);

  const boot_header_merkle_proof_t* proof = boot_header_get_merkle_proof(hdr);

  // Add the Merkle proof nodes to the hash
  for (size_t i = 0; i < proof->node_count; i++) {
    const merkle_proof_node_t* node = &proof->nodes[i];
    IMAGE_HASH_INIT(&ctx);
    IMAGE_HASH_UPDATE(&ctx, prefix1, sizeof(prefix1));
    if (memcmp(node, root->bytes, sizeof(root->bytes)) < 0) {
      IMAGE_HASH_UPDATE(&ctx, node->bytes, sizeof(node->bytes));
      IMAGE_HASH_UPDATE(&ctx, root->bytes, sizeof(root->bytes));
    } else {
      IMAGE_HASH_UPDATE(&ctx, root->bytes, sizeof(root->bytes));
      IMAGE_HASH_UPDATE(&ctx, node->bytes, sizeof(node->bytes));
    }
    IMAGE_HASH_FINAL(&ctx, root->bytes);
  }
}

secbool bootloader_area_needs_update(const boot_header_auth_t* hdr,
                                     uint32_t code_address) {
  boot_header_auth_t* prev_hdr = (boot_header_auth_t*)BOOTLOADER_START;
  if (hdr->header_size == prev_hdr->header_size &&
      hdr->code_size == prev_hdr->code_size &&
      (memcmp(hdr, prev_hdr, hdr->header_size) == 0) &&
      (memcmp((const uint8_t*)code_address,
              (const uint8_t*)prev_hdr + prev_hdr->header_size,
              hdr->code_size) == 0)) {
    return secfalse;
  }
  return sectrue;
}

#endif  // SECURE_MODE
