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

#include <sys/types.h>
#include <util/image.h>

#ifdef TREZOR_EMULATOR
#include "SDL.h"
#endif

#include "bootui.h"
#include "workflow.h"
#include "workflow_internal.h"

workflow_result_t workflow_bootloader(const vendor_header *const vhdr,
                                      const image_header *const hdr,
                                      secbool firmware_present) {
  workflow_reset_jump();
  ui_set_initial_setup(false);

  screen_t screen = SCREEN_INTRO;
  uint32_t ui_result = 0;

  while (true) {
    switch (screen) {
      case SCREEN_INTRO:
        ui_result = ui_screen_intro(vhdr, hdr, firmware_present);
        if (ui_result == 1) {
          screen = SCREEN_MENU;
        }
        if (ui_result == 2) {
          screen = SCREEN_WAIT_FOR_HOST;
        }
        break;
      case SCREEN_MENU:
        ui_result = ui_screen_menu(firmware_present);
        if (ui_result == 0xAABBCCDD) {  // exit menu
          screen = SCREEN_INTRO;
        }
        if (ui_result == 0x11223344) {  // reboot
#ifndef USE_HASH_PROCESSOR
          ui_screen_boot_stage_1(true);
#endif
          workflow_allow_jump_1();
          workflow_allow_jump_2();
          return WF_CONTINUE_TO_FIRMWARE;
        }
        if (ui_result == 0x55667788) {  // wipe
          workflow_result_t r = workflow_wipe_device(NULL, 0, NULL);
          if (r == WF_SHUTDOWN) {
            return r;
          }
        }
        break;
      case SCREEN_WAIT_FOR_HOST:
        ui_screen_connect();
        workflow_result_t res =
            workflow_host_control(vhdr, hdr, ui_screen_connect);
        switch (res) {
          case WF_STAY:
            break;
          case WF_RETURN:
            screen = SCREEN_INTRO;
            break;
          default:
            return workflow_exit_common(res);
        }
        break;
      default:
        return WF_WIPE_AND_SHUTDOWN;
        break;
    }
  }
}
