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
#include <wire/wire_iface_ble.h>
#ifdef USE_BLE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/ble.h>

#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "workflow.h"

workflow_result_t workflow_ble_pairing_request(void) {
  ble_iface_start_pairing();

  uint32_t result = screen_pairing_mode(ui_get_initial_setup());

  if (result == 0) {
    ble_state_t state = {0};

    ble_get_state(&state);

    if (state.peer_count > 0) {
      ble_command_t cmd = {.cmd_type = BLE_SWITCH_ON};
      ble_issue_command(&cmd);
    } else {
      ble_command_t cmd = {.cmd_type = BLE_SWITCH_OFF};
      ble_issue_command(&cmd);
    }

    return WF_OK;
  }

  result = ui_screen_confirm_pairing(result);

  if (result == UI_RESULT_CONFIRM) {
    ble_command_t cmd = {
        .cmd_type = BLE_ALLOW_PAIRING,
    };
    ble_issue_command(&cmd);
  } else {
    ble_command_t cmd = {
        .cmd_type = BLE_REJECT_PAIRING,
    };
    ble_issue_command(&cmd);
  }

  return WF_OK;
}

#endif
