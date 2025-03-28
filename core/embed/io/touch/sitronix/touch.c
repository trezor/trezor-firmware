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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <io/touch.h>

#include "../touch_fsm.h"
#include "sitronix.h"

// Touch driver
typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // Last reported touch state
  uint32_t state;

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

secbool touch_init(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (sectrue == drv->initialized) {
    // The driver is already initialized
    return sectrue;
  }

  TS_Init_t TsInit;

  // Initialize the TouchScreen
  TsInit.Width = 480;
  TsInit.Height = 480;
  TsInit.Orientation = 0;
  TsInit.Accuracy = 2;

  if (0 != BSP_TS_Init(0, &TsInit)) {
    goto cleanup;
  }

  if (!touch_fsm_init()) {
    goto cleanup;
  }

  drv->initialized = sectrue;
  return sectrue;

cleanup:
  touch_deinit();
  return secfalse;
}

void touch_deinit(void) {
  touch_driver_t* drv = &g_touch_driver;

  BSP_TS_DeInit(0);
  touch_fsm_deinit();

  memset(drv, 0, sizeof(touch_driver_t));
}

void touch_power_set(bool on) {
  // Not implemented for the discovery kit
}

secbool touch_ready(void) {
  touch_driver_t* drv = &g_touch_driver;
  return drv->initialized;
}

secbool touch_set_sensitivity(uint8_t value) {
  // Not implemented for the discovery kit
  return sectrue;
}

uint8_t touch_get_version(void) {
  // Not implemented for the discovery kit
  return 0;
}

secbool touch_activity(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (sectrue != drv->initialized) {
    return secfalse;
  }

  TS_State_t new_state = {0};
  BSP_TS_GetState(0, &new_state);

  return sitronix_touching ? sectrue : secfalse;
}

uint32_t touch_get_state(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (sectrue != drv->initialized) {
    return 0;
  }

  TS_State_t ts = {0};
  BSP_TS_GetState(0, &ts);

  uint32_t state = drv->state;

  ts.TouchDetected = sitronix_touching ? 1 : 0;
  ts.TouchX = ts.TouchX > 120 ? ts.TouchX - 120 : 0;
  ts.TouchY = ts.TouchY > 120 ? ts.TouchY - 120 : 0;

  uint32_t xy = touch_pack_xy(ts.TouchX, ts.TouchY);

  if (ts.TouchDetected) {
    if ((drv->state & TOUCH_END) || (drv->state == 0)) {
      state = TOUCH_START | xy;
    } else if (drv->state & TOUCH_MOVE) {
      state = TOUCH_MOVE | xy;
    } else {
      state = TOUCH_START | xy;
      if (state != drv->state) {
        state = TOUCH_MOVE | xy;
      }
    }
  } else {
    if (drv->state & (TOUCH_START | TOUCH_MOVE)) {
      state = drv->state & ~(TOUCH_START | TOUCH_MOVE);
      state |= TOUCH_END;
    }
  }

  drv->state = state;
  return state;
}

#endif  // KERNEL_MODE
