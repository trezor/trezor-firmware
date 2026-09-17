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

/**
 * Firmware variant, narrow form. Only ever the OUTPUT of fw_variant_to_fw_type
 * (the storage-salt byte); everything stored or compared uses the hardened
 * fw_variant_sec_t codewords below. Values must match vendor_fw_type_t
 * (sec/image.h); static-asserted in fw_variant.c.
 */
typedef enum {
  FW_VARIANT_NONE = 0,       // == VENDOR_FW_TYPE_RESERVED
  FW_VARIANT_CUSTOM = 1,     // == VENDOR_FW_TYPE_CUSTOM (unofficial app slot)
  FW_VARIANT_UNIVERSAL = 2,  // == VENDOR_FW_TYPE_UNIVERSAL
  FW_VARIANT_BITCOIN_ONLY = 3,  // == VENDOR_FW_TYPE_BTC_ONLY
  FW_VARIANT_PRODTEST = 4,      // == VENDOR_FW_TYPE_PRODTEST
} fw_variant_t;

/**
 * Hardened firmware variant, stored as-is in both the authenticated manifest
 * and boot_header_unauth_t.firmware_type. fw_variant_t values are one bit flip
 * apart (CUSTOM(1) -> BITCOIN_ONLY(3), NONE(0) -> PRODTEST(4)); these RM(1,5)
 * codewords are >= 16 flips apart and from 0x00000000 / 0xFFFFFFFF, so
 * zeroed, erased or torn memory decodes to INVALID. FIH: never compare a
 * codeword against a narrow FW_VARIANT_* value (compiles, always false).
 */
typedef uint32_t fw_variant_sec_t;
#define FW_VARIANT_SEC_INVALID 0x00000000U /**< not a variant */
#define FW_VARIANT_SEC_NONE 0xCCCCCCCCU    /**< unprovisioned */
#define FW_VARIANT_SEC_CUSTOM 0x33333333U
#define FW_VARIANT_SEC_UNIVERSAL 0x5A5A5A5AU
#define FW_VARIANT_SEC_BITCOIN_ONLY 0xA5A5A5A5U
#define FW_VARIANT_SEC_PRODTEST 0x66666666U

/** Display name for a hardened variant ("Trezor", "Trezor Bitcoin-only", or
 *  an UNSAFE marker). Must agree with the bootloader's tree_vendor_str. Never
 *  returns NULL. */
const char* firmware_vendor_str(fw_variant_sec_t variant);

/** The ONLY narrowing to the fw_variant_t byte, for the storage KDF
 *  (secret_key_storage_salt). Returns FW_VARIANT_NONE for INVALID. */
uint8_t fw_variant_to_fw_type(fw_variant_sec_t variant);

/** Positive allow-list: sectrue only for a recognized official variant. */
secbool fw_variant_is_official(fw_variant_sec_t variant);

/** sectrue only for FW_VARIANT_SEC_CUSTOM. To grant privileges use
 *  fw_variant_is_official(), never !is_custom. */
secbool fw_variant_is_custom(fw_variant_sec_t variant);

/** sectrue only for one of the four real image variants; NONE and INVALID
 *  both return secfalse. */
secbool fw_variant_is_provisioned(fw_variant_sec_t variant);
