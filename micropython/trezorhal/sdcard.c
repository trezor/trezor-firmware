#include STM32_HAL_H

#include <string.h>

#include "sdcard.h"

#define IRQ_PRI_SDIO            4
#define IRQ_SUBPRI_SDIO         0

static SD_HandleTypeDef sd_handle;

int sdcard_init(void) {
    // invalidate the sd_handle
    sd_handle.Instance = NULL;

    GPIO_InitTypeDef GPIO_InitStructure;

    // configure SD GPIO
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_PULLUP;
    GPIO_InitStructure.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStructure.Alternate = GPIO_AF12_SDIO;
    GPIO_InitStructure.Pin       = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
    GPIO_InitStructure.Pin       = GPIO_PIN_2;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

    // configure the SD card detect pin
    GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull = GPIO_PULLUP;
    GPIO_InitStructure.Speed = GPIO_SPEED_HIGH;
    GPIO_InitStructure.Pin = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

    return 0;
}

void HAL_SD_MspInit(SD_HandleTypeDef *hsd) {
    // enable SDIO clock
    __SDIO_CLK_ENABLE();

    // NVIC configuration for SDIO interrupts
    HAL_NVIC_SetPriority(SDIO_IRQn, IRQ_PRI_SDIO, IRQ_SUBPRI_SDIO);
    HAL_NVIC_EnableIRQ(SDIO_IRQn);

    // GPIO have already been initialised by sdcard_init
}

void HAL_SD_MspDeInit(SD_HandleTypeDef *hsd) {
    HAL_NVIC_DisableIRQ(SDIO_IRQn);
    __SDIO_CLK_DISABLE();
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
    HAL_SD_CardInfoTypedef cardinfo;
    for (int retry = 10; HAL_SD_Init(&sd_handle, &cardinfo) != SD_OK; retry--) {
        if (retry == 0) {
            goto error;
        }
        HAL_Delay(50);
    }

    // configure the SD bus width for wide operation
    if (HAL_SD_WideBusOperation_Config(&sd_handle, SDIO_BUS_WIDE_4B) != SD_OK) {
        HAL_SD_DeInit(&sd_handle);
        goto error;
    }

    return true;

error:
    sd_handle.Instance = NULL;
    return false;
}

void sdcard_power_off(void) {
    if (!sd_handle.Instance) {
        return;
    }
    HAL_SD_DeInit(&sd_handle);
    sd_handle.Instance = NULL;
}

uint64_t sdcard_get_capacity_in_bytes(void) {
    if (sd_handle.Instance == NULL) {
        return 0;
    }
    HAL_SD_CardInfoTypedef cardinfo;
    HAL_SD_Get_CardInfo(&sd_handle, &cardinfo);
    return cardinfo.CardCapacity;
}

void SDIO_IRQHandler(void) {
    HAL_SD_IRQHandler(&sd_handle);
}

uint32_t sdcard_read_blocks(uint8_t *dest, uint32_t block_num, uint32_t num_blocks) {
    // check that SD card is initialised
    if (sd_handle.Instance == NULL) {
        return SD_ERROR;
    }

    HAL_SD_ErrorTypedef err = SD_OK;

    // check that dest pointer is aligned on a 4-byte boundary
    if (((uint32_t)dest & 3) != 0) {
        return SD_ERROR;
    }

    err = HAL_SD_ReadBlocks_BlockNumber(&sd_handle, (uint32_t*)dest, block_num, SDCARD_BLOCK_SIZE, num_blocks);

    return err;
}
