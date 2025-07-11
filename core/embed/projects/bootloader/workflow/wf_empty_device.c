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

#include <sys/systick.h>
#include <sys/types.h>
#include <util/flash_utils.h>
#include <util/image.h>

#ifdef USE_STORAGE_HWKEY
#include <sec/secret.h>
#endif

#ifdef USE_BACKUP_RAM
#include <sys/backup_ram.h>
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

  protob_ios_t ios;
  workflow_ifaces_init(sectrue, &ios);

  workflow_result_t res = WF_CANCELLED;
  uint32_t ui_result = WELCOME_CANCEL;
  while (res == WF_CANCELLED ||
         (res == WF_OK_UI_ACTION && ui_result == WELCOME_CANCEL)) {
    c_layout_t layout;
    memset(&layout, 0, sizeof(layout));
    screen_welcome(&layout);
    res = workflow_host_control(NULL, NULL, &layout, &ui_result, &ios);
#ifdef USE_BLE
    if (res == WF_OK_UI_ACTION && ui_result == WELCOME_PAIRING_MODE) {
      res = workflow_wireless_setup(NULL, NULL, &ios);
      if (res == WF_OK_PAIRING_COMPLETED || res == WF_OK_PAIRING_FAILED) {
        res = WF_CANCELLED;
        ui_result = WELCOME_CANCEL;
        continue;
      }
      return res;
    }
#endif
    if (res == WF_OK_UI_ACTION && ui_result == WELCOME_MENU) {
      do {
        res = workflow_menu(NULL, NULL, &ios);
      } while (res == WF_CANCELLED);

      if (res == WF_OK) {
        res = WF_CANCELLED;
        ui_result = WELCOME_CANCEL;
        continue;
      }
      workflow_ifaces_deinit(&ios);
      return res;
    }
  }
  workflow_ifaces_deinit(&ios);
  return res;
}
