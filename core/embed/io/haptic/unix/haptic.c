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

#include <io/haptic.h>

typedef struct {
  bool initialized;
  bool enabled;
} haptic_driver_t;

static haptic_driver_t g_haptic_driver = {
    .initialized = false,
};

ts_t __wur haptic_init(void) {
  haptic_driver_t *drv = &g_haptic_driver;

  if (drv->initialized) {
    return TS_OK;
  }

  memset(drv, 0, sizeof(*drv));
  drv->initialized = true;

  return TS_OK;
}

void haptic_deinit(void) {
  haptic_driver_t *drv = &g_haptic_driver;
  memset(drv, 0, sizeof(*drv));
}

ts_t haptic_set_enabled(bool enabled) {
  TSH_DECLARE;

  haptic_driver_t *drv = &g_haptic_driver;

  TSH_CHECK(drv->initialized, TS_ENOINIT);

  drv->enabled = enabled;

cleanup:
  TSH_RETURN;
}

bool haptic_get_enabled(void) {
  haptic_driver_t *drv = &g_haptic_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->enabled;
}

ts_t haptic_play(haptic_effect_t effect) {
  TSH_DECLARE;

  haptic_driver_t *drv = &g_haptic_driver;

  TSH_CHECK(drv->initialized, TS_ENOINIT);

cleanup:
  TSH_RETURN;
}

ts_t haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  TSH_DECLARE;

  haptic_driver_t *drv = &g_haptic_driver;

  TSH_CHECK(drv->initialized, TS_ENOINIT);

cleanup:
  TSH_RETURN;
}
