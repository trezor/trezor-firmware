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
#ifdef USE_BLE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/ble.h>

#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "wire/wire_iface_ble.h"
#include "workflow.h"

static bool encode_pairing_code(uint32_t code, uint8_t *outbuf) {
  if (code < 0 || code > 999999) {
    return false;
  }
  for (size_t i = 0; i < BLE_PAIRING_CODE_LEN; i++) {
    outbuf[BLE_PAIRING_CODE_LEN - i - 1] = '0' + (code % 10);
    code /= 10;
  }
  return true;
}

workflow_result_t workflow_ble_pairing_request(void) {
  ble_iface_start_pairing();

  uint32_t code = screen_pairing_mode(ui_get_initial_setup());

  if (code == 0) {
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

  uint32_t result = ui_screen_confirm_pairing(code);

  uint8_t pairing_code[BLE_PAIRING_CODE_LEN] = {0};

  if (result == UI_RESULT_CONFIRM && encode_pairing_code(code, pairing_code)) {
    ble_command_t cmd = {
        .cmd_type = BLE_ALLOW_PAIRING,
        .data_len = sizeof(pairing_code),
    };
    memcpy(cmd.data.raw, pairing_code, sizeof(pairing_code));
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
