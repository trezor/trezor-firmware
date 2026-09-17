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

/*
 * Interaction-less upgrade consent over the boot header prefix. Unlike the
 * rest of the boot header (boot_header.c), not secure-mode gated: the firmware
 * computes the digest too, from just the prefix. Built verbatim by the host
 * tests. Both sides (bootloader from a full header, firmware from just the
 * prefix) must compute bit-identical results.
 */

// In a host test build these come from its shim header.
#ifndef SEC_IMAGE_SHIMMED
#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>
#endif

secbool boot_header_prefix_extent(const uint8_t* data, size_t len,
                                  size_t* out_extent) {
  if (data == NULL || out_extent == NULL) {
    return secfalse;
  }
  if (len < sizeof(boot_header_auth_t)) {
    return secfalse;
  }

  const boot_header_auth_t* hdr = (const boot_header_auth_t*)data;
  if (hdr->magic != BOOT_HEADER_MAGIC_TRZQ) {
    return secfalse;
  }
  // Same floor boot_header_auth_get enforces.
  if (hdr->auth_size < sizeof(boot_header_auth_t)) {
    return secfalse;
  }
  if (hdr->auth_size > len ||
      len - hdr->auth_size < sizeof(boot_header_merkle_proof_t)) {
    return secfalse;
  }

  // The Merkle proof sits immediately after the authenticated part.
  const boot_header_merkle_proof_t* proof =
      (const boot_header_merkle_proof_t*)(data + hdr->auth_size);
  if (proof->node_count > BOOT_HEADER_MERKLE_PROOF_MAXLEN) {
    return secfalse;
  }
  const size_t proof_size = boot_header_merkle_proof_size(proof);
  if (len - hdr->auth_size < proof_size) {
    return secfalse;
  }

  *out_extent = (size_t)hdr->auth_size + proof_size;
  return sectrue;
}

secbool boot_header_consent_digest(const uint8_t* prefix, size_t prefix_len,
                                   const uint8_t* manifest, size_t manifest_len,
                                   merkle_proof_node_t* out) {
  if (prefix == NULL || prefix_len == 0 || manifest == NULL ||
      manifest_len == 0 || out == NULL) {
    return secfalse;
  }

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix, prefix_len);
  IMAGE_HASH_UPDATE(&ctx, manifest, manifest_len);
  IMAGE_HASH_FINAL(&ctx, out->bytes);

  return sectrue;
}
