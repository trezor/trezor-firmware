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

#include <bootui.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/sysevent.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/image.h>

#include "antiglitch.h"
#include "protob/protob.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

#ifdef USE_BLE
#include <wire/wire_iface_ble.h>
#endif

workflow_result_t workflow_host_control(
    const vendor_header *const vhdr, const image_header *const hdr,
    uint32_t (*wait_layout_fnc)(uint8_t *mem, size_t mem_len,
                                sysevents_t *signalled),
    uint8_t *wait_layout, size_t wait_layout_len) {
  wire_iface_t usb_iface = {0};
  protob_io_t protob_usb_iface = {0};

  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_iface_init(&usb_iface,
                 (vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

  protob_init(&protob_usb_iface, &usb_iface);

#ifdef USE_BLE
  wire_iface_t ble_iface = {0};
  protob_io_t protob_ble_iface = {0};
  ble_iface_init(&ble_iface);
  protob_init(&protob_ble_iface, &ble_iface);
#endif

  workflow_result_t result = WF_ERROR_FATAL;

  sysevents_t awaited = {0};

  awaited.read_ready |= 1 << protob_get_iface_flag(&protob_usb_iface);

#ifdef USE_BLE
  awaited.read_ready |= 1 << protob_get_iface_flag(&protob_ble_iface);
  awaited.read_ready |= 1 << SYSHANDLE_BLE;
#endif
#ifdef USE_BUTTON
  awaited.read_ready |= 1 << SYSHANDLE_BUTTON;
#endif
#ifdef USE_TOUCH
  awaited.read_ready |= 1 << SYSHANDLE_TOUCH;
#endif

  for (;;) {
    sysevents_t signalled = {0};

    sysevents_poll(&awaited, &signalled, 100);

    if (signalled.read_ready == 0) {
      continue;
    }

    uint16_t msg_id = 0;
    protob_io_t *active_iface = NULL;

    if (signalled.read_ready ==
            (1 << protob_get_iface_flag(&protob_usb_iface)) &&
        sectrue == protob_get_msg_header(&protob_usb_iface, &msg_id)) {
      active_iface = &protob_usb_iface;
    }

#ifdef USE_BLE
    if (signalled.read_ready ==
            (1 << protob_get_iface_flag(&protob_ble_iface)) &&
        sectrue == protob_get_msg_header(&protob_ble_iface, &msg_id)) {
      active_iface = &protob_ble_iface;
    }
#endif

    // no data, lets pass the event signal to UI
    if (active_iface == NULL) {
      wait_result_t res =
          wait_layout_fnc(wait_layout, wait_layout_len, &signalled);

      if (res == WAIT_CANCEL) {
        result = WF_CANCELLED;
        goto exit_host_control;
      }
#ifdef USE_BLE
      if (res == WAIT_PAIRING_MODE) {
        workflow_ble_pairing_request();
        // redraw the wait screen
        wait_layout_fnc(wait_layout, wait_layout_len, &signalled);
      }
#endif

      continue;
    }

    switch (msg_id) {
      case MessageType_MessageType_Initialize:
        workflow_initialize(active_iface, vhdr, hdr);
        // whatever the result, we stay here and continue
        break;
      case MessageType_MessageType_Ping:
        workflow_ping(active_iface);
        // whatever the result, we stay here and continue
        break;
      case MessageType_MessageType_GetFeatures:
        workflow_get_features(active_iface, vhdr, hdr);
        // whatever the result, we stay here and continue
        break;
      case MessageType_MessageType_WipeDevice:
        result = workflow_wipe_device(active_iface);
        goto exit_host_control;
        break;
      case MessageType_MessageType_FirmwareErase:
        result = workflow_firmware_update(active_iface);
        if (result == WF_OK_FIRMWARE_INSTALLED) {
          jump_allow_1();
          jump_allow_2();
        }
        goto exit_host_control;
        break;
#if defined USE_OPTIGA
      case MessageType_MessageType_UnlockBootloader:
        result = workflow_unlock_bootloader(active_iface);
        goto exit_host_control;
        break;
#endif
      default:
        recv_msg_unknown(active_iface);
        break;
    }
  }

exit_host_control:
  systick_delay_ms(100);
  usb_iface_deinit(&usb_iface);
  return result;
}
