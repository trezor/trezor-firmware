

#include STM32_HAL_H
#include "i2c.h"
#include "common.h"

static I2C_HandleTypeDef i2c_handle;

void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c) {
  // enable I2C clock
  __HAL_RCC_I2C1_CLK_ENABLE();
  // GPIO have already been initialised by touch_init
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef *hi2c) {
  __HAL_RCC_I2C1_CLK_DISABLE();
}

void i2c_init(void) {
  if (i2c_handle.Instance) {
    return;
  }

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure CTP I2C SCL and SDA GPIO lines (PB6 & PB7)
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed =
      GPIO_SPEED_FREQ_LOW;  // I2C is a KHz bus and low speed is still good into
  // the low MHz
  GPIO_InitStructure.Alternate = GPIO_AF4_I2C1;
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  i2c_handle.Instance = I2C1;
  i2c_handle.Init.ClockSpeed = 200000;
  i2c_handle.Init.DutyCycle = I2C_DUTYCYCLE_16_9;
  i2c_handle.Init.OwnAddress1 = 0xFE;  // master
  i2c_handle.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  i2c_handle.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  i2c_handle.Init.OwnAddress2 = 0;
  i2c_handle.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  i2c_handle.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_OK != HAL_I2C_Init(&i2c_handle)) {
    ensure(secfalse, "I2C was not loaded properly.");
    return;
  }
}

void _i2c_deinit(void) {
  if (i2c_handle.Instance) {
    HAL_I2C_DeInit(&i2c_handle);
    i2c_handle.Instance = NULL;
  }
}

void _i2c_ensure_pin(uint16_t GPIO_Pin, GPIO_PinState PinState) {
  HAL_GPIO_WritePin(GPIOB, GPIO_Pin, PinState);
  while (HAL_GPIO_ReadPin(GPIOB, GPIO_Pin) != PinState)
    ;
}

// I2C cycle described in section 2.9.7 of STM CD00288116 Errata sheet
//
// https://www.st.com/content/ccc/resource/technical/document/errata_sheet/7f/05/b0/bc/34/2f/4c/21/CD00288116.pdf/files/CD00288116.pdf/jcr:content/translations/en.CD00288116.pdf

void i2c_cycle(void) {
  // PIN6 is SCL, PIN7 is SDA

  // 1. Disable I2C peripheral
  _i2c_deinit();

  // 2. Configure SCL/SDA as GPIO OUTPUT Open Drain
  GPIO_InitTypeDef GPIO_InitStructure;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  HAL_Delay(50);

  // 3. Check SCL and SDA High level
  _i2c_ensure_pin(GPIO_PIN_6, GPIO_PIN_SET);
  _i2c_ensure_pin(GPIO_PIN_7, GPIO_PIN_SET);
  // 4+5. Check SDA Low level
  _i2c_ensure_pin(GPIO_PIN_7, GPIO_PIN_RESET);
  // 6+7. Check SCL Low level
  _i2c_ensure_pin(GPIO_PIN_6, GPIO_PIN_RESET);
  // 8+9. Check SCL High level
  _i2c_ensure_pin(GPIO_PIN_6, GPIO_PIN_SET);
  // 10+11.  Check SDA High level
  _i2c_ensure_pin(GPIO_PIN_7, GPIO_PIN_SET);

  // 12. Configure SCL/SDA as Alternate function Open-Drain
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = GPIO_AF4_I2C1;
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  HAL_Delay(50);

  // 13. Set SWRST bit in I2Cx_CR1 register
  __HAL_RCC_I2C1_FORCE_RESET();
  HAL_Delay(50);

  // 14. Clear SWRST bit in I2Cx_CR1 register
  __HAL_RCC_I2C1_RELEASE_RESET();

  // 15. Enable the I2C peripheral
  i2c_init();
  HAL_Delay(10);
}

HAL_StatusTypeDef i2c_transmit(uint8_t addr, uint8_t *data, uint16_t len,
                               uint32_t timeout) {
  return HAL_I2C_Master_Transmit(&i2c_handle, addr, data, len, timeout);
}
HAL_StatusTypeDef i2c_receive(uint8_t addr, uint8_t *data, uint16_t len,
                              uint32_t timeout) {
  return HAL_I2C_Master_Receive(&i2c_handle, addr, data, len, timeout);
}
