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

#include <sec/secret.h>

#include "bootui.h"
#include "protob.h"
#include "rust_ui.h"
#include "workflow.h"

workflow_result_t workflow_unlock_bootloader(protob_io_t *iface) {
  ui_result_t response = ui_screen_unlock_bootloader_confirm();
  if (UI_RESULT_CONFIRM != response) {
    send_user_abort(iface, "Bootloader unlock cancelled");
    return WF_CANCELLED;
  }
  secret_optiga_erase();
  send_msg_success(iface, NULL);

  screen_unlock_bootloader_success();
  return WF_OK_BOOTLOADER_UNLOCKED;
}
