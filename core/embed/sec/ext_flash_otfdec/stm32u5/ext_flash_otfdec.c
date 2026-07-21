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
#include <sys/mpu.h>

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

typedef struct {
  OTFDEC_HandleTypeDef hotfdec;
  bool initialized;
} ext_flash_otfdec_driver_t;

static ext_flash_otfdec_driver_t g_ext_flash_otfdec_driver;

static void load_le_u32_words(uint32_t words[4], const uint8_t bytes[16]) {
  for (int i = 0; i < 4; i++) {
    words[i] = ((uint32_t)bytes[i * 4 + 0]) |
               ((uint32_t)bytes[i * 4 + 1] << 8) |
               ((uint32_t)bytes[i * 4 + 2] << 16) |
               ((uint32_t)bytes[i * 4 + 3] << 24);
  }
}

secbool ext_flash_otfdec_init(const uint32_t nonce[2], uint16_t version) {
  ext_flash_otfdec_driver_t *drv = &g_ext_flash_otfdec_driver;

  uint8_t key_bytes[16] = {0};
  uint32_t key[4] = {0};
  if (sectrue != secure_aes_ecb_encrypt_hw(OTFDEC_KDF_LABEL,
                                           sizeof(OTFDEC_KDF_LABEL), key_bytes,
                                           SECURE_AES_KEY_DHUK_SP)) {
    return secfalse;
  }
  load_le_u32_words(key, key_bytes);
  memzero(key_bytes, sizeof(key_bytes));

  // Enable the OTFDEC1 clock. In the SECMON build tz_init() does this before
  // the NS world starts; in the non-SECMON prodtest build it is not done
  // elsewhere so we do it here. The call is idempotent.
  __HAL_RCC_OTFDEC1_CLK_ENABLE();

  drv->hotfdec.Instance = OTFDEC1;

  if (HAL_OTFDEC_Init(&drv->hotfdec) != HAL_OK) {
    memzero(key, sizeof(key));
    return secfalse;
  }
  if (HAL_OTFDEC_ConfigAttributes(&drv->hotfdec, OTFDEC_ATTRIBUTE_PRIV) !=
      HAL_OK) {
    goto fail;
  }
  if (HAL_OTFDEC_RegionSetMode(&drv->hotfdec, OTFDEC_REGION1,
                                OTFDEC_REG_MODE_INSTRUCTION_OR_DATA_ACCESSES) !=
      HAL_OK) {
    goto fail;
  }
  if (HAL_OTFDEC_RegionSetKey(&drv->hotfdec, OTFDEC_REGION1, key) != HAL_OK) {
    goto fail;
  }
  memzero(key, sizeof(key));

  OTFDEC_RegionConfigTypeDef region_cfg = {
      .Nonce = {nonce[0], nonce[1]},
      .StartAddress = OTFDEC_MMAP_BASE,
      .EndAddress = OTFDEC_MMAP_BASE + OTFDEC_MMAP_SIZE - 1UL,
      .Version = version,
  };
  // Region NOT locked: CONFIGLOCK=1 silently blocks writes to CR.ENC,
  // preventing cipher() from enabling encipher mode.
  if (HAL_OTFDEC_RegionConfig(&drv->hotfdec, OTFDEC_REGION1, &region_cfg,
                               OTFDEC_REG_CONFIGR_LOCK_DISABLE) != HAL_OK) {
    goto fail;
  }
  drv->initialized = true;
  return sectrue;

fail:
  memzero(key, sizeof(key));
  HAL_OTFDEC_DeInit(&drv->hotfdec);
  memzero(drv, sizeof(*drv));
  return secfalse;
}

void ext_flash_otfdec_deinit(void) {
  ext_flash_otfdec_driver_t *drv = &g_ext_flash_otfdec_driver;

  if (!drv->initialized) return;

  HAL_OTFDEC_RegionDisable(&drv->hotfdec, OTFDEC_REGION1);
  HAL_OTFDEC_DeInit(&drv->hotfdec);
  memzero(drv, sizeof(*drv));
}

bool ext_flash_otfdec_cipher(uint32_t flash_addr, const uint8_t *plaintext,
                              uint32_t byte_len, uint8_t *ciphertext_out) {
  ext_flash_otfdec_driver_t *drv = &g_ext_flash_otfdec_driver;

  if (!drv->initialized) return false;
  if (byte_len == 0u || (byte_len & 15u) != 0u) return false;
  if ((flash_addr & 15u) != 0u) return false;
  if (flash_addr + byte_len > OTFDEC_MMAP_SIZE) return false;

  // CR.ENC can only be written while all regions are disabled: the hardware
  // silently ignores writes to CR.ENC when any region has REG_ENABLE=1.
  // Sequence: disable region → set ENC=1 → re-enable (latches encipher mode)
  // → cipher → disable → clear ENC=0 → re-enable (latches decipher mode).
  //
  // Temporarily open the ext flash mmap window for privileged writes so
  // HAL_OTFDEC_Cipher() can feed plaintext through the OTFDEC AHB path.
  mpu_mode_t saved_mode = mpu_reconfig(MPU_MODE_UNUSED_FLASH);

  HAL_OTFDEC_RegionDisable(&drv->hotfdec, OTFDEC_REGION1);

  if (HAL_OTFDEC_EnableEnciphering(&drv->hotfdec) != HAL_OK) {
    HAL_OTFDEC_RegionEnable(&drv->hotfdec, OTFDEC_REGION1);
    mpu_restore(saved_mode);
    return false;
  }

  HAL_OTFDEC_RegionEnable(&drv->hotfdec, OTFDEC_REGION1);

  HAL_StatusTypeDef rc = HAL_OTFDEC_Cipher(
      &drv->hotfdec, OTFDEC_REGION1, (const uint32_t *)plaintext,
      (uint32_t *)ciphertext_out, byte_len >> 2, OTFDEC_MMAP_BASE + flash_addr);

  HAL_OTFDEC_RegionDisable(&drv->hotfdec, OTFDEC_REGION1);
  HAL_OTFDEC_DisableEnciphering(&drv->hotfdec);
  HAL_OTFDEC_RegionEnable(&drv->hotfdec, OTFDEC_REGION1);

  mpu_restore(saved_mode);

  return (rc == HAL_OK);
}

#endif  // SECURE_MODE
