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

#include <sec/iwdg.h>

_Static_assert(LSI_VALUE == 250, "LSI_VALUE must be defined to 250 Hz");

void iwdg_start(uint32_t time_s) {
  if (time_s > IWDG_MAX_TIME) {
    // Limit the maximum watchdog timeout to 4 hours
    time_s = IWDG_MAX_TIME;
  }

  // Set the reload value based on the desired time in seconds
  uint32_t reload_value = ((time_s * LSI_VALUE) / 1024) - 1;

  IWDG_HandleTypeDef hiwdg = {0};

  hiwdg.Instance = IWDG;
  hiwdg.Init.Prescaler = IWDG_PRESCALER_1024;
  hiwdg.Init.Reload = reload_value;
  hiwdg.Init.Window = 0xFFF;
  hiwdg.Init.EWI = 0;

  // Configure the IWDG
  HAL_IWDG_Init(&hiwdg);
}

#endif
