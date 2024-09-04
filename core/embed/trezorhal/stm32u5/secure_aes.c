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

#include <mpu.h>
#include <secure_aes.h>
#include STM32_HAL_H

#include <stdio.h>
#include <stm32u5xx_hal_cryp.h>
#include <string.h>
#include "model.h"
#include "syscall.h"

#include "memzero.h"

#define SAES_DATA_SIZE_WITH_UPRIV_KEY 32
#define AES_BLOCK_SIZE 16

#ifdef KERNEL_MODE

#include "irq.h"

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

#ifdef SYSCALL_DISPATCH

__attribute__((section(".udata")))
uint32_t saes_input[SAES_DATA_SIZE_WITH_UPRIV_KEY / sizeof(uint32_t)];

__attribute__((section(".udata")))
uint32_t saes_output[SAES_DATA_SIZE_WITH_UPRIV_KEY / sizeof(uint32_t)];

__attribute__((section(".uflash"), used, naked, no_stack_protector)) uint32_t
saes_invoke(void) {
  // reset the key loaded in SAES
  MODIFY_REG(SAES->CR, AES_CR_KEYSEL, CRYP_KEYSEL_NORMAL);

  while (HAL_IS_BIT_SET(SAES->SR, CRYP_FLAG_BUSY)) {
  }
  while (HAL_IS_BIT_SET(SAES->ISR, CRYP_FLAG_RNGEIF)) {
  }

  MODIFY_REG(SAES->CR,
             AES_CR_KMOD | AES_CR_DATATYPE | AES_CR_KEYSIZE | AES_CR_CHMOD |
                 AES_CR_KEYSEL | AES_CR_KEYPROT,
             CRYP_KEYMODE_NORMAL | CRYP_NO_SWAP | CRYP_KEYSIZE_256B |
                 CRYP_AES_ECB | CRYP_KEYSEL_HSW | CRYP_KEYPROT_DISABLE);

  TAMP->BKP0R;
  TAMP->BKP1R;
  TAMP->BKP2R;
  TAMP->BKP3R;
  TAMP->BKP4R;
  TAMP->BKP5R;
  TAMP->BKP6R;
  TAMP->BKP7R;

#define CRYP_OPERATINGMODE_ENCRYPT 0x00000000U /*!< Encryption mode(Mode 1) */

  /* Set the operating mode and normal key selection */
  MODIFY_REG(SAES->CR, AES_CR_MODE | AES_CR_KMOD,
             CRYP_OPERATINGMODE_ENCRYPT | CRYP_KEYMODE_NORMAL);

  SAES->CR |= AES_CR_EN;

  for (int j = 0; j < SAES_DATA_SIZE_WITH_UPRIV_KEY / AES_BLOCK_SIZE; j++) {
    /* Write the input block in the IN FIFO */
    SAES->DINR = saes_input[j * 4 + 0];
    SAES->DINR = saes_input[j * 4 + 1];
    SAES->DINR = saes_input[j * 4 + 2];
    SAES->DINR = saes_input[j * 4 + 3];

    while (HAL_IS_BIT_CLR(SAES->ISR, AES_ISR_CCF)) {
    }

    /* Clear CCF Flag */
    SET_BIT(SAES->ICR, CRYP_CLEAR_CCF);

    /* Read the output block from the output FIFO */
    for (int i = 0U; i < 4U; i++) {
      saes_output[j * 4 + i] = SAES->DOUTR;
    }
  }

  SAES->CR &= ~AES_CR_EN;

  // reset the key loaded in SAES
  MODIFY_REG(SAES->CR, AES_CR_KEYSEL, CRYP_KEYSEL_NORMAL);

  syscall_return_from_callback(sectrue);
  return 0;
}

extern uint32_t sram_u_start;
extern uint32_t sram_u_end;

secbool unpriv_encrypt(const uint8_t* input, size_t size, uint8_t* output,
                       secure_aes_keysel_t key) {
  if (size != SAES_DATA_SIZE_WITH_UPRIV_KEY) {
    return secfalse;
  }

  if (key != SECURE_AES_KEY_XORK_SN) {
    return secfalse;
  }

  uint32_t prev_svc_prio = NVIC_GetPriority(SVCall_IRQn);
  NVIC_SetPriority(SVCall_IRQn, IRQ_PRI_HIGHEST);
  uint32_t basepri = __get_BASEPRI();
  __set_BASEPRI(IRQ_PRI_HIGHEST + 1);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SAES);

  memset(&sram_u_start, 0, &sram_u_end - &sram_u_start);
  memcpy(saes_input, input, size);

  SAES->CR |= AES_CR_KEYSEL_0;

  __HAL_RCC_SAES_CLK_DISABLE();
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();
  __HAL_RCC_SAES_CLK_ENABLE();

  secbool retval = invoke_unpriv(saes_invoke);

  __HAL_RCC_SAES_CLK_DISABLE();
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();
  __HAL_RCC_SAES_CLK_ENABLE();

  memcpy(output, saes_output, size);
  memset(&sram_u_start, 0, &sram_u_end - &sram_u_start);

  mpu_reconfig(mpu_mode);

  __set_BASEPRI(basepri);
  NVIC_SetPriority(SVCall_IRQn, prev_svc_prio);

  return retval;
}
#endif

secbool secure_aes_ecb_encrypt_hw(const uint8_t* input, size_t size,
                                  uint8_t* output, secure_aes_keysel_t key) {
#ifdef SYSCALL_DISPATCH
  if (key == SECURE_AES_KEY_XORK_SN) {
    return unpriv_encrypt(input, size, output, key);
  }
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
    return secfalse;
  }

  // Enable SAES peripheral clock
  __HAL_RCC_SAES_CLK_ENABLE();

  return sectrue;
}

#endif
