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

#ifndef TREZORHAL_RGB_LED_H
#define TREZORHAL_RGB_LED_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

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

// Set RGB LED color
// color: 24-bit RGB color, 0x00RRGGBB
void rgb_led_set_color(uint32_t color);

#define RGBLED_GREEN 0x040D04
#define RGBLED_RED 0x640603
#define RGBLED_BLUE 0x050532
#define RGBLED_YELLOW 0x161000

#endif  // TREZORHAL_RGB_LED_H
