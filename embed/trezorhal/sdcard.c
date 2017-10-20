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

#include "sdcard.h"

static SD_HandleTypeDef sd_handle;

void sdcard_init(void) {
    // invalidate the sd_handle
    sd_handle.Instance = NULL;

    GPIO_InitTypeDef GPIO_InitStructure;

    // configure SD GPIO
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_PULLUP;
    GPIO_InitStructure.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = GPIO_AF12_SDIO;
    GPIO_InitStructure.Pin       = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
    GPIO_InitStructure.Pin       = GPIO_PIN_2;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

    // configure the SD card detect pin
    GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull = GPIO_PULLUP;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Pin = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
}

void HAL_SD_MspInit(SD_HandleTypeDef *hsd) {
    // enable SDIO clock
    __HAL_RCC_SDIO_CLK_ENABLE();
    // GPIO have already been initialised by sdcard_init
}

void HAL_SD_MspDeInit(SD_HandleTypeDef *hsd) {
    __HAL_RCC_SDIO_CLK_DISABLE();
}

bool sdcard_is_present(void) {
    return GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);
}

bool sdcard_power_on(void) {
    if (!sdcard_is_present()) {
        return false;
    }
    if (sd_handle.Instance) {
        return true;
    }

    // SD device interface configuration
    sd_handle.Instance = SDIO;
    sd_handle.Init.ClockEdge           = SDIO_CLOCK_EDGE_RISING;
    sd_handle.Init.ClockBypass         = SDIO_CLOCK_BYPASS_DISABLE;
    sd_handle.Init.ClockPowerSave      = SDIO_CLOCK_POWER_SAVE_ENABLE;
    sd_handle.Init.BusWide             = SDIO_BUS_WIDE_1B;
    sd_handle.Init.HardwareFlowControl = SDIO_HARDWARE_FLOW_CONTROL_DISABLE;
    sd_handle.Init.ClockDiv            = SDIO_TRANSFER_CLK_DIV;

    // init the SD interface, with retry if it's not ready yet
    for (int retry = 10; HAL_SD_Init(&sd_handle) != HAL_OK; retry--) {
        if (retry == 0) {
            goto error;
        }
        HAL_Delay(50);
    }

    // configure the SD bus width for wide operation
    if (HAL_SD_ConfigWideBusOperation(&sd_handle, SDIO_BUS_WIDE_4B) != HAL_OK) {
        HAL_SD_DeInit(&sd_handle);
        goto error;
    }

    return true;

error:
    sd_handle.Instance = NULL;
    return false;
}

bool sdcard_power_off(void) {
    if (!sd_handle.Instance) {
        return true;
    }
    HAL_SD_DeInit(&sd_handle);
    sd_handle.Instance = NULL;
    return true;
}

uint64_t sdcard_get_capacity_in_bytes(void) {
    if (sd_handle.Instance == NULL) {
        return 0;
    }
    HAL_SD_CardInfoTypeDef cardinfo;
    HAL_SD_GetCardInfo(&sd_handle, &cardinfo);
    return (uint64_t)cardinfo.LogBlockNbr * (uint64_t)cardinfo.LogBlockSize;
}

static HAL_StatusTypeDef sdcard_wait_finished(SD_HandleTypeDef *sd, uint32_t timeout) {
    // Wait for HAL driver to be ready (eg for DMA to finish)
    uint32_t start = HAL_GetTick();
    while (sd->State == HAL_SD_STATE_BUSY) {
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
        if (!(state == HAL_SD_CARD_SENDING || state == HAL_SD_CARD_RECEIVING || state == HAL_SD_CARD_PROGRAMMING)) {
            return HAL_ERROR;
        }
        if (HAL_GetTick() - start >= timeout) {
            return HAL_TIMEOUT;
        }
    }
    return HAL_OK;
}

bool sdcard_read_blocks(void *dest, uint32_t block_num, uint32_t num_blocks) {
    // check that SD card is initialised
    if (sd_handle.Instance == NULL) {
        return false;
    }

    // check that dest pointer is aligned on a 4-byte boundary
    if (((uint32_t)dest & 3) != 0) {
        return false;
    }

    HAL_StatusTypeDef err = HAL_OK;

    err = HAL_SD_ReadBlocks(&sd_handle, dest, block_num, num_blocks, 60000);
    if (err == HAL_OK) {
        err = sdcard_wait_finished(&sd_handle, 60000);
    }

    return err == HAL_OK;
}

bool sdcard_write_blocks(const void *src, uint32_t block_num, uint32_t num_blocks) {
    // check that SD card is initialised
    if (sd_handle.Instance == NULL) {
        return false;
    }

    // check that src pointer is aligned on a 4-byte boundary
    if (((uint32_t)src & 3) != 0) {
        return false;
    }

    HAL_StatusTypeDef err = HAL_OK;

    err = HAL_SD_WriteBlocks(&sd_handle, (uint8_t*)src, block_num, num_blocks, 60000);
    if (err == HAL_OK) {
        err = sdcard_wait_finished(&sd_handle, 60000);
    }

    return err == HAL_OK;
}
