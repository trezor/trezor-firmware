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

#pragma once

#include <gmock/gmock.h>

#include <trezor_bsp.h>

// gMock mock of the STM32 HAL GPIO driver declared in <trezor_bsp.h>.
//
// While an instance exists, the HAL_GPIO_* functions forward to it; calling
// them without one fails the test. By default the mock behaves like the
// output data register of the fake ports (GPIOA..GPIOH): WritePin, TogglePin
// and DeInit update it and ReadPin returns it. A test may either set
// expectations on the calls or just check the resulting level with
// PinState(). All ports start low.
class MockHalGpio {
 public:
  MockHalGpio();
  ~MockHalGpio();

  MockHalGpio(const MockHalGpio&) = delete;
  MockHalGpio& operator=(const MockHalGpio&) = delete;

  MOCK_METHOD(void, Init, (GPIO_TypeDef * port, const GPIO_InitTypeDef* init));
  MOCK_METHOD(void, DeInit, (GPIO_TypeDef * port, uint32_t pin));
  MOCK_METHOD(GPIO_PinState, ReadPin,
              (const GPIO_TypeDef* port, uint16_t pin));
  MOCK_METHOD(void, WritePin,
              (GPIO_TypeDef * port, uint16_t pin, GPIO_PinState state));
  MOCK_METHOD(void, TogglePin, (GPIO_TypeDef * port, uint16_t pin));

  // Output level of the pin, read without going through the mock
  static GPIO_PinState PinState(const GPIO_TypeDef* port, uint16_t pin);
};
