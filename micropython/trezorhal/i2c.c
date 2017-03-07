#include STM32_HAL_H

I2C_HandleTypeDef i2c_handle;

void __fatal_error(const char *msg);

void i2c_init(void) {

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
        __fatal_error("i2c_init failed");
        return;
    }

    // Enable IRQs
    HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);
    HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);
}
