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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/optiga_hal.h>
#include <sys/systick.h>

void optiga_hal_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  OPTIGA_RST_CLK_EN();
  // init reset pin
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = OPTIGA_RST_PIN;
  HAL_GPIO_Init(OPTIGA_RST_PORT, &GPIO_InitStructure);

#ifdef OPTIGA_PWR_PIN
  OPTIGA_PWR_CLK_EN();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = OPTIGA_PWR_PIN;
  HAL_GPIO_Init(OPTIGA_PWR_PORT, &GPIO_InitStructure);
  HAL_GPIO_WritePin(OPTIGA_PWR_PORT, OPTIGA_PWR_PIN, GPIO_PIN_RESET);
  hal_delay(10);
#endif

  // perform reset on every initialization
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}

void optiga_hal_deinit(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = OPTIGA_RST_PIN;
  HAL_GPIO_Init(OPTIGA_RST_PORT, &GPIO_InitStructure);

#ifdef OPTIGA_PWR_PIN
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = OPTIGA_PWR_PIN;
  HAL_GPIO_Init(OPTIGA_PWR_PORT, &GPIO_InitStructure);
#endif
}

void optiga_reset(void) {
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_RESET);
  hal_delay(10);
  HAL_GPIO_WritePin(OPTIGA_RST_PORT, OPTIGA_RST_PIN, GPIO_PIN_SET);
  // warm reset startup time min 15ms
  hal_delay(20);
}

#endif  // SECURE_MODE
