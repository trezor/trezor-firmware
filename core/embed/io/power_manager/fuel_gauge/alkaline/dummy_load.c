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

#ifdef KERNEL_MODE

#include <sys/systimer.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "dummy_load.h"

static void pulse_timer_timer_handler(void* context) { dummy_load_off(); }

ts_t dummy_load_init(systimer_t* pulse_timer) {
  pulse_timer = systimer_create(pulse_timer_timer_handler, NULL);
  if (pulse_timer == NULL) {
    return TS_ENOMEM;
  }

  CUR_DUMMY_EN_PIN_CLK_EN();

  HAL_GPIO_WritePin(CUR_DUMMY_EN_PORT, CUR_DUMMY_EN_PIN, GPIO_PIN_RESET);
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = CUR_DUMMY_EN_PIN;
  HAL_GPIO_Init(CUR_DUMMY_EN_PORT, &GPIO_InitStructure);

  return TS_OK;
}

void dummy_load_on(systimer_t* pulse_timer, uint32_t on_duration_ms) {
  HAL_GPIO_WritePin(CUR_DUMMY_EN_PORT, CUR_DUMMY_EN_PIN, GPIO_PIN_SET);
  if (on_duration_ms > 0) {
    systimer_set(pulse_timer, on_duration_ms);
  }
}

void dummy_load_off(void) {
  HAL_GPIO_WritePin(CUR_DUMMY_EN_PORT, CUR_DUMMY_EN_PIN, GPIO_PIN_RESET);
}

#endif  // KERNEL_MODE
