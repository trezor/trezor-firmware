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
  bool connected;        // unreported connect edge
  bool disconnected;     // unreported disconnect edge
  bool transceive_done;  // unreported transceive done
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

  if (fsm->transceive_done) {
    fsm->transceive_done = false;
    *event = NFC_EVENT_TRANSCEIVE_DONE;
    return true;
  } else if (fsm->connected && fsm->disconnected) {
    fsm->connected = false;
    fsm->disconnected = false;
    fsm->last_state = false;
  } else if (fsm->connected) {
    fsm->connected = false;
    fsm->last_state = true;
    *event = NFC_EVENT_CONNECTED;
    return true;
  } else if (fsm->disconnected) {
    fsm->disconnected = false;
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
    bool xfer_pending = nfc_transceive_process();

    if (rfalNfcIsDevActivated(rfalNfcGetState())) {
      if (nfc_card_connected) {
        // The presence check would interfere with the exchange in progress.
        // If the card is removed meanwhile, the exchange fails and the next
        // check detects it.
        if (!xfer_pending && !nfc_check_connection(&nfc_card_info)) {
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
    } else {
      nfc_card_connected = false;
    }

    void* transceive_done = (void*)nfc_transceive_take_event();
    syshandle_signal_read_ready(SYSHANDLE_NFC, transceive_done);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  nfc_fsm_t* fsm = &g_nfc_tls[task_id];
  bool new_state = nfc_card_connected;
  bool transceive_done = (bool)param;

  if (transceive_done) {
    fsm->transceive_done = true;
  }
  if (new_state && !(fsm->last_state)) {
    fsm->connected = true;
  }
  if (!new_state && fsm->last_state) {
    fsm->disconnected = true;
  }
  return fsm->connected || fsm->disconnected || fsm->transceive_done;
}

static const syshandle_vmt_t g_nfc_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
