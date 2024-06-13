

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
  volatile uint32_t *ResetReg;
  uint32_t ResetBit;
} i2c_instance_t;

i2c_instance_t i2c_defs[I2C_COUNT] = {
    {
        .Instance = I2C_INSTANCE_0,
        .SclPort = I2C_INSTANCE_0_SCL_PORT,
        .SdaPort = I2C_INSTANCE_0_SDA_PORT,
        .SclPin = I2C_INSTANCE_0_SCL_PIN,
        .SdaPin = I2C_INSTANCE_0_SDA_PIN,
        .PinAF = I2C_INSTANCE_0_PIN_AF,
        .ResetReg = I2C_INSTANCE_0_RESET_REG,
        .ResetBit = I2C_INSTANCE_0_RESET_BIT,
    },
#ifdef I2C_INSTANCE_1
    {
        .Instance = I2C_INSTANCE_1,
        .SclPort = I2C_INSTANCE_1_SCL_PORT,
        .SdaPort = I2C_INSTANCE_1_SDA_PORT,
        .SclPin = I2C_INSTANCE_1_SCL_PIN,
        .SdaPin = I2C_INSTANCE_1_SDA_PIN,
        .PinAF = I2C_INSTANCE_1_PIN_AF,
        .ResetReg = I2C_INSTANCE_1_RESET_REG,
        .ResetBit = I2C_INSTANCE_1_RESET_BIT,
    },
#endif
#ifdef I2C_INSTANCE_2
    {
        .Instance = I2C_INSTANCE_2,
        .SclPort = I2C_INSTANCE_2_SCL_PORT,
        .SdaPort = I2C_INSTANCE_2_SDA_PORT,
        .SclPin = I2C_INSTANCE_2_SCL_PIN,
        .SdaPin = I2C_INSTANCE_2_SDA_PIN,
        .PinAF = I2C_INSTANCE_2_PIN_AF,
        .ResetReg = I2C_INSTANCE_2_RESET_REG,
        .ResetBit = I2C_INSTANCE_2_RESET_BIT,
    },
#endif

};

/*
 * Using calculation from STM32CubeMX
 * PCLKx as source, assumed 160MHz
 * Fast mode, freq = 400kHz, Rise time = 250ns, Fall time = 100ns
 * Fast mode, freq = 200kHz, Rise time = 250ns, Fall time = 100ns
 * SCLH and SCLL are manually modified to achieve more symmetric clock
 */
#define I2C_TIMING_400000_Hz 0x30D22728
#define I2C_TIMING_200000_Hz 0x30D2595A
#define I2C_TIMING I2C_TIMING_200000_Hz

void i2c_init_instance(uint16_t idx, i2c_instance_t *instance) {
  if (i2c_handle[idx].Instance) {
    return;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

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
  GPIO_InitStructure.Pin = instance->SdaPin;
  HAL_GPIO_Init(instance->SdaPort, &GPIO_InitStructure);

  i2c_handle[idx].Instance = instance->Instance;
  i2c_handle[idx].Init.Timing = I2C_TIMING;
  i2c_handle[idx].Init.OwnAddress1 = 0xFE;  // master
  i2c_handle[idx].Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  i2c_handle[idx].Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  i2c_handle[idx].Init.OwnAddress2 = 0;
  i2c_handle[idx].Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  i2c_handle[idx].Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_OK != HAL_I2C_Init(&i2c_handle[idx])) {
    error_shutdown("I2C was not loaded properly.");
    return;
  }
}

void i2c_init(void) {
  // enable I2C clock
  I2C_INSTANCE_0_CLK_EN();
  I2C_INSTANCE_0_SCL_CLK_EN();
  I2C_INSTANCE_0_SDA_CLK_EN();
  i2c_init_instance(0, &i2c_defs[0]);

#ifdef I2C_INSTANCE_1
  I2C_INSTANCE_1_CLK_EN();
  I2C_INSTANCE_1_SCL_CLK_EN();
  I2C_INSTANCE_1_SDA_CLK_EN();
  i2c_init_instance(1, &i2c_defs[1]);
#endif

#ifdef I2C_INSTANCE_2
  I2C_INSTANCE_2_CLK_EN();
  I2C_INSTANCE_2_SCL_CLK_EN();
  I2C_INSTANCE_2_SDA_CLK_EN();
  i2c_init_instance(2, &i2c_defs[2]);
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

void i2c_cycle(uint16_t idx) {
  SET_BIT(*i2c_defs[idx].ResetReg, i2c_defs[idx].ResetBit);
  CLEAR_BIT(*i2c_defs[idx].ResetReg, i2c_defs[idx].ResetBit);
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
