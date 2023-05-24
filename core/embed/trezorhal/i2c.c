

#include STM32_HAL_H
#include TREZOR_BOARD
#include "i2c.h"
#include "common.h"

static I2C_HandleTypeDef i2c_handle;

void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c) {
  // enable I2C clock
  I2C_INSTANCE_CLK_EN();
  I2C_INSTANCE_SCL_CLK_EN();
  I2C_INSTANCE_SDA_CLK_EN();
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef *hi2c) {
  // disable I2C clock
  I2C_INSTANCE_CLK_DIS();
}

void i2c_init(void) {
  if (i2c_handle.Instance) {
    return;
  }

  HAL_I2C_MspInit(&i2c_handle);

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure CTP I2C SCL and SDA GPIO lines
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed =
      GPIO_SPEED_FREQ_LOW;  // I2C is a KHz bus and low speed is still good into
  // the low MHz

  GPIO_InitStructure.Alternate = I2C_INSTANCE_PIN_AF;
  GPIO_InitStructure.Pin = I2C_INSTANCE_SCL_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SCL_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Alternate = I2C_INSTANCE_PIN_AF;
  GPIO_InitStructure.Pin = I2C_INSTANCE_SDA_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SDA_PORT, &GPIO_InitStructure);

  i2c_handle.Instance = I2C_INSTANCE;
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

void _i2c_ensure_pin(GPIO_TypeDef *port, uint16_t GPIO_Pin,
                     GPIO_PinState PinState) {
  HAL_GPIO_WritePin(port, GPIO_Pin, PinState);
  while (HAL_GPIO_ReadPin(port, GPIO_Pin) != PinState)
    ;
}

// I2C cycle described in section 2.9.7 of STM CD00288116 Errata sheet
//
// https://www.st.com/content/ccc/resource/technical/document/errata_sheet/7f/05/b0/bc/34/2f/4c/21/CD00288116.pdf/files/CD00288116.pdf/jcr:content/translations/en.CD00288116.pdf

void i2c_cycle(void) {
  // 1. Disable I2C peripheral
  _i2c_deinit();

  // 2. Configure SCL/SDA as GPIO OUTPUT Open Drain
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = I2C_INSTANCE_SDA_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SDA_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = I2C_INSTANCE_SCL_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SCL_PORT, &GPIO_InitStructure);
  HAL_Delay(50);

  // 3. Check SCL and SDA High level
  _i2c_ensure_pin(I2C_INSTANCE_SCL_PORT, I2C_INSTANCE_SCL_PIN, GPIO_PIN_SET);
  _i2c_ensure_pin(I2C_INSTANCE_SDA_PORT, I2C_INSTANCE_SDA_PIN, GPIO_PIN_SET);
  // 4+5. Check SDA Low level
  _i2c_ensure_pin(I2C_INSTANCE_SDA_PORT, I2C_INSTANCE_SDA_PIN, GPIO_PIN_RESET);
  // 6+7. Check SCL Low level
  _i2c_ensure_pin(I2C_INSTANCE_SCL_PORT, I2C_INSTANCE_SCL_PIN, GPIO_PIN_RESET);
  // 8+9. Check SCL High level
  _i2c_ensure_pin(I2C_INSTANCE_SCL_PORT, I2C_INSTANCE_SCL_PIN, GPIO_PIN_SET);
  // 10+11.  Check SDA High level
  _i2c_ensure_pin(I2C_INSTANCE_SDA_PORT, I2C_INSTANCE_SDA_PIN, GPIO_PIN_SET);

  // 12. Configure SCL/SDA as Alternate function Open-Drain
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = I2C_INSTANCE_PIN_AF;
  GPIO_InitStructure.Pin = I2C_INSTANCE_SCL_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SCL_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = I2C_INSTANCE_SDA_PIN;
  HAL_GPIO_Init(I2C_INSTANCE_SDA_PORT, &GPIO_InitStructure);
  HAL_Delay(50);

  // 13. Set SWRST bit in I2Cx_CR1 register
  I2C_INSTANCE_FORCE_RESET();
  HAL_Delay(50);

  // 14. Clear SWRST bit in I2Cx_CR1 register
  I2C_INSTANCE_RELEASE_RESET();

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

HAL_StatusTypeDef i2c_mem_write(uint8_t addr, uint16_t mem_addr,
                                uint16_t mem_addr_size, uint8_t *data,
                                uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Write(&i2c_handle, addr, mem_addr, mem_addr_size, data,
                           len, timeout);
}
HAL_StatusTypeDef i2c_mem_read(uint8_t addr, uint16_t mem_addr,
                               uint16_t mem_addr_size, uint8_t *data,
                               uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Read(&i2c_handle, addr, mem_addr, mem_addr_size, data, len,
                          timeout);
}
