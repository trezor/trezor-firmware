/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "secbool.h"
#include "touch.h"

static I2C_HandleTypeDef i2c_handle;

void touch_init(void)
{
    // Enable I2C clock
    __HAL_RCC_I2C1_CLK_ENABLE();

    // Init SCL and SDA GPIO lines (PB6 & PB7)
    GPIO_InitTypeDef GPIO_InitStructure = {
        .Pin = GPIO_PIN_6 | GPIO_PIN_7,
        .Mode = GPIO_MODE_AF_OD,
        .Pull = GPIO_NOPULL,
        .Speed = GPIO_SPEED_FREQ_VERY_HIGH,
        .Alternate = GPIO_AF4_I2C1,
    };
    HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

    i2c_handle.Instance = I2C1;
    i2c_handle.Init.ClockSpeed = 400000;
    i2c_handle.Init.DutyCycle = I2C_DUTYCYCLE_16_9;
    i2c_handle.Init.OwnAddress1 = 0xFE; // master
    i2c_handle.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    i2c_handle.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    i2c_handle.Init.OwnAddress2 = 0;
    i2c_handle.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    i2c_handle.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

    ensure(sectrue * (HAL_OK == HAL_I2C_Init(&i2c_handle)), NULL);
}

#define TOUCH_ADDRESS 56
#define TOUCH_PACKET_SIZE 16

uint32_t touch_read(void)
{
    static uint8_t data[TOUCH_PACKET_SIZE], old_data[TOUCH_PACKET_SIZE];
    if (HAL_OK != HAL_I2C_Master_Receive(&i2c_handle, TOUCH_ADDRESS << 1, data, TOUCH_PACKET_SIZE, 1)) {
        return 0; // read failure
    }
    if (0 == memcmp(data, old_data, TOUCH_PACKET_SIZE)) {
        return 0; // no new event
    }
    memcpy(old_data, data, TOUCH_PACKET_SIZE);

    if (data[0] == 0xff && data[1] == 0x00) {
        if (data[2] == 0x01 && data[3] == 0x00) {
            return TOUCH_START | ((data[3] & 0xF) << 20) | (data[4] << 12) | ((data[5] & 0xF) << 8) | data[6];
        } else
        if (data[2] == 0x01 && data[3] == 0x80) {
            return TOUCH_MOVE  | ((data[3] & 0xF) << 20) | (data[4] << 12) | ((data[5] & 0xF) << 8) | data[6];
        } else
        if (data[2] == 0x00 && data[3] == 0x40) {
            return TOUCH_END   | ((data[3] & 0xF) << 20) | (data[4] << 12) | ((data[5] & 0xF) << 8) | data[6];
        }
    }

    return 0;
}

uint32_t touch_click(void)
{
    uint32_t r;
    // flush touch events if any
    while (touch_read()) { }
    // wait for TOUCH_START
    while ((touch_read() & TOUCH_START) == 0) { }
    // wait for TOUCH_END
    while (((r = touch_read()) & TOUCH_END) == 0) { }
    // flush touch events if any
    while (touch_read()) { }
    // return last touch coordinate
    return r;
}
