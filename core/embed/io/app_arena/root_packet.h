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

#pragma once

#include <trezor_types.h>

#include <rtl/crypto_helpers.h>
#include <sec/mldsa44.h>

/** Root packet magic number */
#define ROOT_PACKET_MAGIC 0x50525254  // 'TRRP'

/** Supported root packet version */
#define ROOT_PACKET_VERSION 0x01

/** Authenticated part of the root packet */
typedef struct {
  /** Magic constant 'TRRP' */
  uint32_t magic;
  /** Root packet format version */
  uint8_t version;
  /** Bitmask of included Merkle roots. Each bit maps to a ring in
   * app_ring_t. Up to three bits may be set. */
  uint8_t ring_mask;
  /** Bitmask of signature verification keys. Each bit maps to a public key
   * in ROOT_PACKET_KEYS. Exactly two bits must be set. */
  uint8_t sigmask;
  /** Reserved for future use */
  uint8_t reserved[1];
  /** Root packet timestamp */
  uint32_t timestamp;
  /** Merkle roots for the rings in ring_mask. The roots are stored
   * in the order of the bits in ring_mask, from least significant to
   * most significant. */
  sha256_digest_t merkle_root[];
} root_packet_auth_t;

/** Unauthenticated part of the root packet.
 *
 * This part is placed directly after the authenticated part
 * in memory, and contains the signatures of the authenticated part hash.
 */
typedef struct {
  /* Signatures of authenticated root packet part */
  mldsa44_signature_t signature[2];
} root_packet_unauth_t;

/**
 * @brief Verifies the integrity and validity of a root packet.
 *
 * @param data Pointer to the root packet data.
 * @param size Size of the root packet data.
 * @param out Pointer to the output authenticated root packet structure.
 *
 * @return TS_OK if the root packet is valid, otherwise an error code.
 */
ts_t root_packet_verify(const void* data, size_t size,
                        root_packet_auth_t** out);
