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

#include "antiglitch.h"
#include "bootui.h"
#include "workflow.h"

typedef enum {
  SCREEN_INTRO,
  SCREEN_MENU,
  SCREEN_WAIT_FOR_HOST,
} screen_t;

workflow_result_t workflow_bootloader(const vendor_header *const vhdr,
                                      const image_header *const hdr,
                                      secbool firmware_present) {
  ui_set_initial_setup(false);

  screen_t screen = SCREEN_INTRO;

  while (true) {
    switch (screen) {
      case SCREEN_INTRO: {
        intro_result_t ui_result = ui_screen_intro(vhdr, hdr, firmware_present);
        if (ui_result == INTRO_MENU) {
          screen = SCREEN_MENU;
        }
        if (ui_result == INTRO_HOST) {
          screen = SCREEN_WAIT_FOR_HOST;
        }
      } break;
      case SCREEN_MENU: {
        menu_result_t menu_result = ui_screen_menu(firmware_present);
        if (menu_result == MENU_EXIT) {  // exit menu
          screen = SCREEN_INTRO;
        }
        if (menu_result == MENU_REBOOT) {  // reboot
#ifndef USE_HASH_PROCESSOR
          ui_screen_boot_stage_1(true);
#endif
          jump_allow_1();
          jump_allow_2();
          return WF_OK_REBOOT_SELECTED;
        }
        if (menu_result == MENU_WIPE) {  // wipe
          workflow_result_t r = workflow_wipe_device(NULL);
          if (r == WF_ERROR) {
            return r;
          }
          if (r == WF_OK_DEVICE_WIPED) {
            return r;
          }
          if (r == WF_CANCELLED) {
            screen = SCREEN_MENU;
            continue;
          }
          return WF_ERROR_FATAL;
        }
      } break;
      case SCREEN_WAIT_FOR_HOST: {
        workflow_result_t res =
            workflow_host_control(vhdr, hdr, ui_screen_connect);
        switch (res) {
          case WF_CANCELLED:
            screen = SCREEN_INTRO;
            continue;
          default:
            return res;
        }
      } break;
      default:
        return WF_ERROR_FATAL;
        break;
    }
  }
}
