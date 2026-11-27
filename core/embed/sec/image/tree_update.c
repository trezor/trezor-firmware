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
#include <sec/tree_update.h>

#ifndef USE_BOOT_UCB
#error "pq_secure_boot needs boot_ucb (boot header is staged via the UCB)"
#endif

secbool tree_update_check(const uint8_t *prefix, size_t prefix_len,
                          const uint8_t *manifest_region, size_t region_len,
                          tree_update_info_t *info) {
  if (prefix == NULL || manifest_region == NULL || info == NULL) {
    return secfalse;
  }
  memset(info, 0, sizeof(*info));

  // The consent digest hashes prefix || manifest, so the host must not choose
  // where one ends: a shifted split would hash the same bytes while the
  // firmware parses a manifest the bootloader never sees. The prefix has to
  // be exactly the extent the bootloader cuts from the header.
  size_t extent = 0;
  if (sectrue != boot_header_prefix_extent(prefix, prefix_len, &extent) ||
      extent != prefix_len) {
    return secfalse;
  }

  const boot_header_auth_t *hdr = (const boot_header_auth_t *)prefix;
  if (hdr->hw_model != HW_MODEL || hdr->hw_revision != HW_REVISION) {
    return secfalse;
  }

  const firmware_manifest_t *manifest =
      (const firmware_manifest_t *)manifest_region;
  if (region_len < sizeof(firmware_manifest_t) ||
      manifest->magic != FW_MANIFEST_MAGIC) {
    return secfalse;
  }
  const size_t manifest_len = firmware_manifest_size(manifest);
  if (manifest_len > region_len) {
    return secfalse;
  }

  // Fold the variant leaf through the embedded co-path to the prefix's own
  // firmware_root; reads no module code.
  merkle_proof_node_t root;
  memcpy(root.bytes, hdr->firmware_root.bytes, sizeof(root.bytes));
  const merkle_proof_node_t *proof = NULL;
  size_t proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, region_len, &proof,
                                              &proof_count) ||
      sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, &root)) {
    return secfalse;
  }

  // Only the manifest is hashed, not its trailing proof -- same extent as the
  // bootloader.
  if (sectrue != boot_header_consent_digest(prefix, prefix_len, manifest_region,
                                            manifest_len,
                                            &info->consent_digest)) {
    return secfalse;
  }

  // The release version decides upgrade / downgrade, as in the bootloader.
  // Official variants carry it as their firmware_version too; refuse a
  // mismatch here, before the user confirms, rather than in the bootloader
  // after. CUSTOM and PRODTEST keep their own numbering.
  const fw_variant_sec_t variant = manifest->firmware_variant;
  if ((variant == FW_VARIANT_SEC_UNIVERSAL ||
       variant == FW_VARIANT_SEC_BITCOIN_ONLY) &&
      memcmp(&hdr->version, manifest->firmware_version,
             sizeof(manifest->firmware_version)) != 0) {
    return secfalse;
  }

  // The variant is authenticated (inside the folded manifest).
  const char *vendor = firmware_vendor_str(variant);
  info->vstr_len = MIN(sizeof(info->vstr), strlen(vendor));
  memcpy(info->vstr, vendor, info->vstr_len);

  memcpy(info->version, &hdr->version, sizeof(info->version));
  info->firmware_root = root;

  return sectrue;
}
