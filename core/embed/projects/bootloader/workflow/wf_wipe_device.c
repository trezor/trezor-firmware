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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <util/flash_utils.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif

#include <sys/systick.h>

#include "bootui.h"
#include "protob.h"
#include "rust_ui.h"
#include "workflow.h"

static void send_error_conditionally(protob_io_t* iface, char* msg) {
  if (iface != NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Could not read BLE status");
  }
}

#ifdef USE_BLE
static bool wipe_bonds(protob_io_t* iface) {
  ble_state_t state = {0};
  ble_get_state(&state);

  if (!state.state_known) {
    send_error_conditionally(iface, "Could not read BLE status");
    screen_wipe_fail();
    return false;
  }

  ble_command_t ble_command = {0};
  ble_command.cmd_type = BLE_ERASE_BONDS;
  if (!ble_issue_command(&ble_command)) {
    send_error_conditionally(iface, "Could not issue BLE command");
    screen_wipe_fail();
    return false;
  }

  uint32_t deadline = ticks_timeout(100);

  while (true) {
    ble_get_state(&state);
    if (state.peer_count == 0) {
      break;
    }
    if (ticks_expired(deadline)) {
      send_error_conditionally(iface, "Could not erase bonds");
      screen_wipe_fail();
      return false;
    }
  }

  return true;
}
#endif

workflow_result_t workflow_wipe_device(protob_io_t* iface) {
  ui_result_t response = ui_screen_wipe_confirm();
  if (UI_RESULT_CONFIRM != response) {
    if (iface != NULL) {
      send_user_abort(iface, "Wipe cancelled");
    }
    return WF_CANCELLED;
  }
  ui_screen_wipe();
  secbool wipe_result = erase_device(ui_screen_wipe_progress);

#ifdef USE_BLE
  if (!wipe_bonds(iface)) {
    return WF_ERROR;
  }
#endif

  if (sectrue != wipe_result) {
    send_error_conditionally(iface, "Could not erase flash");
    screen_wipe_fail();
    return WF_ERROR;
  }

  if (iface != NULL) {
    send_msg_success(iface, NULL);
  }
  screen_wipe_success();
  return WF_OK;
}
