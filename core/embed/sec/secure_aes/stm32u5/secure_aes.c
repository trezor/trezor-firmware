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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <stm32u5xx_hal_cryp.h>

#include <sec/secure_aes.h>

#if NORCOW_MIN_VERSION <= 5
#include "secure_aes_unpriv.h"
#endif

#include "memzero.h"

#define AES_BLOCK_SIZE 16

#ifdef KERNEL_MODE

static void secure_aes_load_bhk(void) {
  TAMP->BKP0R;
  TAMP->BKP1R;
  TAMP->BKP2R;
  TAMP->BKP3R;
  TAMP->BKP4R;
  TAMP->BKP5R;
  TAMP->BKP6R;
  TAMP->BKP7R;
}

static uint32_t get_keysel(secure_aes_keysel_t key) {
  switch (key) {
    case SECURE_AES_KEY_DHUK_SP:
      return CRYP_KEYSEL_HW;
    case SECURE_AES_KEY_BHK:
      return CRYP_KEYSEL_SW;
    case SECURE_AES_KEY_XORK_SP:
    case SECURE_AES_KEY_XORK_SN:
      return CRYP_KEYSEL_HSW;
    default:
      return 0;
  }
}

static secbool is_key_supported(secure_aes_keysel_t key) {
  switch (key) {
    case SECURE_AES_KEY_DHUK_SP:
    case SECURE_AES_KEY_BHK:
    case SECURE_AES_KEY_XORK_SP:
      return sectrue;
    default:
      return secfalse;
  }
}

secbool secure_aes_ecb_encrypt_hw(const uint8_t* input, size_t size,
                                  uint8_t* output, secure_aes_keysel_t key) {
#if NORCOW_MIN_VERSION <= 5
#ifdef KERNEL
  if (key == SECURE_AES_KEY_XORK_SN) {
    return secure_aes_unpriv_encrypt(input, size, output, key);
  }
#endif
#endif

  if (sectrue != is_key_supported(key)) {
    return secfalse;
  }

  CRYP_HandleTypeDef hcryp = {0};
  uint32_t iv[] = {0, 0, 0, 0};

  if (size % AES_BLOCK_SIZE != 0) {
    return secfalse;
  }

  uint32_t keysel = get_keysel(key);

  hcryp.Instance = SAES;
  hcryp.Init.DataType = CRYP_NO_SWAP;
  hcryp.Init.KeySelect = keysel;
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

  if (keysel == CRYP_KEYSEL_HSW || keysel == CRYP_KEYSEL_SW) {
    secure_aes_load_bhk();
  }

  if ((size_t)input % sizeof(uint32_t) != 0 ||
      (size_t)output % sizeof(uint32_t) != 0) {
    size_t tmp_size = size;
    while (tmp_size >= AES_BLOCK_SIZE) {
      uint32_t input_buffer[AES_BLOCK_SIZE / sizeof(uint32_t)];
      uint32_t output_buffer[AES_BLOCK_SIZE / sizeof(uint32_t)];
      memcpy(input_buffer, input, AES_BLOCK_SIZE);
      if (HAL_CRYP_Encrypt(&hcryp, input_buffer, AES_BLOCK_SIZE, output_buffer,
                           HAL_MAX_DELAY) != HAL_OK) {
        memzero(input_buffer, sizeof(input_buffer));
        memzero(output_buffer, sizeof(output_buffer));
        return secfalse;
      }
      memcpy(output, output_buffer, AES_BLOCK_SIZE);
      input += AES_BLOCK_SIZE;
      output += AES_BLOCK_SIZE;
      tmp_size -= AES_BLOCK_SIZE;

      memzero(input_buffer, sizeof(input_buffer));
      memzero(output_buffer, sizeof(output_buffer));
    }

  } else {
    if (HAL_CRYP_Encrypt(&hcryp, (uint32_t*)input, size, (uint32_t*)output,
                         HAL_MAX_DELAY) != HAL_OK) {
      return secfalse;
    }
  }

  HAL_CRYP_DeInit(&hcryp);

  return sectrue;
}

secbool secure_aes_ecb_decrypt_hw(const uint8_t* input, size_t size,
                                  uint8_t* output, secure_aes_keysel_t key) {
  if (sectrue != is_key_supported(key)) {
    return secfalse;
  }

  CRYP_HandleTypeDef hcryp = {0};
  uint32_t iv[] = {0, 0, 0, 0};

  if (size % AES_BLOCK_SIZE != 0) {
    return secfalse;
  }

  uint32_t keysel = get_keysel(key);

  hcryp.Instance = SAES;
  hcryp.Init.DataType = CRYP_NO_SWAP;
  hcryp.Init.KeySelect = keysel;
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
  if (keysel == CRYP_KEYSEL_HSW || keysel == CRYP_KEYSEL_SW) {
    secure_aes_load_bhk();
  }

  if ((size_t)input % sizeof(uint32_t) != 0 ||
      (size_t)output % sizeof(uint32_t) != 0) {
    size_t tmp_size = size;
    while (tmp_size >= AES_BLOCK_SIZE) {
      uint32_t input_buffer[AES_BLOCK_SIZE / sizeof(uint32_t)];
      uint32_t output_buffer[AES_BLOCK_SIZE / sizeof(uint32_t)];
      memcpy(input_buffer, input, AES_BLOCK_SIZE);
      if (HAL_CRYP_Decrypt(&hcryp, input_buffer, AES_BLOCK_SIZE, output_buffer,
                           HAL_MAX_DELAY) != HAL_OK) {
        memzero(input_buffer, sizeof(input_buffer));
        memzero(output_buffer, sizeof(output_buffer));
        return secfalse;
      }
      memcpy(output, output_buffer, AES_BLOCK_SIZE);
      input += AES_BLOCK_SIZE;
      output += AES_BLOCK_SIZE;
      tmp_size -= AES_BLOCK_SIZE;

      memzero(input_buffer, sizeof(input_buffer));
      memzero(output_buffer, sizeof(output_buffer));
    }

  } else {
    if (HAL_CRYP_Decrypt(&hcryp, (uint32_t*)input, size, (uint32_t*)output,
                         HAL_MAX_DELAY) != HAL_OK) {
      return secfalse;
    }
  }

  HAL_CRYP_DeInit(&hcryp);

  return sectrue;
}

secbool secure_aes_init(void) {
  RCC_OscInitTypeDef osc_init_def = {0};
  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_SHSI;
  osc_init_def.SHSIState = RCC_SHSI_ON;

  // Enable SHSI clock
  if (HAL_RCC_OscConfig(&osc_init_def) != HAL_OK) {
    goto cleanup;
  }

  // Enable SAES peripheral clock
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();
  __HAL_RCC_SAES_CLK_ENABLE();

  return sectrue;

cleanup:
  secure_aes_deinit();
  return secfalse;
}

void secure_aes_deinit(void) {
  __HAL_RCC_SAES_CLK_DISABLE();
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();

  RCC_OscInitTypeDef osc_init_def = {0};
  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_SHSI;
  osc_init_def.SHSIState = RCC_SHSI_OFF;

  // Disable SHSI clock
  HAL_RCC_OscConfig(&osc_init_def);
}

#endif
