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

#ifdef USE_POWERCTL
#include <sys/powerctl.h>
#endif

#include <io/display.h>
#include <io/display_utils.h>

#include "antiglitch.h"
#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "workflow.h"

typedef enum {
  SCREEN_INTRO,
  SCREEN_MENU,
  SCREEN_WAIT_FOR_HOST,
} screen_t;

workflow_result_t workflow_menu(const vendor_header *const vhdr,
                                const image_header *const hdr,
                                secbool firmware_present) {
  while (true) {
    uint8_t buf[1024];
    screen_menu(ui_get_initial_setup(), firmware_present, buf, sizeof(buf));
    uint32_t ui_result = 0;
    workflow_result_t result =
        workflow_host_control(vhdr, hdr, buf, sizeof(buf), &ui_result);

    if (result != WF_OK_UI_ACTION) {
      return result;
    }

    menu_result_t menu_result = (menu_result_t)ui_result;

    if (menu_result == MENU_EXIT) {  // exit menu
      return WF_OK;
    }
#ifdef USE_BLE
    if (menu_result == MENU_BLUETOOTH) {
      workflow_ble_pairing_request(vhdr, hdr);
      continue;
    }
#endif
#ifdef USE_POWERCTL
    if (menu_result == MENU_POWER_OFF) {  // reboot
      display_fade(display_get_backlight(), 0, 200);
      powerctl_hibernate();
      // in case hibernation failed, continue with menu
      continue;
    }
#endif
    if (menu_result == MENU_WIPE) {  // wipe
      workflow_result_t r = workflow_wipe_device(NULL);
      if (r == WF_ERROR || r == WF_OK_DEVICE_WIPED || r == WF_CANCELLED) {
        return r;
      }
    }
    return WF_ERROR_FATAL;
  }
}

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
        workflow_result_t res = workflow_menu(vhdr, hdr, firmware_present);
        if (res == WF_OK) {
          screen = SCREEN_INTRO;
          continue;
        }
        if (res == WF_CANCELLED) {
          screen = SCREEN_MENU;
          continue;
        }
        return res;
      } break;
      case SCREEN_WAIT_FOR_HOST: {
        uint8_t buf[1024] = {0};
        uint32_t ui_result = 0;
        screen_connect(false, true, buf, sizeof(buf));
        workflow_result_t res =
            workflow_host_control(vhdr, hdr, buf, sizeof(buf), &ui_result);
        switch (res) {
          case WF_OK_UI_ACTION:
            switch (ui_result) {
              case WAIT_CANCEL:
                screen = SCREEN_INTRO;
                break;
#ifdef USE_BLE
              case WAIT_PAIRING_MODE:
                res = workflow_ble_pairing_request(vhdr, hdr);
                if (res == WF_OK_PAIRING_COMPLETED ||
                    res == WF_OK_PAIRING_FAILED) {
                  screen = SCREEN_WAIT_FOR_HOST;
                  break;
                }
                if (res == WF_CANCELLED) {
                  screen = SCREEN_INTRO;
                  break;
                }
                return res;
#endif
              case WAIT_MENU:
                screen = SCREEN_MENU;
                break;
              default:
                return WF_ERROR_FATAL;
            }
            continue;
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
