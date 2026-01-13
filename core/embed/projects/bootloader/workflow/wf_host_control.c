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
#include <rust_ui_bootloader.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/systick.h>
#include <sys/types.h>

#include "protob/protob.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

#ifdef USE_BLE
#include <wire/wire_iface_ble.h>
#endif

static workflow_result_t bootloader_process_comm(wire_iface_t *wire_iface) {
  if (wire_iface == NULL) {
    // continue with the event processing
    return WF_OK;
  }

  protob_io_t active_iface;
  protob_init(&active_iface, wire_iface);

  uint16_t msg_id = 0;
  if (sectrue != protob_get_msg_header(&active_iface, &msg_id)) {
    return WF_OK;
  }

  fw_info_t fw;
  memset(&fw, 0, sizeof(fw));

  switch (msg_id) {
    case MessageType_MessageType_Initialize:
      fw_check(&fw);
      workflow_initialize(&active_iface, &fw);
      // continue with the event processing
      return WF_OK;
      break;
    case MessageType_MessageType_Ping:
      workflow_ping(&active_iface);
      // continue with the event processing
      return WF_OK;
      break;
    case MessageType_MessageType_GetFeatures:
      fw_check(&fw);
      workflow_get_features(&active_iface, &fw);
      // continue with the event processing
      return WF_OK;
      break;
    case MessageType_MessageType_WipeDevice:
      return workflow_wipe_device(&active_iface);
      break;
    case MessageType_MessageType_FirmwareErase:
      return workflow_firmware_update(&active_iface);
      break;
#if defined LOCKABLE_BOOTLOADER
    case MessageType_MessageType_UnlockBootloader:
      return workflow_unlock_bootloader(&active_iface);
      break;
#endif
    default:
      recv_msg_unknown(&active_iface);
      // continue with the event processing
      return WF_OK;
  }
}

workflow_result_t bootloader_process_usb(void) {
  wire_iface_t *iface = usb_iface_get();
  return bootloader_process_comm(iface);
}

#ifdef USE_BLE
workflow_result_t bootloader_process_ble(void) {
  wire_iface_t *iface = ble_iface_get();
  return bootloader_process_comm(iface);
}
#endif

void workflow_ifaces_init(secbool usb21_landing, protob_ios_t *ios) {
  size_t cnt = 1;
  memset(ios, 0, sizeof(*ios));

  wire_iface_t *usb_iface = usb_iface_init(usb21_landing);

  protob_init(&ios->ifaces[0], usb_iface);

#ifdef USE_BLE
  wire_iface_t *ble_iface = ble_iface_init();

  protob_init(&ios->ifaces[1], ble_iface);
  cnt++;
#endif

  ios->count = cnt;
}

void workflow_ifaces_deinit(protob_ios_t *ios) {
  systick_delay_ms(100);
  usb_iface_deinit();
#ifdef USE_BLE
  ble_iface_deinit();
#endif
}

void workflow_ifaces_pause(protob_ios_t *ios) {
  if (ios == NULL) {
    return;
  }
  usb_iface_deinit();
#ifdef USE_BLE
  ble_iface_deinit();
#endif
}

void workflow_ifaces_resume(protob_ios_t *ios) {
  if (ios == NULL) {
    return;
  }
  workflow_ifaces_init(secfalse, ios);
}
