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

#ifdef USE_POWER_MANAGER
#include <sys/power_manager.h>
#endif

#include <io/display.h>
#include <io/display_utils.h>

#include "antiglitch.h"
#include "bootui.h"
#include "rust_ui_bootloader.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

workflow_result_t workflow_menu(const vendor_header* const vhdr,
                                const image_header* const hdr,
                                protob_ios_t* ios) {
  while (true) {
    c_layout_t layout;
    memset(&layout, 0, sizeof(layout));
    screen_menu(ui_get_initial_setup(), &layout);
    uint32_t ui_result = 0;
    workflow_result_t result =
        workflow_host_control(vhdr, hdr, &layout, &ui_result, ios);

    if (result != WF_OK_UI_ACTION) {
      return result;
    }

    menu_result_t menu_result = (menu_result_t)ui_result;

    if (menu_result == MENU_EXIT) {  // exit menu
      return WF_OK;
    }
#ifdef USE_BLE
    if (menu_result == MENU_BLUETOOTH) {
      workflow_ifaces_pause(ios);
      workflow_ble_pairing_request(vhdr, hdr);
      workflow_ifaces_resume(ios);
      continue;
    }
#endif
#ifdef USE_POWER_MANAGER
    if (menu_result == MENU_POWER_OFF) {  // reboot
      display_fade(display_get_backlight(), 0, 200);
      pm_hibernate();
      // in case hibernation failed, continue with menu
      continue;
    }
#endif
    if (menu_result == MENU_REBOOT) {  // reboot
      jump_allow_1();
      jump_allow_2();
      return WF_OK_REBOOT_SELECTED;
    }
    if (menu_result == MENU_WIPE) {  // wipe
      workflow_ifaces_pause(ios);
      workflow_result_t r = workflow_wipe_device(NULL);
      if (r == WF_CANCELLED) {
        workflow_ifaces_resume(ios);
      }
      if (r == WF_ERROR || r == WF_OK_DEVICE_WIPED || r == WF_CANCELLED) {
        return r;
      }
    }
    return WF_ERROR_FATAL;
  }
}

typedef enum {
  SCREEN_INTRO,
  SCREEN_MENU,
  SCREEN_WAIT_FOR_HOST,
  SCREEN_DONE,
} screen_t;

// Each handler returns either a next screen, or SCREEN_DONE and an out‑param
// for the result.
static screen_t handle_intro(const vendor_header* vhdr, const image_header* hdr,
                             secbool firmware_present,
                             workflow_result_t* out_result) {
  intro_result_t ui = ui_screen_intro(vhdr, hdr, firmware_present);
  if (ui == INTRO_MENU) return SCREEN_MENU;
  if (ui == INTRO_HOST) return SCREEN_WAIT_FOR_HOST;
  // no other valid INTRO result -> fatal
  *out_result = WF_ERROR_FATAL;
  return SCREEN_DONE;
}

static screen_t handle_menu(const vendor_header* vhdr, const image_header* hdr,
                            workflow_result_t* out_result) {
  workflow_result_t res = workflow_menu(vhdr, hdr, NULL);
  switch (res) {
    case WF_OK:
      return SCREEN_INTRO;  // back to intro
    case WF_CANCELLED:
      return SCREEN_MENU;  // re‑show menu
    default:
      *out_result = res;  // final result
      return SCREEN_DONE;
  }
}

static screen_t handle_wait_for_host(const vendor_header* vhdr,
                                     const image_header* hdr,
                                     workflow_result_t* out_result) {
  c_layout_t layout;
  memset(&layout, 0, sizeof(layout));
  uint32_t ui_res = 0;

  protob_ios_t ios;
  workflow_ifaces_init(secfalse, &ios);

  screen_t next_screen = SCREEN_WAIT_FOR_HOST;

  while (next_screen == SCREEN_WAIT_FOR_HOST) {
    screen_connect(false, true, &layout);
    workflow_result_t res =
        workflow_host_control(vhdr, hdr, &layout, &ui_res, &ios);

    switch (res) {
      case WF_OK_UI_ACTION: {
        switch (ui_res) {
          case CONNECT_CANCEL:
            next_screen = SCREEN_INTRO;
            break;
#ifdef USE_BLE
          case CONNECT_PAIRING_MODE: {
            workflow_ifaces_pause(&ios);
            workflow_result_t ble = workflow_ble_pairing_request(vhdr, hdr);
            workflow_ifaces_resume(&ios);
            if (ble == WF_OK_PAIRING_COMPLETED || ble == WF_OK_PAIRING_FAILED) {
              next_screen = SCREEN_WAIT_FOR_HOST;
            } else if (ble == WF_CANCELLED) {
              next_screen = SCREEN_INTRO;
            } else {
              *out_result = ble;
              next_screen = SCREEN_DONE;
            }
            break;
          }
#endif
          case CONNECT_MENU: {
            workflow_result_t menu_result = WF_CANCELLED;
            while (menu_result == WF_CANCELLED) {
              menu_result = workflow_menu(vhdr, hdr, &ios);
              switch (menu_result) {
                case WF_OK:
                  next_screen = SCREEN_WAIT_FOR_HOST;
                  break;
                case WF_CANCELLED:
                  // stay in menu
                  break;
                default:
                  *out_result = menu_result;  // final result
                  next_screen = SCREEN_DONE;
                  break;
              }
            }
          } break;
          default:
            *out_result = WF_ERROR_FATAL;
            next_screen = SCREEN_DONE;
            break;
        }

      } break;
      case WF_CANCELLED: {
        next_screen = SCREEN_INTRO;
      } break;
      default:
        *out_result = res;
        next_screen = SCREEN_DONE;
        break;
    }
  }

  workflow_ifaces_deinit(&ios);
  return next_screen;
}

workflow_result_t workflow_bootloader(const vendor_header* vhdr,
                                      const image_header* hdr,
                                      secbool firmware_present) {
  ui_set_initial_setup(false);
  screen_t screen = SCREEN_INTRO;
  workflow_result_t final_res = WF_ERROR_FATAL;

  while (screen != SCREEN_DONE) {
    switch (screen) {
      case SCREEN_INTRO:
        screen = handle_intro(vhdr, hdr, firmware_present, &final_res);
        break;
      case SCREEN_MENU:
        screen = handle_menu(vhdr, hdr, &final_res);
        break;
      case SCREEN_WAIT_FOR_HOST:
        screen = handle_wait_for_host(vhdr, hdr, &final_res);
        break;
      default:
        // shouldn’t happen
        return WF_ERROR_FATAL;
    }
  }

  return final_res;
}
