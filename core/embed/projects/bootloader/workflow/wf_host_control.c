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

#include <sys/sysevent.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/image.h>

#include "protob/protob.h"
#include "wire/wire_iface_usb.h"
#include "workflow.h"

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_BLE
#include <wire/wire_iface_ble.h>
#endif

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_POWER_MANAGER
#include <io/display.h>
#include <io/display_utils.h>
#include <sys/power_manager.h>

#define FADE_TIME_MS 30000
#define SUSPEND_TIME_MS 40000

#endif

workflow_result_t workflow_host_control(const vendor_header *const vhdr,
                                        const image_header *const hdr,
                                        c_layout_t *wait_layout,
                                        uint32_t *ui_action_result,
                                        protob_ios_t *ios) {
  workflow_result_t result = WF_ERROR_FATAL;

#ifdef USE_POWER_MANAGER
  uint32_t button_deadline = 0;
#ifdef USE_HAPTIC
  bool button_haptic_played = false;
#endif
  uint32_t fade_deadline = ticks_timeout(FADE_TIME_MS);
  uint32_t suspend_deadline = ticks_timeout(SUSPEND_TIME_MS);
  bool faded = false;
  int fade_value = display_get_backlight();
#endif

  sysevents_t awaited = {0};

  if (ios != NULL) {
    for (size_t i = 0; i < ios->count; i++) {
      awaited.read_ready |= 1 << protob_get_iface_flag(&ios->ifaces[i]);
    }
  }

#ifdef USE_BLE
  awaited.read_ready |= 1 << SYSHANDLE_BLE;
#endif
#ifdef USE_BUTTON
  awaited.read_ready |= 1 << SYSHANDLE_BUTTON;
#endif
#ifdef USE_TOUCH
  awaited.read_ready |= 1 << SYSHANDLE_TOUCH;
#endif
#ifdef USE_POWER_MANAGER
  awaited.read_ready |= 1 << SYSHANDLE_POWER_MANAGER;
#endif

  uint32_t res = screen_attach(wait_layout);

  if (res != 0) {
    if (ui_action_result != NULL) {
      *ui_action_result = res;
    }
    result = WF_OK_UI_ACTION;
    goto exit_host_control;
  }

  for (;;) {
    sysevents_t signalled = {0};

    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

#ifdef USE_POWER_MANAGER

#ifdef USE_HAPTIC
    if (button_deadline != 0 && !button_haptic_played &&
        ticks_expired(button_deadline)) {
      // we reached hibernation time
      haptic_play(HAPTIC_BOOTLOADER_ENTRY);
      button_haptic_played = true;
    }
#endif

    if (signalled.read_ready == 0) {
      pm_state_t pm_state = {0};

      pm_get_state(&pm_state);

      if (pm_state.usb_connected) {
        fade_deadline = ticks_timeout(FADE_TIME_MS);
        suspend_deadline = ticks_timeout(SUSPEND_TIME_MS);
        continue;
      }

      // device idle.
      if (!faded && ticks_expired(fade_deadline)) {
        fade_value = display_get_backlight();
        display_fade(fade_value, BACKLIGHT_LOW, 200);
        faded = true;
      }

      if (ticks_expired(suspend_deadline)) {
        pm_suspend(NULL);
        screen_render(wait_layout);
        display_fade(display_get_backlight(), fade_value, 200);
        button_deadline = 0;
        faded = false;
        fade_deadline = ticks_timeout(FADE_TIME_MS);
        suspend_deadline = ticks_timeout(SUSPEND_TIME_MS);
      }
      continue;
    }

    fade_deadline = ticks_timeout(FADE_TIME_MS);
    suspend_deadline = ticks_timeout(SUSPEND_TIME_MS);
    if (faded) {
      display_fade(display_get_backlight(), fade_value, 200);
      faded = false;
    }

    // in case of battery powered device, power button is handled by eventloop
    if (signalled.read_ready & (1 << SYSHANDLE_BUTTON)) {
      button_event_t btn_event = {0};
      // todo this eats all button events, not only power button, so it needs to
      //  be handled differently for button-based battery powered devices.
      if (button_get_event(&btn_event) && btn_event.button == BTN_POWER) {
        if (btn_event.event_type == BTN_EVENT_DOWN) {
          button_deadline = ticks_timeout(3000);
#ifdef USE_HAPTIC
          button_haptic_played = false;
#endif
        } else if (btn_event.event_type == BTN_EVENT_UP &&
                   button_deadline != 0) {
          display_fade(display_get_backlight(), 0, 200);
          if (ticks_expired(button_deadline)) {
            // power button pressed for 3 seconds, we hibernate

#ifdef USE_HAPTIC
            if (!button_haptic_played) {
              haptic_play(HAPTIC_BOOTLOADER_ENTRY);
              button_haptic_played = true;
            }
#endif
            pm_hibernate();
          } else {
            pm_suspend(NULL);
            button_deadline = 0;
            screen_render(wait_layout);
            display_fade(display_get_backlight(), BACKLIGHT_NORMAL, 200);
            faded = false;
            fade_deadline = ticks_timeout(FADE_TIME_MS);
            suspend_deadline = ticks_timeout(SUSPEND_TIME_MS);
          }
        }
      }
    }

#else
    if (signalled.read_ready == 0) {
      continue;
    }
#endif

    uint16_t msg_id = 0;
    protob_io_t *active_iface = NULL;

    if (ios != NULL) {
      for (size_t i = 0; i < ios->count; i++) {
        if (signalled.read_ready ==
                (1 << protob_get_iface_flag(&ios->ifaces[i])) &&
            sectrue == protob_get_msg_header(&ios->ifaces[i], &msg_id)) {
          active_iface = &ios->ifaces[i];
          break;
        }
      }
    }

    // no data, lets pass the event signal to UI
    if (active_iface == NULL) {
      uint32_t res = screen_event(wait_layout, &signalled);

      if (res != 0) {
        if (ui_action_result != NULL) {
          *ui_action_result = res;
        }
        result = WF_OK_UI_ACTION;
        goto exit_host_control;
      }
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
        goto exit_host_control;
        break;
#if defined LOCKABLE_BOOTLOADER
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
  return result;
}

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
