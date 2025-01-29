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

#include <io/backlight.h>

#include <trezor_bsp.h>
#include <trezor_rtl.h>

typedef struct {
  // Set if driver is initialized
  bool initialized;
  // Current backlight level in range 0-255
  int current_level;

} backlight_driver_t;

static backlight_driver_t g_backlight_driver = {
    .initialized = false,
};

static void backlight_on(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Pin = BACKLIGHT_PIN_PIN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(BACKLIGHT_PIN_PORT, &GPIO_InitStructure);
}

static void backlight_off(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Pin = BACKLIGHT_PIN_PIN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(BACKLIGHT_PIN_PORT, &GPIO_InitStructure);
}

void backlight_init(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (drv->initialized) {
    return;
  }

  BACKLIGHT_PIN_CLK_ENABLE();

  if (action == BACKLIGHT_RESET) {
    backlight_off();
  };

  drv->initialized = true;
}

void backlight_deinit(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;
  if (!drv->initialized) {
    return;
  }

  if (action == BACKLIGHT_RESET) {
    backlight_off();
  }
}

int backlight_set(int val) {
  backlight_driver_t *drv = &g_backlight_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (val > 0) {
    backlight_on();
  } else {
    backlight_off();
  }
  drv->current_level = val;
  return val;
}

int backlight_get(void) {
  backlight_driver_t *drv = &g_backlight_driver;
  if (!drv->initialized) {
    return 0;
  }
  return drv->current_level;
}
