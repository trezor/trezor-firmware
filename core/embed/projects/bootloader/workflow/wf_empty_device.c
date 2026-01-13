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

#include <sys/notify.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/flash_utils.h>
#include <util/image.h>

#ifdef USE_STORAGE_HWKEY
#include <sec/secret.h>
#endif

#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#ifdef USE_BLE
#include <io/ble.h>

#include "wire/wire_iface_ble.h"
#endif

#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "workflow.h"

workflow_result_t workflow_empty_device(void) {
  ui_set_initial_setup(true);

#ifdef USE_STORAGE_HWKEY
  secret_bhk_regenerate();
#endif
  ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
  ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif

#ifdef USE_BLE
  screen_boot_empty();
  ble_wait_until_ready();
#endif

  protob_ios_t ios;
  workflow_ifaces_init(sectrue, &ios);
  notify_send(NOTIFY_UNLOCK);

  workflow_result_t res = WF_CANCELLED;
  uint32_t ui_result = WELCOME_CANCEL;
  while (res == WF_CANCELLED ||
         (res == WF_OK_UI_ACTION && ui_result == WELCOME_CANCEL)) {
    res = screen_welcome(&ui_result);
#ifdef USE_BLE
    if (res == WF_OK_UI_ACTION && ui_result == WELCOME_PAIRING_MODE) {
      res = workflow_wireless_setup(NULL, &ios);
      if (res == WF_OK_PAIRING_COMPLETED || res == WF_OK_PAIRING_FAILED) {
        res = WF_CANCELLED;
        ui_result = WELCOME_CANCEL;
        continue;
      }
      break;
    }
#endif
    if (res == WF_OK_UI_ACTION && ui_result == WELCOME_MENU) {
      do {
        res = workflow_menu(NULL, &ios);
      } while (res == WF_CANCELLED);

      if (res == WF_OK) {
        res = WF_CANCELLED;
        ui_result = WELCOME_CANCEL;
        continue;
      }
      break;
    }
  }
  notify_send(NOTIFY_LOCK);
  workflow_ifaces_deinit(&ios);
  return res;
}
