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

#include <sys/systick.h>
#include <trezor_rtl.h>

#include "rgb_led_internal.h"

// Effects constants
#define EFFECT_BOOTLOADER_BREATHE_UP_MS 2000
#define EFFECT_BOOTLOADER_BREATHE_DOWN_MS 800
#define EFFECT_BOOTLOADER_BREATHE_CYCLE_MS \
  (EFFECT_BOOTLOADER_BREATHE_UP_MS + EFFECT_BOOTLOADER_BREATHE_DOWN_MS)

#define EFFECT_CHARGING_UP_MS 200
#define EFFECT_CHARGING_DOWN_MS 500
#define EFFECT_CHARGING_CYCLE_MS \
  (EFFECT_CHARGING_UP_MS + EFFECT_CHARGING_DOWN_MS)

// Effect callback function prototypes
static uint32_t rgb_led_effect_bootloader_breathe(uint32_t elapsed_ms);
static uint32_t rgb_led_effect_charging(uint32_t elapsed_ms);

static uint32_t (*rgb_led_effects_callbacks[])(uint32_t elapsed_ms) = {
    [RGB_LED_EFFECT_BOOTLOADER_BREATHE] = rgb_led_effect_bootloader_breathe,
    [RGB_LED_EFFECT_CHARGING] = rgb_led_effect_charging,
};

static inline uint32_t linear_interpolate(uint32_t y0, uint32_t y1, uint32_t x,
                                          uint32_t x1) {
  int32_t diff = (int32_t)y1 - (int32_t)y0;
  return (uint32_t)(y0 + (diff * (int32_t)x / (int32_t)x1));
}

static uint32_t rgb_led_linear_effect(uint32_t c_start, uint32_t c_end,
                                      uint32_t elapsed_ms, uint32_t total_ms) {
  if (elapsed_ms >= total_ms) {
    return c_end;
  }

  uint32_t start_r = RGB_EXTRACT_RED(c_start);
  uint32_t start_g = RGB_EXTRACT_GREEN(c_start);
  uint32_t start_b = RGB_EXTRACT_BLUE(c_start);

  uint32_t end_r = RGB_EXTRACT_RED(c_end);
  uint32_t end_g = RGB_EXTRACT_GREEN(c_end);
  uint32_t end_b = RGB_EXTRACT_BLUE(c_end);

  uint32_t r = linear_interpolate(start_r, end_r, elapsed_ms, total_ms);
  uint32_t g = linear_interpolate(start_g, end_g, elapsed_ms, total_ms);
  uint32_t b = linear_interpolate(start_b, end_b, elapsed_ms, total_ms);

  return RGB_COMPOSE_COLOR(r, g, b);
}

bool rgb_led_assign_effect(rgb_led_effect_t *effect,
                           rgb_led_effect_type_t effect_type) {
  if (effect_type < 0 || effect_type >= RGB_LED_NUM_OF_EFFECTS) {
    return false;
  }

  // Clear effect structure
  memset(effect, 0, sizeof(rgb_led_effect_t));

  effect->type = effect_type;
  effect->callback = rgb_led_effects_callbacks[effect_type];

  return true;
}

static uint32_t rgb_led_effect_bootloader_breathe(uint32_t elapsed_ms) {
  uint32_t effect_time = elapsed_ms % EFFECT_BOOTLOADER_BREATHE_CYCLE_MS;

  if (effect_time < EFFECT_BOOTLOADER_BREATHE_UP_MS) {
    return rgb_led_linear_effect(RGBLED_OFF, RGBLED_BLUE, effect_time,
                                 EFFECT_BOOTLOADER_BREATHE_UP_MS);
  } else if (effect_time < EFFECT_BOOTLOADER_BREATHE_CYCLE_MS) {
    return rgb_led_linear_effect(RGBLED_BLUE, RGBLED_OFF,
                                 effect_time - EFFECT_BOOTLOADER_BREATHE_UP_MS,
                                 EFFECT_BOOTLOADER_BREATHE_DOWN_MS);
  } else {
    // Should not happen
    return RGBLED_OFF;
  }
}

static uint32_t rgb_led_effect_charging(uint32_t elapsed_ms) {
  uint32_t effect_time = elapsed_ms % EFFECT_CHARGING_CYCLE_MS;

  if (effect_time < EFFECT_CHARGING_UP_MS) {
    return rgb_led_linear_effect(RGBLED_OFF, RGBLED_YELLOW, effect_time,
                                 EFFECT_CHARGING_UP_MS);
  } else if (effect_time < EFFECT_CHARGING_CYCLE_MS) {
    return rgb_led_linear_effect(RGBLED_YELLOW, RGBLED_OFF,
                                 effect_time - EFFECT_CHARGING_UP_MS,
                                 EFFECT_CHARGING_DOWN_MS);
  } else {
    // Should not happen
    return RGBLED_OFF;
  }
}
