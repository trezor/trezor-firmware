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

#include "bootui.h"
#include "protob.h"
#include "rust_ui.h"
#include "workflow.h"

workflow_result_t workflow_wipe_device(protob_io_t *iface) {
  WipeDevice msg_recv;
  if (iface != NULL) {
    recv_msg_wipe_device(iface, &msg_recv);
  }
  ui_result_t response = ui_screen_wipe_confirm();
  if (UI_RESULT_CONFIRM != response) {
    if (iface != NULL) {
      send_user_abort(iface, "Wipe cancelled");
    }
    return WF_CANCELLED;
  }
  ui_screen_wipe();
  secbool wipe_result = erase_device(ui_screen_wipe_progress);

  if (sectrue != wipe_result) {
    if (iface != NULL) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Could not erase flash");
    }
    screen_wipe_fail();
    return WF_ERROR;
  }

  if (iface != NULL) {
    send_msg_success(iface, NULL);
  }
  screen_wipe_success();
  return WF_OK_DEVICE_WIPED;
}
