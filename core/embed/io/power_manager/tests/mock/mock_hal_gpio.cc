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

#include "mock_hal_gpio.h"

#include <cstring>

using ::testing::_;

GPIO_TypeDef mock_gpio_ports[MOCK_GPIO_PORT_COUNT];

static MockHalGpio* g_mock_hal_gpio = nullptr;

MockHalGpio::MockHalGpio() {
  EXPECT_EQ(g_mock_hal_gpio, nullptr) << "Only one MockHalGpio may exist";
  g_mock_hal_gpio = this;

  memset(mock_gpio_ports, 0, sizeof(mock_gpio_ports));

  ON_CALL(*this, DeInit(_, _))
      .WillByDefault([](GPIO_TypeDef* port, uint32_t pin) {
        port->ODR &= ~pin;
      });
  ON_CALL(*this, ReadPin(_, _)).WillByDefault(&MockHalGpio::PinState);
  ON_CALL(*this, WritePin(_, _, _))
      .WillByDefault(
          [](GPIO_TypeDef* port, uint16_t pin, GPIO_PinState state) {
            if (state == GPIO_PIN_RESET) {
              port->ODR &= ~(uint32_t)pin;
            } else {
              port->ODR |= pin;
            }
          });
  ON_CALL(*this, TogglePin(_, _))
      .WillByDefault([](GPIO_TypeDef* port, uint16_t pin) { port->ODR ^= pin; });
}

MockHalGpio::~MockHalGpio() { g_mock_hal_gpio = nullptr; }

GPIO_PinState MockHalGpio::PinState(const GPIO_TypeDef* port, uint16_t pin) {
  return (port->ODR & pin) != 0 ? GPIO_PIN_SET : GPIO_PIN_RESET;
}

static MockHalGpio* active_mock(const char* fn) {
  if (g_mock_hal_gpio == nullptr) {
    ADD_FAILURE() << fn << "() called without a MockHalGpio instance";
  }
  return g_mock_hal_gpio;
}

extern "C" {

void HAL_GPIO_Init(GPIO_TypeDef* GPIOx, const GPIO_InitTypeDef* GPIO_Init) {
  if (MockHalGpio* mock = active_mock(__func__)) {
    mock->Init(GPIOx, GPIO_Init);
  }
}

void HAL_GPIO_DeInit(GPIO_TypeDef* GPIOx, uint32_t GPIO_Pin) {
  if (MockHalGpio* mock = active_mock(__func__)) {
    mock->DeInit(GPIOx, GPIO_Pin);
  }
}

GPIO_PinState HAL_GPIO_ReadPin(const GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin) {
  if (MockHalGpio* mock = active_mock(__func__)) {
    return mock->ReadPin(GPIOx, GPIO_Pin);
  }
  return GPIO_PIN_RESET;
}

void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin,
                       GPIO_PinState PinState) {
  if (MockHalGpio* mock = active_mock(__func__)) {
    mock->WritePin(GPIOx, GPIO_Pin, PinState);
  }
}

void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin) {
  if (MockHalGpio* mock = active_mock(__func__)) {
    mock->TogglePin(GPIOx, GPIO_Pin);
  }
}

}  // extern "C"
