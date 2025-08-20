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

#include <trezor_bsp.h>
#include <trezor_types.h>

#include <io/rgb_led.h>
#include <sys/systimer.h>

typedef struct {
  uint32_t cycles;
  uint32_t requested_cycles;
} rgb_led_effect_data_t;

typedef struct {
  rgb_led_effect_type_t type;
  uint32_t start_time_ms;
  rgb_led_effect_data_t data;
  uint32_t (*callback)(uint32_t elapsed_ms, rgb_led_effect_data_t *data);
} rgb_led_effect_t;

typedef struct {
  LPTIM_HandleTypeDef tim_1;
  LPTIM_HandleTypeDef tim_3;
  bool initialized;
  bool enabled;

  bool ongoing_effect;
  systimer_t *effect_timer;
  rgb_led_effect_t effect;
} rgb_led_t;

/**
 * @brief Assign effect a callback function according to the effect_type,
 *
 * @param effect pointer to the effect handler
 * @param effect_type the type of effect to assign
 * @return true on success, false on failure
 */
bool rgb_led_assign_effect(rgb_led_effect_t *effect,
                           rgb_led_effect_type_t effect_type);
