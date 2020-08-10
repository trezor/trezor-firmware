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
#include "touch.h"

#if TREZOR_MODEL == T
#include "touch_T.h"
#elif TREZOR_MODEL == 1
#include "touch_1.h"
#else
#error Unknown Trezor model
#endif

uint32_t touch_click(void) {
  uint32_t r = 0;
  // flush touch events if any
  while (touch_read()) {
  }
  // wait for TOUCH_START
  while ((touch_read() & TOUCH_START) == 0) {
  }
  // wait for TOUCH_END
  while (((r = touch_read()) & TOUCH_END) == 0) {
  }
  // flush touch events if any
  while (touch_read()) {
  }
  // return last touch coordinate
  return r;
}
