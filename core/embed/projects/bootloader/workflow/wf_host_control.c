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

#include <io/usb.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/image.h>

#include "antiglitch.h"
#include "bootui.h"
#include "poll.h"
#include "protob/protob.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

workflow_result_t workflow_host_control(const vendor_header *const vhdr,
                                        const image_header *const hdr,
                                        void (*redraw_wait_screen)(void)) {
  wire_iface_t usb_iface = {0};
  protob_iface_t protob_usb_iface = {0};

  ui_screen_connect();

  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_iface_init(&usb_iface,
                 (vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

  protob_init(&protob_usb_iface, &usb_iface);

  uint8_t buf[MAX_PACKET_SIZE] = {0};

  workflow_result_t result = WF_ERROR_FATAL;

  for (;;) {
    uint16_t ifaces[1] = {protob_get_iface_flag(&protob_usb_iface) | MODE_READ};
    poll_event_t e = {0};

    uint8_t i = poll_events(ifaces, 1, &e, 100);

    uint16_t msg_id = 0;
    uint32_t msg_size = 0;
    protob_iface_t *active_iface = NULL;

    switch (e.type) {
      case EVENT_USB_CAN_READ:
        if (i == protob_get_iface_flag(&protob_usb_iface) &&
            sectrue == protob_get_msg_header(&protob_usb_iface, buf, &msg_id,
                                             &msg_size)) {
          active_iface = &protob_usb_iface;
        } else {
          continue;
        }
        break;
      case EVENT_NONE:
      default:
        continue;
    }

    switch (msg_id) {
      case MessageType_MessageType_Initialize:
        workflow_initialize(active_iface, msg_size, buf, vhdr, hdr);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_Ping:
        workflow_ping(active_iface, msg_size, buf);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_GetFeatures:
        workflow_get_features(active_iface, msg_size, buf, vhdr, hdr);
        // whatever the result, we stay here and continue
        continue;
      case MessageType_MessageType_WipeDevice:
        result = workflow_wipe_device(active_iface, msg_size, buf);
        if (result == WF_OK) {
          systick_delay_ms(100);
          usb_deinit();
          return WF_OK_DEVICE_WIPED;
        }
        break;
      case MessageType_MessageType_FirmwareErase:
        result = workflow_firmware_update(active_iface, msg_size, buf);
        if (result == WF_OK) {
          jump_allow_1();
          jump_allow_2();
          systick_delay_ms(100);
          usb_deinit();
          return WF_OK_FIRMWARE_INSTALLED;
        }
        break;
#if defined USE_OPTIGA
      case MessageType_MessageType_UnlockBootloader:
        result = workflow_unlock_bootloader(active_iface, msg_size, buf);
        if (result == WF_OK) {
          systick_delay_ms(100);
          usb_deinit();
          return WF_OK_BOOTLOADER_UNLOCKED;
        }
        break;
#endif
      default:
        recv_msg_unknown(active_iface, msg_size, buf);
        continue;
    }

    return result;
  }
}
