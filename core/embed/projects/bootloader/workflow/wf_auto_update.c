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

#include <antiglitch.h>
#include <sys/bootargs.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <util/image.h>

#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "workflow.h"

workflow_result_t workflow_auto_update(const vendor_header *const vhdr,
                                       const image_header *const hdr) {
  ui_set_initial_setup(true);

  workflow_result_t res = WF_CANCELLED;
  uint32_t ui_result = CONNECT_CANCEL;

  c_layout_t layout;
  memset(&layout, 0, sizeof(layout));
  screen_connect(true, false, &layout);
  res = workflow_host_control(vhdr, hdr, &layout, &ui_result);

  if (res == WF_OK_UI_ACTION && ui_result == CONNECT_CANCEL) {
    bootargs_set(BOOT_COMMAND_NONE, NULL, 0);
    jump_allow_1();
    jump_allow_2();
    return WF_OK_REBOOT_SELECTED;
  }

  return res;
}
