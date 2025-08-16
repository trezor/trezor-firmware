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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/haptic.h>
#include <io/unix/sdl_display.h>

#ifdef KERNEL_MODE

// Driver state
typedef struct {
  bool initialized;
  bool enabled;
} haptic_driver_t;

// Haptic driver instance
static haptic_driver_t g_haptic_driver = {
    .initialized = true,
    .enabled = false,
};

bool haptic_init(void) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (driver->initialized) {
    return true;
  }

  memset(driver, 0, sizeof(haptic_driver_t));

  driver->initialized = true;
  driver->enabled = true;

  return true;
}

void haptic_deinit(void) {
  haptic_driver_t *driver = &g_haptic_driver;
  memset(driver, 0, sizeof(haptic_driver_t));
}

void haptic_set_enabled(bool enabled) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return;
  }

  driver->enabled = enabled;
}

bool haptic_get_enabled(void) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  return driver->enabled;
}

bool haptic_test(uint16_t duration_ms) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  if (!driver->enabled) {
    return true;
  }

  // display_effect(0xff, duration_ms);
  return true;
}

bool haptic_play(haptic_effect_t effect) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  if (!driver->enabled) {
    return true;
  }

  switch (effect) {
    case HAPTIC_BUTTON_PRESS:
      display_haptic_effect(HAPTIC_BUTTON_PRESS);
      return true;
    case HAPTIC_HOLD_TO_CONFIRM:
      display_haptic_effect(HAPTIC_HOLD_TO_CONFIRM);
      return true;
    case HAPTIC_BOOTLOADER_ENTRY:
      display_haptic_effect(HAPTIC_BOOTLOADER_ENTRY);
      return true;
    default:
      return false;
  }
}

bool haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  if (!driver->enabled) {
    return true;
  }

  display_custom_effect(duration_ms);
  return true;
}

#endif  // KERNEL_MODE
