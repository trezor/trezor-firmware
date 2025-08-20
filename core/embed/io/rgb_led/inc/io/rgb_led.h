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

#include <trezor_types.h>

#ifdef KERNEL_MODE

#define RGB_EXTRACT_RED(color) (((color) >> 16) & 0xFF)
#define RGB_EXTRACT_GREEN(color) (((color) >> 8) & 0xFF)
#define RGB_EXTRACT_BLUE(color) ((color) & 0xFF)

#define RGB_COMPOSE_COLOR(red, green, blue) \
  (((red) & 0xFF) << 16 | ((green) & 0xFF) << 8 | ((blue) & 0xFF))

typedef enum {
  RGB_LED_STATUS_OK = 0,
  RGB_LED_NOT_INITIALIZED,
  RGB_LED_INVALID_ARGUMENT,
} rgb_led_status_t;

typedef enum {
  RGB_LED_EFFECT_BOOTLOADER_BREATHE = 0,
  RGB_LED_EFFECT_CHARGING,
  RGB_LED_NUM_OF_EFFECTS,
} rgb_led_effect_type_t;

// Initialize RGB LED driver
void rgb_led_init(void);

// Deinitialize RGB LED driver
void rgb_led_deinit(void);

#endif  // KERNEL_MODE

// Set RGB LED enabled state
// enabled: true to enable, false to disable
void rgb_led_set_enabled(bool enabled);

// Get RGB LED enabled state
bool rgb_led_get_enabled(void);

#define RGBLED_WHITE RGB_COMPOSE_COLOR(35, 35, 32)
#define RGBLED_GREEN RGB_COMPOSE_COLOR(0, 255, 0)
#define RGBLED_GREEN_LIGHT RGB_COMPOSE_COLOR(4, 13, 4)
#define RGBLED_GREEN_LIME RGB_COMPOSE_COLOR(35, 75, 10)
#define RGBLED_ORANGE RGB_COMPOSE_COLOR(188, 42, 6)
#define RGBLED_RED RGB_COMPOSE_COLOR(100, 6, 3)
#define RGBLED_YELLOW RGB_COMPOSE_COLOR(22, 16, 0)
#define RGBLED_BLUE RGB_COMPOSE_COLOR(0, 0, 50)
#define RGBLED_OFF 0x000000

// Set RGB LED color
// color: 24-bit RGB color, 0x00RRGGBB
void rgb_led_set_color(uint32_t color);

void rgb_led_effect_start(rgb_led_effect_type_t effect_type,
                          uint32_t requested_cycles);

void rgb_led_effect_stop(void);
