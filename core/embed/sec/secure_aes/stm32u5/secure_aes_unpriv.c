
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

#include <sec/secure_aes.h>

#include <stm32u5xx_hal_cryp.h>

#include "secure_aes_unpriv.h"

#include "memzero.h"

#define SAES_DATA_SIZE_WITH_UNPRIV_KEY 32
#define AES_BLOCK_SIZE 16

// -----------------------------------------------------------------------
// Code in unprivileged mode

#ifndef KERNEL_MODE

#include <sys/syscall.h>

uint32_t saes_unpriv_input[SAES_DATA_SIZE_WITH_UNPRIV_KEY / sizeof(uint32_t)];

uint32_t saes_unpriv_output[SAES_DATA_SIZE_WITH_UNPRIV_KEY / sizeof(uint32_t)];

__attribute((no_stack_protector)) void saes_unpriv_callback(void) {
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

  for (int j = 0; j < SAES_DATA_SIZE_WITH_UNPRIV_KEY / AES_BLOCK_SIZE; j++) {
    /* Write the input block in the IN FIFO */
    SAES->DINR = saes_unpriv_input[j * 4 + 0];
    SAES->DINR = saes_unpriv_input[j * 4 + 1];
    SAES->DINR = saes_unpriv_input[j * 4 + 2];
    SAES->DINR = saes_unpriv_input[j * 4 + 3];

    while (HAL_IS_BIT_CLR(SAES->ISR, AES_ISR_CCF)) {
    }

    /* Clear CCF Flag */
    SET_BIT(SAES->ICR, CRYP_CLEAR_CCF);

    /* Read the output block from the output FIFO */
    for (int i = 0U; i < 4U; i++) {
      saes_unpriv_output[j * 4 + i] = SAES->DOUTR;
    }
  }

  SAES->CR &= ~AES_CR_EN;

  // reset the key loaded in SAES
  MODIFY_REG(SAES->CR, AES_CR_KEYSEL, CRYP_KEYSEL_NORMAL);

  return_from_unprivileged_callback(sectrue);
}

#endif  // !KERNEL_MODE

// -----------------------------------------------------------------------
// Code running privileged mode

#ifdef KERNEL

#include <sys/coreapp.h>
#include <sys/mpu.h>
#include <sys/systask.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

static void *secure_aes_unpriv_applet = NULL;

void secure_aes_set_applet(applet_t *applet) {
  secure_aes_unpriv_applet = applet;
}

secbool secure_aes_unpriv_encrypt(const uint8_t *input, size_t size,
                                  uint8_t *output, secure_aes_keysel_t key) {
  if (secure_aes_unpriv_applet == NULL) {
    return secfalse;
  }

  if (size != SAES_DATA_SIZE_WITH_UNPRIV_KEY) {
    return secfalse;
  }

  if (key != SECURE_AES_KEY_XORK_SN) {
    return secfalse;
  }

#ifdef USE_TRUSTZONE
  tz_set_saes_unpriv(true);
  tz_set_tamper_unpriv(true);
#endif  // USE_TRUSTZONE

  applet_t *applet = secure_aes_unpriv_applet;

  const coreapp_header_t *header =
      (coreapp_header_t *)applet->layout.code1.start;

  void *unpriv_input = header->saes_input;
  void *unpriv_output = header->saes_output;
  void *unpriv_callback = header->saes_callback;

  memzero(unpriv_input, SAES_DATA_SIZE_WITH_UNPRIV_KEY);
  memzero(unpriv_output, SAES_DATA_SIZE_WITH_UNPRIV_KEY);
  memcpy(unpriv_input, input, size);

  SAES->CR |= AES_CR_KEYSEL_0;

  __HAL_RCC_SAES_CLK_DISABLE();
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();
  __HAL_RCC_SAES_CLK_ENABLE();

  applet->task.mpu_mode = MPU_MODE_APP_SAES;
  secbool retval =
      systask_invoke_callback(&applet->task, 0, 0, 0, unpriv_callback);
  applet->task.mpu_mode = MPU_MODE_APP;

  __HAL_RCC_SAES_CLK_DISABLE();
  __HAL_RCC_SAES_FORCE_RESET();
  __HAL_RCC_SAES_RELEASE_RESET();
  __HAL_RCC_SAES_CLK_ENABLE();

  memcpy(output, unpriv_output, size);
  memzero(unpriv_input, SAES_DATA_SIZE_WITH_UNPRIV_KEY);
  memzero(unpriv_output, SAES_DATA_SIZE_WITH_UNPRIV_KEY);

#ifdef USE_TRUSTZONE
  tz_set_saes_unpriv(false);
  tz_set_tamper_unpriv(false);
#endif  // USE_TRUSTZONE

  return retval;
}
#endif  // KERNEL
