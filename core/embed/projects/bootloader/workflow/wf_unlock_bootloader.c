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
#include <sys/flash_utils.h>

#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#include "bootui.h"
#include "protob.h"
#include "rust_ui_bootloader.h"
#include "workflow.h"

workflow_result_t workflow_unlock_bootloader(protob_io_t *iface) {
  confirm_result_t response = ui_screen_unlock_bootloader_confirm();
  if (CONFIRM != response) {
    send_user_abort(iface, "Bootloader unlock cancelled");
    return WF_CANCELLED;
  }
#ifdef USE_STORAGE_HWKEY
  secret_bhk_regenerate();
#endif
  ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
  ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif

  secret_unlock_bootloader();
  send_msg_success(iface, NULL);

  screen_unlock_bootloader_success();
  return WF_OK_BOOTLOADER_UNLOCKED;
}
