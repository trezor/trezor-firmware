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
 * Firmware variant helpers. Pure functions over the hardened codeword, so not
 * secure-mode gated, and built verbatim by the host tests.
 */

// In a host test build these come from its shim header.
#ifndef SEC_IMAGE_SHIMMED
#include <sec/fw_variant.h>
#include <sec/image.h>

// fw_variant_t must match vendor_fw_type_t so a variant maps to the same
// firmware_type byte in both schemes.
_Static_assert((int)FW_VARIANT_NONE == (int)VENDOR_FW_TYPE_RESERVED,
               "fw variant");
_Static_assert((int)FW_VARIANT_CUSTOM == (int)VENDOR_FW_TYPE_CUSTOM,
               "fw variant");
_Static_assert((int)FW_VARIANT_UNIVERSAL == (int)VENDOR_FW_TYPE_UNIVERSAL,
               "fw variant");
_Static_assert((int)FW_VARIANT_BITCOIN_ONLY == (int)VENDOR_FW_TYPE_BTC_ONLY,
               "fw variant");
_Static_assert((int)FW_VARIANT_PRODTEST == (int)VENDOR_FW_TYPE_PRODTEST,
               "fw variant");
#endif

uint8_t fw_variant_to_fw_type(fw_variant_sec_t variant) {
  // INVALID and NONE narrow to FW_VARIANT_NONE: an unusable variant must not
  // borrow another domain's salt.
  switch (variant) {
    case FW_VARIANT_SEC_CUSTOM:
      return (uint8_t)FW_VARIANT_CUSTOM;
    case FW_VARIANT_SEC_UNIVERSAL:
      return (uint8_t)FW_VARIANT_UNIVERSAL;
    case FW_VARIANT_SEC_BITCOIN_ONLY:
      return (uint8_t)FW_VARIANT_BITCOIN_ONLY;
    case FW_VARIANT_SEC_PRODTEST:
      return (uint8_t)FW_VARIANT_PRODTEST;
    default:
      return (uint8_t)FW_VARIANT_NONE;
  }
}

secbool fw_variant_is_official(fw_variant_sec_t variant) {
  // Positive allow-list: only an exact codeword match yields sectrue, so a
  // corrupted variant fails toward restricted. `|` keeps every compare live in
  // source, but GCC still predicates them -- not fault-hardened; the real
  // double check is the unlock gate in wf_firmware_update_pq.c.
  return ((variant == FW_VARIANT_SEC_UNIVERSAL) |
          (variant == FW_VARIANT_SEC_BITCOIN_ONLY) |
          (variant == FW_VARIANT_SEC_PRODTEST)) *
         sectrue;
}

secbool fw_variant_is_custom(fw_variant_sec_t variant) {
  // Failure direction and codegen caveat as above.
  return (variant == FW_VARIANT_SEC_CUSTOM) * sectrue;
}

secbool fw_variant_is_provisioned(fw_variant_sec_t variant) {
  // NONE and INVALID yield secfalse. Failure direction and codegen caveat as
  // above.
  return ((variant == FW_VARIANT_SEC_CUSTOM) |
          (variant == FW_VARIANT_SEC_UNIVERSAL) |
          (variant == FW_VARIANT_SEC_BITCOIN_ONLY) |
          (variant == FW_VARIANT_SEC_PRODTEST)) *
         sectrue;
}

// Shared by the secmon (installed image) and the coreapp (offered image); must
// agree with the bootloader's tree_vendor_str.
// FIH: assume UNSAFE unless a positive match names a trusted vendor.
const char* firmware_vendor_str(fw_variant_sec_t variant) {
  if (fw_variant_is_custom(variant) != secfalse) {
    return "UNSAFE, DO NOT USE!";
  }
  switch (variant) {
    case FW_VARIANT_SEC_PRODTEST:
      // Founder-signed but factory-only -- must never be used in the field.
      return "UNSAFE, FACTORY TEST ONLY";
    case FW_VARIANT_SEC_BITCOIN_ONLY:
      return "Trezor Bitcoin-only";
    case FW_VARIANT_SEC_UNIVERSAL:
      return "Trezor";
    default:
      return "UNSAFE, DO NOT USE!";
  }
}
