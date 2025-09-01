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

#include <trezor_rtl.h>

#include <io/rgb_led.h>
#include <io/unix/sdl_display.h>

#ifdef KERNEL_MODE

// Driver state
typedef struct {
  bool initialized;
  bool enabled;
} rgb_led_driver_t;

// RGB LED driver instance
static rgb_led_driver_t g_rgb_led_driver = {
    .initialized = true,
    .enabled = false,
};

void rgb_led_init(void) {
  rgb_led_driver_t *driver = &g_rgb_led_driver;

  // turn the LED off
  rgb_led_set_color(0);

  driver->initialized = true;
  driver->enabled = true;
}

void rgb_led_deinit(void) {
  rgb_led_driver_t *driver = &g_rgb_led_driver;

  // turn the LED off
  rgb_led_set_color(0);

  memset(driver, 0, sizeof(rgb_led_driver_t));
}

void rgb_led_set_enabled(bool enabled) {
  rgb_led_driver_t *driver = &g_rgb_led_driver;

  if (!driver->initialized) {
    return;
  }

  // If the RGB LED is to be disabled, turn off the LED
  if (!enabled) {
    rgb_led_set_color(0);
  }

  driver->enabled = enabled;
}

bool rgb_led_get_enabled(void) {
  rgb_led_driver_t *driver = &g_rgb_led_driver;

  if (!driver->initialized) {
    return false;
  }

  return driver->enabled;
}

void rgb_led_set_color(uint32_t color) {
  rgb_led_driver_t *driver = &g_rgb_led_driver;
  if (!driver->initialized || !driver->enabled) {
    return;
  }

  display_rgb_led(color);
}

void rgb_led_effect_start(rgb_led_effect_type_t effect_type,
                          uint32_t requested_cycles) {
  // RGB effect not supported in unix yet
  return;
}

void rgb_led_effect_stop(void) {
  // RGB effect not supported in unix yet
  return;
}

bool rgb_led_get_effect_ongoing(void) {
  // RGB effect not supported in unix yet
  return false;
}

#endif /* KERNEL_MODE */
