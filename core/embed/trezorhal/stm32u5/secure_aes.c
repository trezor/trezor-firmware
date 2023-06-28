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

#include <secure_aes.h>
#include STM32_HAL_H

#include <stdio.h>
#include <stm32u5xx_hal_cryp.h>

secbool secure_aes_init(void) {
  RCC_OscInitTypeDef osc_init_def = {0};
  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_SHSI;
  osc_init_def.SHSIState = RCC_SHSI_ON;

  // Enable SHSI clock
  if (HAL_RCC_OscConfig(&osc_init_def) != HAL_OK) {
    return secfalse;
  }

  // Enable SAES peripheral clock
  __HAL_RCC_SAES_CLK_ENABLE();

  return sectrue;
}

static void secure_aes_load_bhk(void) {
  TAMP->BKP7R;
  TAMP->BKP6R;
  TAMP->BKP5R;
  TAMP->BKP4R;
  TAMP->BKP3R;
  TAMP->BKP2R;
  TAMP->BKP1R;
  TAMP->BKP0R;
}

secbool secure_aes_encrypt(uint32_t* input, size_t size, uint32_t* output) {
  CRYP_HandleTypeDef hcryp = {0};
  uint32_t iv[] = {0, 0, 0, 0};

  hcryp.Instance = SAES;
  hcryp.Init.DataType = CRYP_NO_SWAP;
  hcryp.Init.KeySelect = CRYP_KEYSEL_HSW;
  hcryp.Init.KeySize = CRYP_KEYSIZE_256B;
  hcryp.Init.pKey = NULL;
  hcryp.Init.pInitVect = iv;
  hcryp.Init.Algorithm = CRYP_AES_ECB;
  hcryp.Init.Header = NULL;
  hcryp.Init.HeaderSize = 0;
  hcryp.Init.DataWidthUnit = CRYP_DATAWIDTHUNIT_WORD;
  hcryp.Init.HeaderWidthUnit = CRYP_HEADERWIDTHUNIT_BYTE;
  hcryp.Init.KeyIVConfigSkip = CRYP_KEYIVCONFIG_ALWAYS;
  hcryp.Init.KeyMode = CRYP_KEYMODE_NORMAL;

  if (HAL_CRYP_Init(&hcryp) != HAL_OK) {
    return secfalse;
  }

  secure_aes_load_bhk();

  if (HAL_CRYP_Encrypt(&hcryp, input, size, output, HAL_MAX_DELAY) != HAL_OK) {
    return secfalse;
  }

  HAL_CRYP_DeInit(&hcryp);

  return sectrue;
}

secbool secure_aes_decrypt(uint32_t* input, size_t size, uint32_t* output) {
  CRYP_HandleTypeDef hcryp = {0};
  uint32_t iv[] = {0, 0, 0, 0};

  hcryp.Instance = SAES;
  hcryp.Init.DataType = CRYP_NO_SWAP;
  hcryp.Init.KeySelect = CRYP_KEYSEL_HSW;
  hcryp.Init.KeySize = CRYP_KEYSIZE_256B;
  hcryp.Init.pKey = NULL;
  hcryp.Init.pInitVect = iv;
  hcryp.Init.Algorithm = CRYP_AES_ECB;
  hcryp.Init.Header = NULL;
  hcryp.Init.HeaderSize = 0;
  hcryp.Init.DataWidthUnit = CRYP_DATAWIDTHUNIT_BYTE;
  hcryp.Init.HeaderWidthUnit = CRYP_HEADERWIDTHUNIT_BYTE;
  hcryp.Init.KeyIVConfigSkip = CRYP_KEYIVCONFIG_ALWAYS;
  hcryp.Init.KeyMode = CRYP_KEYMODE_NORMAL;

  if (HAL_CRYP_Init(&hcryp) != HAL_OK) {
    return secfalse;
  }

  secure_aes_load_bhk();

  if (HAL_CRYP_Decrypt(&hcryp, input, size, output, HAL_MAX_DELAY) != HAL_OK) {
    return secfalse;
  }

  HAL_CRYP_DeInit(&hcryp);

  return sectrue;
}
