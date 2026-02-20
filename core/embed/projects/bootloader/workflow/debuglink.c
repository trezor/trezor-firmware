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

#ifdef USE_TOUCH
#include <io/../../touch_debug.h>
#endif

#ifdef USE_BUTTON
#include <io/../../button_debug.h>
#endif

#include "debuglink.h"

#include <io/display_utils.h>

#include "fw_check.h"
#include "protob/protob.h"
#include "protob/protob_debug.h"
#include "wire/debug_iface_usb.h"
#include "workflow.h"

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
#ifdef USE_BUTTON
  if (msg_recv.has_physical_button) {
    switch (msg_recv.physical_button) {
      case DebugPhysicalButton_LEFT_BTN: {
        button_debug_click(BTN_LEFT);
        break;
      }
      case DebugPhysicalButton_RIGHT_BTN: {
        button_debug_click(BTN_RIGHT);
        break;
      }
      case DebugPhysicalButton_MIDDLE_BTN: {
        button_debug_press(BTN_LEFT);
        button_debug_press(BTN_RIGHT);
        button_debug_release(BTN_LEFT);
        button_debug_release(BTN_RIGHT);
        break;
      }
    }
  }
#endif
}

static debuglink_result_t debuglink_process_record_screen(protob_io_t *io) {
  DebugLinkRecordScreen msg;

  debuglink_result_t res = DEBUGLINK_RESULT_NONE;

  char buffer[1024];
  memset(buffer, 0, sizeof(buffer));

  recv_msg_debug_link_screen_record(io, &msg, (uint8_t *)buffer,
                                    sizeof(buffer));

  size_t dir_len = strnlen(buffer, sizeof(buffer));

  if (dir_len > 0) {
    display_record_start((uint8_t *)buffer, dir_len, 0);
    res = DEBUGLINK_RESULT_REPAINT;
  } else {
    display_record_stop();
  }

  send_msg_success(&g_debug_io, "success");

  return res;
}

debuglink_result_t debuglink_process(void) {
  fw_info_t fw = {0};
  fw_check(&fw);

  debuglink_result_t res = DEBUGLINK_RESULT_NONE;

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
        res = debuglink_process_record_screen(&g_debug_io);
        break;
      default:
        send_msg_success(&g_debug_io, "success");
        break;
    }
  }

  return res;
}

void debuglink_notify_layout_change(void) {
  layout_ready = true;
  if (query_pending) {
    send_msg_debug_link_state(&g_debug_io);
    query_pending = false;
  }
}
