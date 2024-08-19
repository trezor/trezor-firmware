/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include STM32_HAL_H
#include TREZOR_BOARD

#include "i2c_new.h"
#include "irq.h"

typedef struct {
  I2C_TypeDef* Instance;
  GPIO_TypeDef* SclPort;
  GPIO_TypeDef* SdaPort;
  uint16_t SclPin;
  uint16_t SdaPin;
  uint8_t PinAF;
  volatile uint32_t* ResetReg;
  uint32_t ResetBit;
} i2c_bus_def_t;

// I2C bus hardware definitions
static const i2c_bus_def_t g_i2c_bus_def[I2C_COUNT] = {
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

struct i2c_bus {
  // Number of references to the bus
  // (0 means the bus is not initialized)
  int refcount;

  // STM32 HAL I2C handle
  I2C_HandleTypeDef handle;

  // Head of the packet queue
  // (this packet is currently being processed)
  i2c_packet_t* head;
  // Tail of the packet queue
  // (this packet is the last in the queue)
  i2c_packet_t* tail;
};

// I2C bus driver instances
static i2c_bus_t g_i2c_bus_driver[I2C_COUNT] = {0};

// Using calculation from STM32CubeMX
// PCLKx as source, assumed 160MHz
// Fast mode, freq = 400kHz, Rise time = 250ns, Fall time = 100ns
// Fast mode, freq = 200kHz, Rise time = 250ns, Fall time = 100ns
// SCLH and SCLL are manually modified to achieve more symmetric clock
#define I2C_TIMING_400000_Hz 0x30D22728
#define I2C_TIMING_200000_Hz 0x30D2595A
#define I2C_TIMING I2C_TIMING_200000_Hz

static bool i2c_bus_init(i2c_bus_t* bus, int bus_index) {
  switch (bus_index) {
    case 0:
      // enable I2C clock
      I2C_INSTANCE_0_CLK_EN();
      I2C_INSTANCE_0_SCL_CLK_EN();
      I2C_INSTANCE_0_SDA_CLK_EN();
      break;

#ifdef I2C_INSTANCE_1
    case 1:
      I2C_INSTANCE_1_CLK_EN();
      I2C_INSTANCE_1_SCL_CLK_EN();
      I2C_INSTANCE_1_SDA_CLK_EN();
      break;
#endif

#ifdef I2C_INSTANCE_2
    case 2:
      I2C_INSTANCE_2_CLK_EN();
      I2C_INSTANCE_2_SCL_CLK_EN();
      I2C_INSTANCE_2_SDA_CLK_EN();
      break;
#endif
    default:
      return false;
  }

  const i2c_bus_def_t* def = &g_i2c_bus_def[bus_index];

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // configure CTP I2C SCL and SDA GPIO lines
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed =
      GPIO_SPEED_FREQ_LOW;  // I2C is a KHz bus and low speed is still good into
  // the low MHz

  GPIO_InitStructure.Alternate = def->PinAF;
  GPIO_InitStructure.Pin = def->SclPin;
  HAL_GPIO_Init(def->SclPort, &GPIO_InitStructure);

  GPIO_InitStructure.Alternate = def->PinAF;
  GPIO_InitStructure.Pin = def->SdaPin;
  HAL_GPIO_Init(def->SdaPort, &GPIO_InitStructure);

  I2C_HandleTypeDef* handle = &bus->handle;

  handle->Instance = def->Instance;
  handle->Init.Timing = I2C_TIMING;
  handle->Init.OwnAddress1 = 0xFE;  // master
  handle->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  handle->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  handle->Init.OwnAddress2 = 0;
  handle->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  handle->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  return (HAL_OK == HAL_I2C_Init(handle));
}

static void i2c_bus_deinit(i2c_bus_t* bus) {
  HAL_I2C_DeInit(&bus->handle);
  bus->handle.Instance = NULL;
}

i2c_bus_t* i2c_bus_acquire(uint8_t bus_index) {
  if (bus_index >= I2C_COUNT) {
    return NULL;
  }

  i2c_bus_t* bus = &g_i2c_bus_driver[bus_index];

  if (bus->refcount == 0) {
    if (!i2c_bus_init(bus, bus_index)) {
      return NULL;
    }
  }

  ++bus->refcount;

  return bus;
}

void i2c_bus_release(i2c_bus_t* bus) {
  if (bus->refcount > 0) {
    if (--bus->refcount == 0) {
      i2c_bus_deinit(bus);
    }
  }
}

i2c_status_t i2c_packet_status(i2c_packet_t* packet) {
  uint32_t irq_state = disable_irq();
  i2c_status_t status = packet->status;
  enable_irq(irq_state);
  return status;
}

i2c_status_t i2c_packet_wait(i2c_packet_t* packet) {
  while (true) {
    i2c_status_t status = i2c_packet_status(packet);

    if (status != I2C_STATUS_PENDING) {
      return status;
    }

    // Enter sleep mode and wait for any interrupt
    __WFI();
  }
}

i2c_status_t i2c_packet_submit(i2c_bus_t* bus, i2c_packet_t* packet) {
  if (bus->refcount > 0) {
    // Bus in not initialized
    return I2C_STATUS_ERROR;
  }

  if (packet->next != NULL) {
    // Packet is already in the queue
    return I2C_STATUS_ERROR;
  }

  packet->status = I2C_STATUS_PENDING;

  uint32_t irq_state = disable_irq();

  // Insert packet into the queue
  if (bus->tail == NULL) {
    bus->head = packet;
    bus->tail = packet;
    enable_irq(irq_state);

    // !@# i2c_bus_start_packet(bus, packet);

  } else {
    bus->tail->next = packet;
    enable_irq(irq_state);
  }

  return I2C_STATUS_OK;
}
