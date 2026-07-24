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

#include <io/nfc.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>

#include "nfc_poll.h"
#include "nfc_poll_internal.h"
#include "rfal_nfc.h"

typedef struct {
  bool last_state;       // connection state already reported to this task
  uint8_t connected;     // unreported connect edge
  uint8_t disconnected;  // unreported disconnect edge
} nfc_fsm_t;

//!< Card connection status flag
static bool nfc_card_connected = false;

//!< Active card details
static nfc_dev_info_t nfc_card_info;

//!< State machine for each task
static nfc_fsm_t g_nfc_tls[SYSTASK_MAX_TASKS] = {0};

//!< Forward declarations
static const syshandle_vmt_t g_nfc_handle_vmt;

bool nfc_poll_init(void) {
  nfc_card_connected = false;
  return syshandle_register(SYSHANDLE_NFC, &g_nfc_handle_vmt, NULL);
}

void nfc_poll_deinit(void) {
  nfc_card_connected = false;
  syshandle_unregister(SYSHANDLE_NFC);
}

bool nfc_get_event(nfc_event_t* event) {
  assert(event != NULL);
  nfc_fsm_t* fsm = &g_nfc_tls[systask_id(systask_active())];

  if (fsm->connected && fsm->disconnected) {
    fsm->connected = 0;
    fsm->disconnected = 0;
    fsm->last_state = false;
  } else if (fsm->connected) {
    fsm->connected = 0;
    fsm->last_state = true;
    *event = NFC_EVENT_CONNECTED;
    return true;
  } else if (fsm->disconnected) {
    fsm->disconnected = 0;
    fsm->last_state = false;
    *event = NFC_EVENT_DISCONNECTED;
    return true;
  }
  *event = NFC_NO_EVENT;
  return false;
}

bool nfc_get_state(void) { return nfc_card_connected; }

ts_t nfc_get_device_info(nfc_dev_info_t* dev_info) {
  if (nfc_card_connected) {
    memcpy(dev_info, &nfc_card_info, sizeof(nfc_dev_info_t));
    return TS_OK;
  } else {
    memset(dev_info, 0, sizeof(nfc_dev_info_t));
    return TS_ENOSTATE;
  }
}

static void on_task_created(void* context, systask_id_t task_id) {
  nfc_fsm_t* fsm = &g_nfc_tls[task_id];
  memset(fsm, 0, sizeof(nfc_fsm_t));
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(write_awaited);

  if (read_awaited) {
    // Run worker
    rfalNfcWorker();

    if (rfalNfcIsDevActivated(rfalNfcGetState())) {
      if (nfc_card_connected) {
        if (!nfc_check_connection(&nfc_card_info)) {
          nfc_restart_discovery();
          nfc_card_connected = false;
        }
      } else {
        if (nfc_identify(&nfc_card_info)) {
          nfc_card_connected = true;
        } else {
          nfc_restart_discovery();
        }
      }
    }

    syshandle_signal_read_ready(SYSHANDLE_NFC, &nfc_card_connected);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  nfc_fsm_t* fsm = &g_nfc_tls[task_id];
  bool new_state = *(bool*)param;

  if (new_state && !(fsm->last_state)) {
    fsm->connected = 1;
  }
  if (!new_state && fsm->last_state) {
    fsm->disconnected = 1;
  }
  return fsm->connected || fsm->disconnected;
}

static const syshandle_vmt_t g_nfc_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
