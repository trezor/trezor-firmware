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
#include "workflow.h"

workflow_result_t workflow_ble_pairing_request(const char *code) {
  ui_result_t result = ui_screen_confirm_pairing(code);

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
