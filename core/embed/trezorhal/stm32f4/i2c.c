

#include STM32_HAL_H
#include TREZOR_BOARD
#include "i2c.h"
#include "common.h"

static I2C_HandleTypeDef i2c_handle[I2C_COUNT];

typedef struct {
  I2C_TypeDef *Instance;
  GPIO_TypeDef *SclPort;
  GPIO_TypeDef *SdaPort;
  uint16_t SclPin;
  uint16_t SdaPin;
  uint8_t PinAF;
  uint32_t Reset;
} i2c_instance_t;

i2c_instance_t i2c_defs[I2C_COUNT] = {
    {
        .Instance = I2C_INSTANCE_1,
        .SclPort = I2C_INSTANCE_1_SCL_PORT,
        .SdaPort = I2C_INSTANCE_1_SDA_PORT,
        .SclPin = I2C_INSTANCE_1_SCL_PIN,
        .SdaPin = I2C_INSTANCE_1_SDA_PIN,
        .PinAF = I2C_INSTANCE_1_PIN_AF,
        .Reset = I2C_INSTANCE_1_RESET_FLG,
    },
#ifdef I2C_INSTANCE_2
    {
        .Instance = I2C_INSTANCE_2,
        .SclPort = I2C_INSTANCE_2_SCL_PORT,
        .SdaPort = I2C_INSTANCE_2_SDA_PORT,
        .SclPin = I2C_INSTANCE_2_SCL_PIN,
        .SdaPin = I2C_INSTANCE_2_SDA_PIN,
        .PinAF = I2C_INSTANCE_2_PIN_AF,
        .Reset = I2C_INSTANCE_2_RESET_FLG,
    },
#endif

};

void i2c_init_instance(uint16_t idx, i2c_instance_t *instance) {
  if (i2c_handle[idx].Instance) {
    return;
  }

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure CTP I2C SCL and SDA GPIO lines
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed =
      GPIO_SPEED_FREQ_LOW;  // I2C is a KHz bus and low speed is still good into
  // the low MHz

  GPIO_InitStructure.Alternate = instance->PinAF;
  GPIO_InitStructure.Pin = instance->SclPin;
  HAL_GPIO_Init(instance->SclPort, &GPIO_InitStructure);

  GPIO_InitStructure.Alternate = instance->PinAF;
  ;
  GPIO_InitStructure.Pin = instance->SdaPin;
  HAL_GPIO_Init(instance->SdaPort, &GPIO_InitStructure);

  i2c_handle[idx].Instance = instance->Instance;
  i2c_handle[idx].Init.ClockSpeed = 200000;
  i2c_handle[idx].Init.DutyCycle = I2C_DUTYCYCLE_16_9;
  i2c_handle[idx].Init.OwnAddress1 = 0xFE;  // master
  i2c_handle[idx].Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  i2c_handle[idx].Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  i2c_handle[idx].Init.OwnAddress2 = 0;
  i2c_handle[idx].Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  i2c_handle[idx].Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_OK != HAL_I2C_Init(&i2c_handle[idx])) {
    ensure(secfalse, "I2C was not loaded properly.");
    return;
  }
}

void i2c_init(void) {
  // enable I2C clock
  I2C_INSTANCE_1_CLK_EN();
  I2C_INSTANCE_1_SCL_CLK_EN();
  I2C_INSTANCE_1_SDA_CLK_EN();

  i2c_init_instance(0, &i2c_defs[0]);

#ifdef I2C_INSTANCE_2
  I2C_INSTANCE_2_CLK_EN();
  I2C_INSTANCE_2_SCL_CLK_EN();
  I2C_INSTANCE_2_SDA_CLK_EN();
  i2c_init_instance(1, &i2c_defs[1]);
#endif
}

void i2c_deinit(uint16_t idx) {
  if (i2c_handle[idx].Instance) {
    HAL_I2C_DeInit(&i2c_handle[idx]);
    i2c_handle[idx].Instance = NULL;
  }
}

void i2c_ensure_pin(GPIO_TypeDef *port, uint16_t GPIO_Pin,
                    GPIO_PinState PinState) {
  HAL_GPIO_WritePin(port, GPIO_Pin, PinState);
  while (HAL_GPIO_ReadPin(port, GPIO_Pin) != PinState)
    ;
}

// I2C cycle described in section 2.9.7 of STM CD00288116 Errata sheet
//
// https://www.st.com/content/ccc/resource/technical/document/errata_sheet/7f/05/b0/bc/34/2f/4c/21/CD00288116.pdf/files/CD00288116.pdf/jcr:content/translations/en.CD00288116.pdf

void i2c_cycle(uint16_t idx) {
  i2c_instance_t *instance = &i2c_defs[0];

  // 1. Disable I2C peripheral
  i2c_deinit(idx);

  // 2. Configure SCL/SDA as GPIO OUTPUT Open Drain
  GPIO_InitTypeDef GPIO_InitStructure;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = instance->SdaPin;
  HAL_GPIO_Init(instance->SdaPort, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = instance->SclPin;
  HAL_GPIO_Init(instance->SclPort, &GPIO_InitStructure);
  HAL_Delay(50);

  // 3. Check SCL and SDA High level
  i2c_ensure_pin(instance->SclPort, instance->SclPin, GPIO_PIN_SET);
  i2c_ensure_pin(instance->SdaPort, instance->SdaPin, GPIO_PIN_SET);
  // 4+5. Check SDA Low level
  i2c_ensure_pin(instance->SdaPort, instance->SdaPin, GPIO_PIN_RESET);
  // 6+7. Check SCL Low level
  i2c_ensure_pin(instance->SclPort, instance->SclPin, GPIO_PIN_RESET);
  // 8+9. Check SCL High level
  i2c_ensure_pin(instance->SclPort, instance->SclPin, GPIO_PIN_SET);
  // 10+11.  Check SDA High level
  i2c_ensure_pin(instance->SclPort, instance->SdaPin, GPIO_PIN_SET);

  // 12. Configure SCL/SDA as Alternate function Open-Drain
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = instance->PinAF;
  GPIO_InitStructure.Pin = instance->SclPin;
  HAL_GPIO_Init(instance->SclPort, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = instance->SdaPin;
  HAL_GPIO_Init(instance->SdaPort, &GPIO_InitStructure);
  HAL_Delay(50);

  // 13. Force reset
  RCC->APB1RSTR |= instance->Reset;

  HAL_Delay(50);

  // 14. Release reset
  RCC->APB1RSTR &= ~instance->Reset;

  // 15. Enable the I2C peripheral
  i2c_init_instance(idx, instance);
  HAL_Delay(10);
}

HAL_StatusTypeDef i2c_transmit(uint16_t idx, uint8_t addr, uint8_t *data,
                               uint16_t len, uint32_t timeout) {
  return HAL_I2C_Master_Transmit(&i2c_handle[idx], addr, data, len, timeout);
}

HAL_StatusTypeDef i2c_receive(uint16_t idx, uint8_t addr, uint8_t *data,
                              uint16_t len, uint32_t timeout) {
  HAL_StatusTypeDef ret =
      HAL_I2C_Master_Receive(&i2c_handle[idx], addr, data, len, timeout);
#ifdef USE_OPTIGA
  if (idx == OPTIGA_I2C_INSTANCE) {
    // apply GUARD_TIME as specified by the OPTIGA datasheet
    // (only applies to the I2C bus to which the OPTIGA is connected)
    hal_delay_us(50);
  }
#endif
  return ret;
}

HAL_StatusTypeDef i2c_mem_write(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                                uint16_t mem_addr_size, uint8_t *data,
                                uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Write(&i2c_handle[idx], addr, mem_addr, mem_addr_size,
                           data, len, timeout);
}
HAL_StatusTypeDef i2c_mem_read(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                               uint16_t mem_addr_size, uint8_t *data,
                               uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Read(&i2c_handle[idx], addr, mem_addr, mem_addr_size, data,
                          len, timeout);
}
