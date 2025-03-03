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
#include <util/image.h>

#include "antiglitch.h"
#include "poll.h"
#include "protob/protob.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

#ifdef USE_BLE
#include <wire/wire_iface_ble.h>

#ifdef USE_BUTTON
#include <io/button.h>
#endif
#endif

workflow_result_t workflow_host_control(const vendor_header *const vhdr,
                                        const image_header *const hdr,
                                        void (*redraw_wait_screen)(void)) {
  wire_iface_t usb_iface = {0};
  wire_iface_t ble_iface = {0};
  protob_io_t protob_usb_iface = {0};
  protob_io_t protob_ble_iface = {0};

  redraw_wait_screen();

  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_iface_init(&usb_iface,
                 (vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

  ble_iface_init(&ble_iface);

  protob_init(&protob_usb_iface, &usb_iface);
  protob_init(&protob_ble_iface, &ble_iface);

  workflow_result_t result = WF_ERROR_FATAL;

  for (;;) {
    uint16_t ifaces[] = {
        protob_get_iface_flag(&protob_usb_iface) | MODE_READ,
#ifdef USE_BLE
        protob_get_iface_flag(&protob_ble_iface) | MODE_READ,
        IFACE_BLE_EVENT,
#ifdef USE_BUTTON
        IFACE_BUTTON,
#endif
#endif
    };

    poll_event_t e = {0};

    int16_t i = poll_events(ifaces, ARRAY_LENGTH(ifaces), &e, 100);

    if (i < 0) {
      continue;
    }

    uint16_t msg_id = 0;
    protob_io_t *active_iface = NULL;

    if (i < IFACE_USB_MAX) {
      switch (e.event.usb_data_event) {
        case EVENT_USB_CAN_READ:
          if (i == protob_get_iface_flag(&protob_usb_iface) &&
              sectrue == protob_get_msg_header(&protob_usb_iface, &msg_id)) {
            active_iface = &protob_usb_iface;
          } else {
            continue;
          }
          break;
        default:
          continue;
      }
    }
#ifdef USE_BLE
    if (i == IFACE_BLE) {
      switch (e.event.ble_data_event) {
        case EVENT_BLE_CAN_READ:
          if (i == protob_get_iface_flag(&protob_ble_iface) &&
              sectrue == protob_get_msg_header(&protob_ble_iface, &msg_id)) {
            active_iface = &protob_ble_iface;
          } else {
            continue;
          }
          break;
        default:
          continue;
      }
    }
    if (i == IFACE_BLE_EVENT) {
      switch (e.event.ble_event.type) {
        case BLE_PAIRING_REQUEST:
          workflow_ble_pairing_request(e.event.ble_event.data);
          continue;
        default:
          break;
      }
    }
#ifdef USE_BUTTON
    if (i == IFACE_BUTTON) {
      switch (e.event.button_event.type) {
        case (BTN_EVT_DOWN >> 24):
          ble_iface_start_pairing();
        default:
          continue;
      }
    }
#endif
#endif

    if (active_iface == NULL) {
      continue;
      ;
    }

    switch (msg_id) {
      case MessageType_MessageType_Initialize:
        workflow_initialize(active_iface, vhdr, hdr);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_Ping:
        workflow_ping(active_iface);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_GetFeatures:
        workflow_get_features(active_iface, vhdr, hdr);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_WipeDevice:
        result = workflow_wipe_device(active_iface);
        if (result == WF_OK) {
          systick_delay_ms(100);
          usb_iface_deinit(&usb_iface);
          return WF_OK_DEVICE_WIPED;
        }
        break;
      case MessageType_MessageType_FirmwareErase:
        result = workflow_firmware_update(active_iface);
        if (result == WF_OK) {
          jump_allow_1();
          jump_allow_2();
          systick_delay_ms(100);
          usb_iface_deinit(&usb_iface);
          return WF_OK_FIRMWARE_INSTALLED;
        }
        break;
#if defined USE_OPTIGA
      case MessageType_MessageType_UnlockBootloader:
        result = workflow_unlock_bootloader(active_iface);
        if (result == WF_OK) {
          systick_delay_ms(100);
          usb_iface_deinit(&usb_iface);
          return WF_OK_BOOTLOADER_UNLOCKED;
        }
        break;
#endif
      default:
        recv_msg_unknown(active_iface);
        continue;
    }

    systick_delay_ms(100);
    usb_iface_deinit(&usb_iface);
    return result;
  }
}
