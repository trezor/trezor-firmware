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
  if (code > 999999) {
    return false;
  }
  for (size_t i = 0; i < BLE_PAIRING_CODE_LEN; i++) {
    outbuf[BLE_PAIRING_CODE_LEN - i - 1] = '0' + (code % 10);
    code /= 10;
  }
  return true;
}

workflow_result_t workflow_ble_pairing_request(const vendor_header *const vhdr,
                                               const image_header *const hdr) {
  if (!ble_iface_start_pairing()) {
    return WF_OK_PAIRING_FAILED;
  }
  c_layout_t layout;
  memset(&layout, 0, sizeof(layout));
  screen_pairing_mode(ui_get_initial_setup(), &layout);

  uint32_t code = 0;
  workflow_result_t res = workflow_host_control(vhdr, hdr, &layout, &code);

  if (res != WF_OK_UI_ACTION) {
    ble_iface_end_pairing();
    return res;
  }

  if (code == PAIRING_MODE_CANCEL) {
    ble_iface_end_pairing();
    return WF_OK_PAIRING_FAILED;
  }

  uint32_t result = ui_screen_confirm_pairing(code);

  uint8_t pairing_code[BLE_PAIRING_CODE_LEN] = {0};

  if (result != CONFIRM || !encode_pairing_code(code, pairing_code)) {
    ble_command_t cmd = {
        .cmd_type = BLE_REJECT_PAIRING,
    };
    ble_issue_command(&cmd);
    return WF_OK_PAIRING_FAILED;
  }

  ble_command_t cmd = {
      .cmd_type = BLE_ALLOW_PAIRING,
      .data_len = sizeof(pairing_code),
  };
  memcpy(cmd.data.raw, pairing_code, sizeof(pairing_code));
  ble_issue_command(&cmd);

  bool skip_finalization = false;

  sysevents_t awaited = {0};
  sysevents_t signalled = {0};
  awaited.read_ready |= 1 << SYSHANDLE_BLE;

  sysevents_poll(&awaited, &signalled, 500);

  if (signalled.read_ready == 1 << SYSHANDLE_BLE) {
    ble_event_t event = {0};
    if (ble_get_event(&event)) {
      if (event.type == BLE_PAIRING_COMPLETED) {
        skip_finalization = true;
      }
    }
  }

  if (!skip_finalization) {
    pairing_mode_finalization_result_t r =
        screen_pairing_mode_finalizing(ui_get_initial_setup());
    if (r == PAIRING_FINALIZATION_FAILED) {
      ble_iface_end_pairing();
      return WF_OK_PAIRING_FAILED;
    }
    if (r == PAIRING_FINALIZATION_CANCEL) {
      ble_command_t disconnect = {.cmd_type = BLE_DISCONNECT};
      ble_issue_command(&disconnect);
      ble_iface_end_pairing();
      return WF_OK_PAIRING_FAILED;
    }
  }

  return WF_OK_PAIRING_COMPLETED;
}

#endif
