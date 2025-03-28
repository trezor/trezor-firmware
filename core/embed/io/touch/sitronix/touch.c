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
#include <sys/sysevent_source.h>

#include "../touch_fsm.h"
#include "sitronix.h"

// Touch driver
typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // Last reported touch state
  uint32_t state;
  // Touch state machine for each task
  touch_fsm_t tls[SYSTASK_MAX_TASKS];

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

// Forward declarations
static const syshandle_vmt_t g_touch_handle_vmt;

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

  if (!syshandle_register(SYSHANDLE_TOUCH, &g_touch_handle_vmt, drv)) {
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
  syshandle_unregister(SYSHANDLE_TOUCH);

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

static uint32_t touch_get_state(touch_driver_t* drv) {
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

uint32_t touch_get_event(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (sectrue != drv->initialized) {
    return 0;
  }

  touch_fsm_t* fsm = &drv->tls[systask_id(systask_active())];

  uint32_t touch_state = touch_get_state(drv);

  uint32_t event = touch_fsm_get_event(fsm, touch_state);

  return event;
}

static void on_task_created(void* context, systask_id_t task_id) {
  touch_driver_t* drv = (touch_driver_t*)context;
  touch_fsm_t* fsm = &drv->tls[task_id];
  touch_fsm_init(fsm);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  touch_driver_t* drv = (touch_driver_t*)context;

  UNUSED(write_awaited);

  if (read_awaited) {
    uint32_t touch_state = touch_get_state(drv);
    if (touch_state != 0) {
      syshandle_signal_read_ready(SYSHANDLE_TOUCH, &touch_state);
    }
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  touch_driver_t* drv = (touch_driver_t*)context;
  touch_fsm_t* fsm = &drv->tls[task_id];

  uint32_t touch_state = *(uint32_t*)param;

  return touch_fsm_event_ready(fsm, touch_state);
}

static const syshandle_vmt_t g_touch_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
