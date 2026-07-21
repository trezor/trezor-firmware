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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/ext_flash_otfdec.h>
#include <sec/secure_aes.h>

#include "memzero.h"

// OCTOSPI1 memory-mapped base address and flash size (AT25SF161B, 2 MiB).
// Duplicated here to avoid a sys/ext_flash.h dependency in the sec build.
#define OTFDEC_MMAP_BASE 0x90000000UL
#define OTFDEC_MMAP_SIZE (2UL * 1024UL * 1024UL)

// Diversification label used to bind the OTFDEC region key to this specific
// use case.  Exactly 16 bytes so that a single AES block covers it.
// Changing this value invalidates all previously encrypted flash content.
// TODO: replace with HKDF or equivalent once the KDF design is finalised.
static const uint8_t OTFDEC_KDF_LABEL[16] = "OTFDEC1/extflsh";

secbool ext_flash_otfdec_init(const uint32_t nonce[2], uint16_t version) {
  // Derive a device-unique 128-bit OTFDEC key from the hardware unique key
  // (DHUK) by encrypting a fixed diversification label with AES-256-ECB
  // (SAES peripheral, CRYP_KEYSEL_HW).  The 16-byte ciphertext block
  // becomes the AES-128 region key.
  //
  // SAES must already be initialised by the caller (secure_aes_init()).
  uint32_t key[4] = {0};
  if (sectrue !=
      secure_aes_ecb_encrypt_hw(OTFDEC_KDF_LABEL, sizeof(OTFDEC_KDF_LABEL),
                                 (uint8_t *)key, SECURE_AES_KEY_DHUK_SP)) {
    return secfalse;
  }

  OTFDEC_HandleTypeDef hotfdec = {0};
  hotfdec.Instance = OTFDEC1;

  if (HAL_OTFDEC_Init(&hotfdec) != HAL_OK) {
    memzero(key, sizeof(key));
    return secfalse;
  }

  // Limit OTFDEC configuration access to privileged mode.
  if (HAL_OTFDEC_ConfigAttributes(&hotfdec, OTFDEC_ATTRIBUTE_PRIV) != HAL_OK) {
    goto fail;
  }

  // Decrypt both instruction and data fetches from the mmap window.
  if (HAL_OTFDEC_RegionSetMode(
          &hotfdec, OTFDEC_REGION1,
          OTFDEC_REG_MODE_INSTRUCTION_OR_DATA_ACCESSES) != HAL_OK) {
    goto fail;
  }

  // Write the derived key into the region key registers (write-only hardware).
  if (HAL_OTFDEC_RegionSetKey(&hotfdec, OTFDEC_REGION1, key) != HAL_OK) {
    goto fail;
  }
  // Key is now held exclusively in the OTFDEC hardware; zero the local copy.
  memzero(key, sizeof(key));

  // Configure the address window and cryptographic parameters.
  OTFDEC_RegionConfigTypeDef region_cfg = {
      .Nonce = {nonce[0], nonce[1]},
      .StartAddress = OTFDEC_MMAP_BASE,
      .EndAddress = OTFDEC_MMAP_BASE + OTFDEC_MMAP_SIZE - 1UL,
      .Version = version,
  };
  if (HAL_OTFDEC_RegionConfig(&hotfdec, OTFDEC_REGION1, &region_cfg,
                               OTFDEC_REG_CONFIGR_LOCK_DISABLE) != HAL_OK) {
    goto fail;
  }

  // Activate on-the-fly decryption on every read from the mmap window.
  if (HAL_OTFDEC_RegionEnable(&hotfdec, OTFDEC_REGION1) != HAL_OK) {
    goto fail;
  }

  return sectrue;

fail:
  memzero(key, sizeof(key));
  HAL_OTFDEC_DeInit(&hotfdec);
  return secfalse;
}

void ext_flash_otfdec_deinit(void) {
  OTFDEC_HandleTypeDef hotfdec = {0};
  hotfdec.Instance = OTFDEC1;
  HAL_OTFDEC_RegionDisable(&hotfdec, OTFDEC_REGION1);
  HAL_OTFDEC_DeInit(&hotfdec);
}

#endif  // SECURE_MODE
