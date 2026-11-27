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

#include <sec/merkle.h>

/** What the firmware shows and returns for an offered Merkle-tree release. */
typedef struct {
  // vendor string, derived from the authenticated firmware variant
  uint8_t vstr[64];
  size_t vstr_len;
  // firmware version from the manifest: major, minor, patch, build
  uint8_t version[4];
  // firmware_root, as the bootloader's confirm screen shows it
  merkle_proof_node_t firmware_root;
  // consent digest for reboot_and_upgrade
  merkle_proof_node_t consent_digest;
} tree_update_info_t;

/**
 * @brief Parses a Merkle-tree release offered by the host.
 *
 * The release comes as a boot header PREFIX (auth part + Merkle proof, no
 * signatures) and the firmware manifest region, the two halves of the
 * consent-digest preimage. Runs unprivileged over host bytes; the signature
 * is NOT checked (that needs the bootloader code), so this is
 * self-consistency, not authenticity -- the bootloader recomputes the digest
 * before installing.
 *
 * @param prefix Boot header prefix; must be exactly its own extent
 * @param prefix_len Boot header prefix length
 * @param manifest_region Firmware manifest followed by its Merkle proof
 * @param region_len Manifest region length
 * @param info Filled on success
 * @return sectrue if both parts are well-formed, target this model and the
 *         manifest folds to the prefix's firmware_root
 */
secbool __wur tree_update_check(const uint8_t *prefix, size_t prefix_len,
                                const uint8_t *manifest_region,
                                size_t region_len, tree_update_info_t *info);
