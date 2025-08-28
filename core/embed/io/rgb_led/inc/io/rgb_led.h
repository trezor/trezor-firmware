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

#define RGB_EXTRACT_RED(color) (((color) >> 16) & 0xFF)
#define RGB_EXTRACT_GREEN(color) (((color) >> 8) & 0xFF)
#define RGB_EXTRACT_BLUE(color) ((color) & 0xFF)

#define RGB_COMPOSE_COLOR(red, green, blue) \
  (((red) & 0xFF) << 16 | ((green) & 0xFF) << 8 | ((blue) & 0xFF))

#define RGBLED_WHITE RGB_COMPOSE_COLOR(35, 35, 32)
#define RGBLED_GREEN RGB_COMPOSE_COLOR(0, 255, 0)
#define RGBLED_GREEN_LIGHT RGB_COMPOSE_COLOR(4, 13, 4)
#define RGBLED_GREEN_LIME RGB_COMPOSE_COLOR(35, 75, 10)
#define RGBLED_ORANGE RGB_COMPOSE_COLOR(188, 42, 6)
#define RGBLED_RED RGB_COMPOSE_COLOR(100, 6, 3)
#define RGBLED_YELLOW RGB_COMPOSE_COLOR(22, 16, 0)
#define RGBLED_BLUE RGB_COMPOSE_COLOR(5, 5, 50)
#define RGBLED_OFF 0x000000

/**
 * @brief RGB LED effect type
 */
typedef enum {
  RGB_LED_EFFECT_NONE = -1,
  RGB_LED_EFFECT_PAIRING = 0,
  RGB_LED_EFFECT_CHARGING,
  RGB_LED_NUM_OF_EFFECTS,
} rgb_led_effect_type_t;

#ifdef KERNEL_MODE

/**
 * @brief RGB LED wakeup parameters
 */
typedef struct {
  bool ongoing_effect;
  rgb_led_effect_type_t effect_type;
} rgb_led_wakeup_params_t;

/**
 * @brief Initialize RGB LED driver
 */
void rgb_led_init(void);

/**
 * @brief Deinitialize RGB LED driver
 */
void rgb_led_deinit(void);

/**
 * @brief set RGB LED wakeup parameters
 *
 * @param params: Pointer to the wakeup parameters structure
 */
void rgb_led_set_wakeup_params(rgb_led_wakeup_params_t *params);

/**
 * @brief Suspend RGB LED driver
 */
void rgb_led_suspend(void);

/**
 * @brief Resume RGB LED driver
 *
 * @param params: Pointer to the wakeup parameters structure
 */
void rgb_led_resume(const rgb_led_wakeup_params_t *params);

#endif  // KERNEL_MODE

/**
 * @brief Set RGB LED enabled state
 *
 * @param enabled: true to enable, false to disable
 */
void rgb_led_set_enabled(bool enabled);

/**
 * @brief Get RGB LED enabled state
 *
 * @return true if enabled, false otherwise
 */
bool rgb_led_get_enabled(void);

/**
 * @brief Set the RGB led color.
 *
 * Set the color of the RGB led, if there is ongoing RGB led effect, this
 * setting will stop the effect and override the color.
 *
 * @param color 24-bit RGB color, 0x00RRGGBB
 */
void rgb_led_set_color(uint32_t color);

/**
 * @brief Start an RGB led effect.
 *
 * @param effect_type The type of effect to start selected from
 *                    `rgb_led_effect_type_t` enum.
 *
 * @param requested_cycles The number of cycles to run the effect for, 0 will
 *                         run the effect indefinitely.
 */
void rgb_led_effect_start(rgb_led_effect_type_t effect_type,
                          uint32_t requested_cycles);

/**
 * @brief Stop the currently running RGB led effect and turn off the RGB led
 */
void rgb_led_effect_stop(void);

/**
 * @brief Get the ongoing RGB led effect state
 *
 * @return true if an effect is currently running, false otherwise
 */
bool rgb_led_effect_ongoing(void);

/**
 * @brief Get the ongoing RGB led effect type
 *
 * Get the ongoing RGB led effect type, return RGB_LED_EFFECT_NONE if no effect
 * is running.
 *
 * @return The type of the currently running RGB led effect
 */
rgb_led_effect_type_t rgb_led_effect_get_type(void);
