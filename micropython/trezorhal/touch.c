#include STM32_HAL_H

#include <string.h>

I2C_HandleTypeDef i2c_handle = {
    .Instance = I2C1,
};

int touch_init(void) {

    // Enable I2C clock
    __HAL_RCC_I2C1_CLK_ENABLE();

    __I2C1_CLK_ENABLE();

    // Init SCL and SDA GPIO lines (PB6 & PB7)
    GPIO_InitTypeDef GPIO_InitStructure = {
        .Pin = GPIO_PIN_6 | GPIO_PIN_7,
        .Mode = GPIO_MODE_AF_OD,
        .Pull = GPIO_NOPULL,
        .Speed = GPIO_SPEED_FREQ_VERY_HIGH,
        .Alternate = GPIO_AF4_I2C1,
    };
    HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

    I2C_InitTypeDef *init = &(i2c_handle.Init);
    init->OwnAddress1 = 0xFE; // master
    init->ClockSpeed = 400000;
    init->DutyCycle = I2C_DUTYCYCLE_16_9;
    init->AddressingMode  = I2C_ADDRESSINGMODE_7BIT;
    init->DualAddressMode = I2C_DUALADDRESS_DISABLED;
    init->GeneralCallMode = I2C_GENERALCALL_DISABLED;
    init->NoStretchMode   = I2C_NOSTRETCH_DISABLED;
    init->OwnAddress2     = 0;

    // Init I2C handle
    if (HAL_I2C_Init(&i2c_handle) != HAL_OK) {
        return 1;
    }

    // Enable IRQs
    HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);
    HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);

    return 0;
}

uint32_t touch_read(void) {
    static uint8_t data[16], old_data[16];
    if (HAL_OK != HAL_I2C_Master_Receive(&i2c_handle, 56 << 1, data, 16, 1)) {
        return 0; // read failure
    }
    if (0 == memcmp(data, old_data, 16)) {
        return 0; // no new event
    }
    uint32_t r = 0;
    if (old_data[2] == 0 && data[2] == 1) {
        r = 0x00010000 + (data[4] << 8) + data[6]; // touch start
    } else
    if (old_data[2] == 1 && data[2] == 1) {
        r = 0x00020000 + (data[4] << 8) + data[6]; // touch move
    }
    if (old_data[2] == 1 && data[2] == 0) {
        r = 0x00040000 + (data[4] << 8) + data[6]; // touch end
    }
    memcpy(old_data, data, 16);
    return r;
}

void I2C1_EV_IRQHandler(void) {
    HAL_I2C_EV_IRQHandler(&i2c_handle);
}

void I2C1_ER_IRQHandler(void) {
    HAL_I2C_ER_IRQHandler(&i2c_handle);
}
