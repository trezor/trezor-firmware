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

#include <io/nfc_backup.h>
#include <rfal_nfc.h>
#include <sys/sysevent_source.h>

#include "nfc_backup_poll.h"

typedef struct {
  // Last state
  nfc_backup_state_t last_state;
  // Pending events
  nfc_backup_event_t events;
} nfc_backup_fsm_t;

// State machine for each task
static nfc_backup_fsm_t g_nfc_backup_tls[SYSTASK_MAX_TASKS] = {0};

static const syshandle_vmt_t g_pm_handle_vmt;

bool nfc_backup_poll_init(void) {
  return syshandle_register(SYSHANDLE_NFC_BACKUP, &g_pm_handle_vmt, NULL);
}

void nfc_backup_poll_deinit() { syshandle_unregister(SYSHANDLE_NFC_BACKUP); }

bool nfc_backup_get_events(nfc_backup_event_t* events) {
  nfc_backup_fsm_t* fsm = &g_nfc_backup_tls[systask_id(systask_active())];

  *events = fsm->events;
  fsm->events = 0;
  return true;
}

static bool nfc_backup_fsm_update(nfc_backup_fsm_t* fsm,
                                  nfc_backup_state_t* new_state) {
  bool new_event = false;

  if (new_state->connected != fsm->last_state.connected) {
    if (new_state->connected) {
      fsm->events = NFC_BACKUP_CONNECTED;
    } else {
      fsm->events = NFC_BACKUP_DISCONNECTED;
    }
    new_event = true;
  }

  fsm->last_state = *new_state;

  return new_event;
}

static void on_task_created(void* context, systask_id_t task_id) {
  // Initialize FSM for the task
  nfc_backup_fsm_t* fsm = &g_nfc_backup_tls[task_id];
  memset(fsm, 0, sizeof(nfc_backup_fsm_t));
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(write_awaited);

  if (read_awaited) {
    nfc_backup_state_t state = {.connected = false};

    // Run worker
    rfalNfcWorker();

    rfalNfcState rfal_state = rfalNfcGetState();
    if (rfalNfcIsDevActivated(rfal_state)) {
      // Read system info to verify connection
      nfc_backup_system_info_t system_info;
      if (nfc_backup_read_system_info(&system_info)) {
        state.connected = true;
      } else {
        rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);
      }
    }

    syshandle_signal_read_ready(SYSHANDLE_NFC_BACKUP, &state);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  nfc_backup_fsm_t* fsm = &g_nfc_backup_tls[task_id];
  nfc_backup_state_t* new_state = (nfc_backup_state_t*)param;

  return nfc_backup_fsm_update(fsm, new_state);
}

static const syshandle_vmt_t g_pm_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
