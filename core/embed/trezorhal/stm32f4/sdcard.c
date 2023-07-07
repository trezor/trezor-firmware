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
 * This file is part of the Micro Python project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013, 2014 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include STM32_HAL_H

#include <string.h>

#include "dma.h"
#include "irq.h"
#include "sdcard-set_clr_card_detect.h"
#include "sdcard.h"
#include "supervise.h"

#define SDMMC_CLK_ENABLE() __HAL_RCC_SDMMC1_CLK_ENABLE()
#define SDMMC_CLK_DISABLE() __HAL_RCC_SDMMC1_CLK_DISABLE()
#define SDMMC_IRQn SDMMC1_IRQn
#define SDMMC_DMA dma_SDIO_0

static SD_HandleTypeDef sd_handle;

static inline void sdcard_default_pin_state(void) {
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_SET);     // SD_ON/PC0
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_8, GPIO_PIN_RESET);   // SD_DAT0/PC8
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_9, GPIO_PIN_RESET);   // SD_DAT1/PC9
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_10, GPIO_PIN_RESET);  // SD_DAT2/PC10
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_11, GPIO_PIN_RESET);  // SD_DAT3/PC11
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, GPIO_PIN_RESET);  // SD_CLK/PC12
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_2, GPIO_PIN_RESET);   // SD_CMD/PD2

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure the SD card circuitry on/off pin
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_0;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

  // configure SD GPIO
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin =
      GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_2;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

  // configure the SD card detect pin
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_13;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
}

static inline void sdcard_active_pin_state(void) {
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_RESET);  // SD_ON/PC0
  HAL_Delay(10);  // we need to wait until the circuit fully kicks-in

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure SD GPIO
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF12_SDIO;
  GPIO_InitStructure.Pin =
      GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_2;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
}

void sdcard_init(void) { sdcard_default_pin_state(); }

void HAL_SD_MspInit(SD_HandleTypeDef *hsd) {
  if (hsd->Instance == sd_handle.Instance) {
    // enable SDIO clock
    SDMMC_CLK_ENABLE();

    // NVIC configuration for SDIO interrupts
    svc_setpriority(SDMMC_IRQn, IRQ_PRI_SDIO);
    svc_enableIRQ(SDMMC_IRQn);
  }

  // GPIO have already been initialised by sdcard_init
}

void HAL_SD_MspDeInit(SD_HandleTypeDef *hsd) {
  if (hsd->Instance == sd_handle.Instance) {
    svc_disableIRQ(SDMMC_IRQn);
    SDMMC_CLK_DISABLE();
  }
}

secbool sdcard_power_on(void) {
  if (sectrue != sdcard_is_present()) {
    return secfalse;
  }
  if (sd_handle.Instance) {
    return sectrue;
  }
  // turn on SD card circuitry
  sdcard_active_pin_state();
  HAL_Delay(50);

  // SD device interface configuration
  sd_handle.Instance = SDIO;
  sd_handle.Init.ClockEdge = SDIO_CLOCK_EDGE_RISING;
  sd_handle.Init.ClockBypass = SDIO_CLOCK_BYPASS_DISABLE;
  sd_handle.Init.ClockPowerSave = SDIO_CLOCK_POWER_SAVE_ENABLE;
  sd_handle.Init.BusWide = SDIO_BUS_WIDE_1B;
  sd_handle.Init.HardwareFlowControl = SDIO_HARDWARE_FLOW_CONTROL_DISABLE;
  sd_handle.Init.ClockDiv = SDIO_TRANSFER_CLK_DIV;

  // init the SD interface, with retry if it's not ready yet
  for (int retry = 10; HAL_SD_Init(&sd_handle) != HAL_OK; retry--) {
    if (retry == 0) {
      goto error;
    }
    HAL_Delay(50);
  }

  // disable the card's internal CD/DAT3 card detect pull-up resistor
  // to send ACMD42, we have to send CMD55 (APP_CMD) with with the card's RCA as
  // the argument followed by CMD42 (SET_CLR_CARD_DETECT)
  if (SDMMC_CmdAppCommand(sd_handle.Instance, sd_handle.SdCard.RelCardAdd
                                                  << 16U) != SDMMC_ERROR_NONE) {
    goto error;
  }
  if (SDMMC_CmdSetClrCardDetect(sd_handle.Instance, 0) != SDMMC_ERROR_NONE) {
    goto error;
  }

  // configure the SD bus width for wide operation
  if (HAL_SD_ConfigWideBusOperation(&sd_handle, SDIO_BUS_WIDE_4B) != HAL_OK) {
    HAL_SD_DeInit(&sd_handle);
    goto error;
  }

  return sectrue;

error:
  sdcard_power_off();
  return secfalse;
}

void sdcard_power_off(void) {
  if (sd_handle.Instance) {
    HAL_SD_DeInit(&sd_handle);
    sd_handle.Instance = NULL;
  }
  // turn off SD card circuitry
  HAL_Delay(50);
  sdcard_default_pin_state();
  HAL_Delay(100);
}

secbool sdcard_is_present(void) {
  return sectrue * (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13));
}

uint64_t sdcard_get_capacity_in_bytes(void) {
  if (sd_handle.Instance == NULL) {
    return 0;
  }
  HAL_SD_CardInfoTypeDef cardinfo;
  HAL_SD_GetCardInfo(&sd_handle, &cardinfo);
  return (uint64_t)cardinfo.LogBlockNbr * (uint64_t)cardinfo.LogBlockSize;
}

void SDIO_IRQHandler(void) {
  IRQ_ENTER(SDIO_IRQn);
  if (sd_handle.Instance) {
    HAL_SD_IRQHandler(&sd_handle);
  }
  IRQ_EXIT(SDIO_IRQn);
}

static void sdcard_reset_periph(void) {
  // Fully reset the SDMMC peripheral before calling HAL SD DMA functions.
  // (There could be an outstanding DTIMEOUT event from a previous call and the
  // HAL function enables IRQs before fully configuring the SDMMC peripheral.)
  SDIO->DTIMER = 0;
  SDIO->DLEN = 0;
  SDIO->DCTRL = 0;
  SDIO->ICR = SDMMC_STATIC_FLAGS;
}

static HAL_StatusTypeDef sdcard_wait_finished(SD_HandleTypeDef *sd,
                                              uint32_t timeout) {
  // Wait for HAL driver to be ready (eg for DMA to finish)
  uint32_t start = HAL_GetTick();
  for (;;) {
    // Do an atomic check of the state; WFI will exit even if IRQs are disabled
    uint32_t irq_state = disable_irq();
    if (sd->State != HAL_SD_STATE_BUSY) {
      enable_irq(irq_state);
      break;
    }
    __WFI();
    enable_irq(irq_state);
    if (HAL_GetTick() - start >= timeout) {
      return HAL_TIMEOUT;
    }
  }

  // Wait for SD card to complete the operation
  for (;;) {
    HAL_SD_CardStateTypeDef state = HAL_SD_GetCardState(sd);
    if (state == HAL_SD_CARD_TRANSFER) {
      return HAL_OK;
    }
    if (!(state == HAL_SD_CARD_SENDING || state == HAL_SD_CARD_RECEIVING ||
          state == HAL_SD_CARD_PROGRAMMING)) {
      return HAL_ERROR;
    }
    if (HAL_GetTick() - start >= timeout) {
      return HAL_TIMEOUT;
    }
    __WFI();
  }
  return HAL_OK;
}

secbool sdcard_read_blocks(uint32_t *dest, uint32_t block_num,
                           uint32_t num_blocks) {
  // check that SD card is initialised
  if (sd_handle.Instance == NULL) {
    return secfalse;
  }

  // check that dest pointer is aligned on a 4-byte boundary
  if (((uint32_t)dest & 3) != 0) {
    return secfalse;
  }

  HAL_StatusTypeDef err = HAL_OK;

  // we must disable USB irqs to prevent MSC contention with SD card
  uint32_t basepri = raise_irq_pri(IRQ_PRI_OTG_FS);

  DMA_HandleTypeDef sd_dma;
  dma_init(&sd_dma, &SDMMC_DMA, DMA_PERIPH_TO_MEMORY, &sd_handle);
  sd_handle.hdmarx = &sd_dma;

  // we need to assign hdmatx even though it's unused
  // because STMHAL tries to access its error code in SD_DMAError()
  // even though it shouldn't :-/
  // this will get removed eventually when we update to new STMHAL
  DMA_HandleTypeDef dummy_dma;
  memset(&dummy_dma, 0, sizeof(dummy_dma));
  sd_handle.hdmatx = &dummy_dma;

  sdcard_reset_periph();
  err =
      HAL_SD_ReadBlocks_DMA(&sd_handle, (uint8_t *)dest, block_num, num_blocks);
  if (err == HAL_OK) {
    err = sdcard_wait_finished(&sd_handle, 5000);
  }

  dma_deinit(&SDMMC_DMA);
  sd_handle.hdmarx = NULL;

  restore_irq_pri(basepri);

  return sectrue * (err == HAL_OK);
}

secbool sdcard_write_blocks(const uint32_t *src, uint32_t block_num,
                            uint32_t num_blocks) {
  // check that SD card is initialised
  if (sd_handle.Instance == NULL) {
    return secfalse;
  }

  // check that src pointer is aligned on a 4-byte boundary
  if (((uint32_t)src & 3) != 0) {
    return secfalse;
  }

  HAL_StatusTypeDef err = HAL_OK;

  // we must disable USB irqs to prevent MSC contention with SD card
  uint32_t basepri = raise_irq_pri(IRQ_PRI_OTG_FS);

  DMA_HandleTypeDef sd_dma;
  dma_init(&sd_dma, &SDMMC_DMA, DMA_MEMORY_TO_PERIPH, &sd_handle);
  sd_handle.hdmatx = &sd_dma;

  // we need to assign hdmarx even though it's unused
  // because HAL tries to access its error code in SD_DMAError()
  // even though it shouldn't :-/
  // this will get removed eventually when we update to new STMHAL
  DMA_HandleTypeDef dummy_dma;
  memset(&dummy_dma, 0, sizeof(dummy_dma));
  sd_handle.hdmarx = &dummy_dma;

  sdcard_reset_periph();
  err =
      HAL_SD_WriteBlocks_DMA(&sd_handle, (uint8_t *)src, block_num, num_blocks);
  if (err == HAL_OK) {
    err = sdcard_wait_finished(&sd_handle, 5000);
  }

  dma_deinit(&SDMMC_DMA);
  sd_handle.hdmatx = NULL;

  restore_irq_pri(basepri);

  return sectrue * (err == HAL_OK);
}
