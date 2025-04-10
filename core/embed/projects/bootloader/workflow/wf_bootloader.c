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
#include "rust_ui_bootloader.h"
#include "workflow.h"

workflow_result_t workflow_menu(const vendor_header* const vhdr,
                                const image_header* const hdr,
                                secbool firmware_present) {
  while (true) {
    c_layout_t layout;
    memset(&layout, 0, sizeof(layout));
    screen_menu(ui_get_initial_setup(), firmware_present, &layout);
    uint32_t ui_result = 0;
    workflow_result_t result =
        workflow_host_control(vhdr, hdr, &layout, &ui_result);

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
    if (menu_result == MENU_REBOOT) {  // reboot
      jump_allow_1();
      jump_allow_2();
      return WF_OK_REBOOT_SELECTED;
    }
    if (menu_result == MENU_WIPE) {  // wipe
      workflow_result_t r = workflow_wipe_device(NULL);
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
                            secbool firmware_present,
                            workflow_result_t* out_result) {
  workflow_result_t res = workflow_menu(vhdr, hdr, firmware_present);
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
                                     secbool firmware_present,
                                     workflow_result_t* out_result) {
  c_layout_t layout;
  memset(&layout, 0, sizeof(layout));
  uint32_t ui_res = 0;

  screen_connect(false, true, &layout);
  workflow_result_t res = workflow_host_control(vhdr, hdr, &layout, &ui_res);

  switch (res) {
    case WF_OK_UI_ACTION: {
      switch (ui_res) {
        case CONNECT_CANCEL:
          return SCREEN_INTRO;
#ifdef USE_BLE
        case CONNECT_PAIRING_MODE: {
          workflow_result_t ble = workflow_ble_pairing_request(vhdr, hdr);
          if (ble == WF_OK_PAIRING_COMPLETED || ble == WF_OK_PAIRING_FAILED)
            return SCREEN_WAIT_FOR_HOST;
          if (ble == WF_CANCELLED) return SCREEN_INTRO;
          *out_result = ble;
          return SCREEN_DONE;
        }
#endif
        case CONNECT_MENU:
          return SCREEN_MENU;
        default:
          *out_result = WF_ERROR_FATAL;
          return SCREEN_DONE;
      }
    }

    case WF_CANCELLED: {
      return SCREEN_INTRO;
    }
    default:
      *out_result = res;
      return SCREEN_DONE;
  }
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
        screen = handle_menu(vhdr, hdr, firmware_present, &final_res);
        break;
      case SCREEN_WAIT_FOR_HOST:
        screen = handle_wait_for_host(vhdr, hdr, firmware_present, &final_res);
        break;
      default:
        // shouldn’t happen
        return WF_ERROR_FATAL;
    }
  }

  return final_res;
}
