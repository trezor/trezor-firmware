#include STM32_HAL_H

I2C_HandleTypeDef *i2c_handle = 0;

void __fatal_error(const char *msg);

void i2c_init(I2C_HandleTypeDef *i2c) {

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

    // Init I2C handle
    if (HAL_I2C_Init(i2c) != HAL_OK) {
        __fatal_error("i2c_init failed");
        return;
    }

    // Enable IRQs
    i2c_handle = i2c;
    HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);
    HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);
}
