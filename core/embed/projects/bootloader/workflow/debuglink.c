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

#include <trezor_rtl.h>

#include <io/../../touch_debug.h>

#include <io/display_utils.h>

#include "protob/protob.h"
#include "protob/protob_debug.h"
#include "version_check.h"
#include "wire/debug_iface_usb.h"
#include "workflow.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

static protob_io_t g_debug_io;

static bool layout_ready = false;
static bool query_pending = false;

void debuglink_init(void) {
  wire_iface_t *wire = usb_debug_iface_init();

  protob_init(&g_debug_io, wire);
}

void debuglink_deinit(void) { usb_debug_iface_deinit(); }

static void debuglink_process_get_state(protob_io_t *io) {
  DebugLinkGetState msg_recv;

  recv_msg_debug_link_get_state(io, &msg_recv);

  if (!msg_recv.has_wait_layout) {
    // defaults to current layout behavior
    if (!layout_ready) {
      query_pending = true;
    } else {
      send_msg_debug_link_state(io);
      query_pending = false;
    }
    return;
  }

  switch (msg_recv.wait_layout) {
    case DebugWaitType_IMMEDIATE:
      send_msg_debug_link_state(io);
      break;
    case DebugWaitType_NEXT_LAYOUT:
      layout_ready = false;
      query_pending = true;
      break;
    default:
    case DebugWaitType_CURRENT_LAYOUT:
      if (!layout_ready) {
        query_pending = true;
      } else {
        send_msg_debug_link_state(io);
        query_pending = false;
      }
      break;
  }
}

static void debuglink_process_decision(protob_io_t *io) {
  DebugLinkDecision msg_recv;
  recv_msg_debug_link_decision(io, &msg_recv);

#ifdef USE_TOUCH
  if (msg_recv.has_x && msg_recv.has_y) {
    if (!msg_recv.has_touch_event_type) {
      touch_debug_click(msg_recv.x, msg_recv.y);
    } else {
      switch (msg_recv.touch_event_type) {
        case DebugTouchEventType_TOUCH_START:
          touch_debug_start(msg_recv.x, msg_recv.y);
          break;
        case DebugTouchEventType_TOUCH_END:
          touch_debug_end(msg_recv.x, msg_recv.y);
          break;
        default:
        case DebugTouchEventType_TOUCH_FULL_CLICK:
          touch_debug_click(msg_recv.x, msg_recv.y);
          break;
      }
    }
  }
#endif
}

static void debuglink_process_record_screen(protob_io_t *io) {
  DebugLinkRecordScreen msg;

  char buffer[1024];
  memset(buffer, 0, sizeof(buffer));

  recv_msg_debug_link_screen_record(io, &msg, (uint8_t *)buffer,
                                    sizeof(buffer));

  size_t dir_len = strnlen(buffer, sizeof(buffer));

  if (dir_len > 0) {
    display_record_start((uint8_t *)buffer, dir_len, 0);
  } else {
    display_record_stop();
  }

  send_msg_success(&g_debug_io, "success");
}

void debuglink_process(void) {
  vendor_header vhdr = {0};
  volatile secbool vhdr_present = secfalse;
  vhdr_present = read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr);

  const image_header *hdr = NULL;

  // detect whether the device contains a valid firmware
  volatile secbool vhdr_keys_ok = secfalse;  //  todo
  volatile secbool vhdr_lock_ok = secfalse;
  volatile secbool img_hdr_ok = secfalse;
  volatile secbool model_ok = secfalse;
  volatile secbool signatures_ok = secfalse;
  volatile secbool version_ok = secfalse;
  volatile secbool header_present = secfalse;
  volatile secbool firmware_present = secfalse;
  volatile secbool secmon_valid = secfalse;

  if (sectrue == vhdr_present) {
    vhdr_keys_ok = check_vendor_header_keys(&vhdr);
  }

  // todo
  if (sectrue == vhdr_keys_ok) {
    vhdr_lock_ok = sectrue;  // check_vendor_header_lock(&vhdr);
  }

  if (sectrue == vhdr_lock_ok) {
    hdr = read_image_header(
        (const uint8_t *)(size_t)(FIRMWARE_START + vhdr.hdrlen),
        FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);
    if (hdr == (const image_header *)(size_t)(FIRMWARE_START + vhdr.hdrlen)) {
      img_hdr_ok = sectrue;
    }
  }
  if (sectrue == img_hdr_ok) {
    model_ok = check_image_model(hdr);
  }

  if (sectrue == model_ok) {
    signatures_ok =
        check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub);
  }

  if (sectrue == signatures_ok) {
    version_ok = check_firmware_min_version(hdr->monotonic);
  }

  if (sectrue == version_ok) {
    header_present = version_ok;
  }

#ifdef USE_SECMON_VERIFICATION
  size_t secmon_start = (size_t)IMAGE_CODE_ALIGN(FIRMWARE_START + vhdr.hdrlen +
                                                 IMAGE_HEADER_SIZE);

  const secmon_header_t *secmon_hdr =
      read_secmon_header((const uint8_t *)secmon_start, FIRMWARE_MAXSIZE);

  volatile secbool secmon_header_present = secfalse;
  volatile secbool secmon_model_valid = secfalse;
  volatile secbool secmon_header_sig_valid = secfalse;
  volatile secbool secmon_contents_valid = secfalse;

  if (sectrue == header_present) {
    secmon_header_present =
        secbool_and(header_present, (secmon_hdr != NULL) * sectrue);
  }

  if (sectrue == secmon_header_present) {
    secmon_model_valid =
        secbool_and(secmon_header_present, check_secmon_model(secmon_hdr));
  }

  if (sectrue == secmon_model_valid) {
    secmon_header_sig_valid =
        secbool_and(secmon_model_valid, check_secmon_header_sig(secmon_hdr));
  }

  if (sectrue == secmon_header_sig_valid) {
    secmon_contents_valid = secbool_and(
        secmon_header_sig_valid,
        check_secmon_contents(secmon_hdr, secmon_start - FIRMWARE_START,
                              &FIRMWARE_AREA));
    secmon_valid = secmon_contents_valid;
  }

#else
  secmon_valid = header_present;
#endif

  if (sectrue == secmon_valid) {
    firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, &FIRMWARE_AREA);
  }

  fw_info_t fw = {
      .vhdr = &vhdr, .hdr = hdr, .firmware_present = firmware_present};

  uint16_t msg_id = 0;
  if (protob_get_msg_header(&g_debug_io, &msg_id) == sectrue) {
    switch (msg_id) {
      case MessageType_MessageType_Initialize:
        workflow_initialize(&g_debug_io, &fw);
        break;
      case MessageType_MessageType_GetFeatures:
        workflow_get_features(&g_debug_io, &fw);
        break;
      case MessageType_MessageType_Ping:
        workflow_ping(&g_debug_io);
        break;
      case MessageType_MessageType_DebugLinkGetState:
        debuglink_process_get_state(&g_debug_io);
        break;
      case MessageType_MessageType_DebugLinkDecision:
        debuglink_process_decision(&g_debug_io);
        break;
      case MessageType_MessageType_DebugLinkRecordScreen:
        debuglink_process_record_screen(&g_debug_io);
        break;
      default:
        send_msg_success(&g_debug_io, "success");
        break;
    }
  }
}

void debuglink_notify_layout_change(void) {
  layout_ready = true;
  if (query_pending) {
    send_msg_debug_link_state(&g_debug_io);
    query_pending = false;
  }
}
