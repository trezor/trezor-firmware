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

#include <sec/boot_header.h>
#include <sec/firmware_manifest.h>
#include <sec/fw_variant.h>
#include <sec/tree_preamble.h>

#ifndef USE_BOOT_UCB
#error "pq_secure_boot needs boot_ucb (boot header is staged via the UCB)"
#endif

secbool tree_preamble_check(const uint8_t *preamble, size_t len,
                            tree_preamble_info_t *info) {
  if (preamble == NULL || info == NULL) {
    return secfalse;
  }
  memset(info, 0, sizeof(*info));

  // The prefix is self-describing, so the manifest is located the same way the
  // bootloader will locate it.
  size_t prefix_len = 0;
  if (sectrue != boot_header_prefix_extent(preamble, len, &prefix_len)) {
    return secfalse;
  }
  if (prefix_len >= len) {
    // Nothing left for a manifest.
    return secfalse;
  }

  const boot_header_auth_t *hdr = (const boot_header_auth_t *)preamble;
  if (hdr->hw_model != HW_MODEL || hdr->hw_revision != HW_REVISION) {
    return secfalse;
  }

  const uint8_t *mh = preamble + prefix_len;
  const size_t mh_len = len - prefix_len;
  const firmware_manifest_t *manifest = (const firmware_manifest_t *)mh;
  if (mh_len < sizeof(firmware_manifest_t) ||
      manifest->magic != FW_MANIFEST_MAGIC) {
    return secfalse;
  }
  const size_t manifest_len = firmware_manifest_size(manifest);
  if (manifest_len > mh_len) {
    return secfalse;
  }

  // Fold the variant leaf through the embedded co-path to the prefix's own
  // firmware_root; reads no module code.
  merkle_proof_node_t root;
  memcpy(root.bytes, hdr->firmware_root.bytes, sizeof(root.bytes));
  const merkle_proof_node_t *proof = NULL;
  size_t proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, mh_len, &proof,
                                              &proof_count) ||
      sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, &root)) {
    return secfalse;
  }

  // Only the manifest is hashed, not its trailing proof -- same extent as the
  // bootloader.
  if (sectrue != boot_header_consent_digest(preamble, prefix_len, mh,
                                            manifest_len,
                                            &info->consent_digest)) {
    return secfalse;
  }

  // The variant is authenticated (inside the folded manifest).
  const char *vendor = firmware_vendor_str(manifest->firmware_variant);
  info->vstr_len = MIN(sizeof(info->vstr), strlen(vendor));
  memcpy(info->vstr, vendor, info->vstr_len);

  memcpy(info->version, manifest->firmware_version, sizeof(info->version));
  info->firmware_root = root;

  return sectrue;
}
