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

#ifdef KERNEL_MODE

#include <io/touch.h>

#include "../touch_fsm.h"
#include "stmpe811.h"

typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // I2C Bus driver
  i2c_bus_t* i2c_bus;
  // Last reported touch state
  uint32_t state;

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

secbool touch_init(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (drv->initialized == sectrue) {
    return sectrue;
  }

  memset(drv, 0, sizeof(drv));

  drv->i2c_bus = i2c_bus_open(TOUCH_I2C_INSTANCE);

  if (drv->i2c_bus == NULL) {
    goto cleanup;
  }

  if (!touch_fsm_init()) {
    goto cleanup;
  }

  stmpe811_Reset(drv->i2c_bus);
  touch_set_mode();

  drv->initialized = sectrue;
  return sectrue;

cleanup:
  touch_deinit();
  return secfalse;
}

void touch_deinit(void) {
  touch_driver_t* drv = &g_touch_driver;

  touch_fsm_deinit();
  i2c_bus_close(drv->i2c_bus);
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
  return touch_active() ? sectrue : secfalse;
  /*    uint8_t state = ((IOE_Read(TS_I2C_ADDRESS, STMPE811_REG_TSC_CTRL) &
                        (uint8_t)STMPE811_TS_CTRL_STATUS) == (uint8_t)0x80);
      return state > 0 ? sectrue : secfalse;*/
}

uint32_t touch_get_state(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (sectrue != drv->initialized) {
    return 0;
  }

  TS_StateTypeDef ts = {0};
  BSP_TS_GetState(&ts);

  uint32_t state = drv->state;

  uint32_t xy = touch_pack_xy(ts.X, ts.Y);

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
