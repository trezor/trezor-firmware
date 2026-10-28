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

// Host replacement of <trezor_bsp.h> for the power manager unit tests.
//
// Declares the subset of the STM32 HAL GPIO driver and the board pin
// definitions used by the code under test. The HAL_GPIO_* functions are
// implemented by mock_hal_gpio.cc.

#pragma once

#include <trezor_types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  uint32_t ODR;  // Output data register
} GPIO_TypeDef;

typedef struct {
  uint32_t Pin;
  uint32_t Mode;
  uint32_t Pull;
  uint32_t Speed;
  uint32_t Alternate;
} GPIO_InitTypeDef;

typedef enum {
  GPIO_PIN_RESET = 0U,
  GPIO_PIN_SET,
} GPIO_PinState;

#define GPIO_PIN_0 ((uint16_t)0x0001)
#define GPIO_PIN_1 ((uint16_t)0x0002)
#define GPIO_PIN_2 ((uint16_t)0x0004)
#define GPIO_PIN_3 ((uint16_t)0x0008)
#define GPIO_PIN_4 ((uint16_t)0x0010)
#define GPIO_PIN_5 ((uint16_t)0x0020)
#define GPIO_PIN_6 ((uint16_t)0x0040)
#define GPIO_PIN_7 ((uint16_t)0x0080)
#define GPIO_PIN_8 ((uint16_t)0x0100)
#define GPIO_PIN_9 ((uint16_t)0x0200)
#define GPIO_PIN_10 ((uint16_t)0x0400)
#define GPIO_PIN_11 ((uint16_t)0x0800)
#define GPIO_PIN_12 ((uint16_t)0x1000)
#define GPIO_PIN_13 ((uint16_t)0x2000)
#define GPIO_PIN_14 ((uint16_t)0x4000)
#define GPIO_PIN_15 ((uint16_t)0x8000)

#define GPIO_MODE_INPUT 0x00000000U
#define GPIO_MODE_OUTPUT_PP 0x00000001U
#define GPIO_MODE_OUTPUT_OD 0x00000011U
#define GPIO_MODE_AF_PP 0x00000002U
#define GPIO_MODE_AF_OD 0x00000012U
#define GPIO_MODE_ANALOG 0x00000003U

#define GPIO_NOPULL 0x00000000U
#define GPIO_PULLUP 0x00000001U
#define GPIO_PULLDOWN 0x00000002U

#define GPIO_SPEED_FREQ_LOW 0x00000000U
#define GPIO_SPEED_FREQ_MEDIUM 0x00000001U
#define GPIO_SPEED_FREQ_HIGH 0x00000002U
#define GPIO_SPEED_FREQ_VERY_HIGH 0x00000003U

// Fake GPIO ports, defined in mock_hal_gpio.cc
#define MOCK_GPIO_PORT_COUNT 8
extern GPIO_TypeDef mock_gpio_ports[MOCK_GPIO_PORT_COUNT];

#define GPIOA (&mock_gpio_ports[0])
#define GPIOB (&mock_gpio_ports[1])
#define GPIOC (&mock_gpio_ports[2])
#define GPIOD (&mock_gpio_ports[3])
#define GPIOE (&mock_gpio_ports[4])
#define GPIOF (&mock_gpio_ports[5])
#define GPIOG (&mock_gpio_ports[6])
#define GPIOH (&mock_gpio_ports[7])

#define __HAL_RCC_GPIOA_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOB_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOC_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOD_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOE_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOF_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOG_CLK_ENABLE() \
  do {                               \
  } while (0)
#define __HAL_RCC_GPIOH_CLK_ENABLE() \
  do {                               \
  } while (0)

void HAL_GPIO_Init(GPIO_TypeDef* GPIOx, const GPIO_InitTypeDef* GPIO_Init);
void HAL_GPIO_DeInit(GPIO_TypeDef* GPIOx, uint32_t GPIO_Pin);
GPIO_PinState HAL_GPIO_ReadPin(const GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin,
                       GPIO_PinState PinState);
void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);

// Board pins, as in models/T3T2/boards/devkit.h
#define CUR_DUMMY_EN_PIN GPIO_PIN_5
#define CUR_DUMMY_EN_PORT GPIOA
#define CUR_DUMMY_EN_PIN_CLK_EN __HAL_RCC_GPIOA_CLK_ENABLE

#ifdef __cplusplus
}
#endif
