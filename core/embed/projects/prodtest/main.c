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

#include <memzero.h>
#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <io/rsod.h>
#include <io/usb.h>
#include <io/usb_config.h>
#include <rtl/cli.h>
#include <sec/board_capabilities.h>
#include <sec/unit_properties.h>
#include <sys/flash_otp.h>
#include <sys/system.h>
#include <sys/systick.h>

#include "commands.h"
#include "rust_types.h"
#include "rust_ui_prodtest.h"
#include "sys/sysevent.h"

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_SBU
#include <io/sbu.h>
#endif

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_commands.h>
#include <sec/optiga_init.h>
#include "cmd/prodtest_optiga.h"
#endif

#ifdef USE_RTC
#include <sys/rtc.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_NFC
#include <io/nfc.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#ifdef USE_POWER_MANAGER
#include <io/power_manager.h>
#endif

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef USE_BLE
#include <io/ble.h>
#include "cmd/prodtest_ble.h"
#endif

#ifdef USE_HW_REVISION
#include <sec/hw_revision.h>
#endif

#ifdef USE_TAMPER
#include <sec/tamper.h>
#endif

#ifdef TREZOR_MODEL_T2T1
#define MODEL_IDENTIFIER "TREZOR2-"
#else
#define MODEL_IDENTIFIER MODEL_INTERNAL_NAME "-"
#endif

// Command line interface context
cli_t g_cli = {0};

struct {
  c_layout_t layout;
  bool set;
} g_layout __attribute__((aligned(4))) = {0};

static ssize_t console_read(void *context, char *buf, size_t size) {
  return syshandle_read(SYSHANDLE_USB_VCP, buf, size);
}

static ssize_t console_write(void *context, const char *buf, size_t size) {
  static uint32_t timeout = 2000;
  int rc = syshandle_write_blocking(SYSHANDLE_USB_VCP, buf, size, timeout);
  // Do not wait too long if the host is not connected.
  // This is a workaround that needs to be fixed properly later.
  timeout = rc < size ? 100 : 2000;
  return rc;
}

static void usb_vcp_intr_callback(void) { cli_abort(&g_cli); }

// Set if the RGB LED must not be controlled by the main loop
static bool g_rgbled_control_disabled = false;

void prodtest_disable_rgbled_control(void) { g_rgbled_control_disabled = true; }

static void drivers_init(void) {
  parse_boardloader_capabilities();
  unit_properties_init();

#ifdef USE_RTC
  rtc_init();
#endif
#ifdef USE_BACKUP_RAM
  backup_ram_init();
#endif
#ifdef USE_POWER_MANAGER
  pm_init(true);
  pm_set_soc_target(70);
#endif

  display_init(DISPLAY_RESET_CONTENT);

#ifdef USE_TAMPER
  tamper_init();
#endif
#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif
#ifdef USE_SD_CARD
  sdcard_init();
#endif
#ifdef USE_BUTTON
  button_init();
#endif
#ifdef USE_TOUCH
  touch_init();
#endif
#ifdef USE_SBU
  sbu_init();
#endif
#ifdef USE_HAPTIC
  haptic_init();
#endif
#ifdef USE_RGB_LED
  rgb_led_init();
#endif
#ifdef USE_BLE
  ble_init();
#endif
#ifdef USE_TROPIC
#ifdef TREZOR_EMULATOR
  tropic_init(28992);
#else
  tropic_init();
#endif
  tropic_wait_for_ready();
#endif
#ifdef USE_HW_REVISION
  hw_revision_init();
#endif
}

void prodtest_show_homescreen(void) {
  memset(&g_layout, 0, sizeof(g_layout));
  g_layout.set = true;

  static char device_sn[MAX_DEVICE_SN_SIZE] = {0};
  size_t device_sn_size = 0;
  if (unit_properties_get_sn((uint8_t *)device_sn, sizeof(device_sn) - 1,
                             &device_sn_size)) {
    screen_prodtest_welcome(&g_layout.layout, device_sn, device_sn_size);
  } else {
    screen_prodtest_welcome(&g_layout.layout, NULL, 0);
  }
}

#ifndef TREZOR_EMULATOR
int main(void) {
#else
int prodtest_main(void) {
#endif
  system_init(&rsod_panic_handler);

  drivers_init();

  ensure(usb_configure(&usb_vcp_intr_callback), "usb_configure failed");

  ensure(usb_start(NULL), "usb_start failed");

  // Initialize command line interface
  cli_init(&g_cli, console_read, console_write, NULL);

  cli_set_commands(&g_cli, commands_get_ptr(), commands_count());

#ifdef USE_OPTIGA
  optiga_init();
  optiga_open_application();
#endif

#if defined USE_BUTTON && defined USE_POWER_MANAGER
  uint32_t btn_deadline = 0;
#endif

#ifdef USE_RGB_LED
  uint32_t led_start_deadline = ticks_timeout(1000);
  rgb_led_set_color(RGBLED_GREEN);
#endif

#ifdef TREZOR_MODEL_T3W1
  display_set_backlight(155);
#else
  display_set_backlight(150);
#endif

  prodtest_show_homescreen();

  while (true) {
    sysevents_t awaited = {0};
    awaited.read_ready |= 1 << SYSHANDLE_USB_VCP;
#ifdef USE_BUTTON
    awaited.read_ready |= 1 << SYSHANDLE_BUTTON;
#endif
#ifdef USE_TOUCH
    awaited.read_ready |= 1 << SYSHANDLE_TOUCH;
#endif
#ifdef USE_POWER_MANAGER
    awaited.read_ready |= 1 << SYSHANDLE_POWER_MANAGER;
#endif
    sysevents_t signalled = {0};
    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

    if (signalled.read_ready & (1 << SYSHANDLE_USB_VCP)) {
      const cli_command_t *cmd = cli_process_io(&g_cli);

      if (cmd != NULL) {
        screen_prodtest_bars("", 0);
        memzero(&g_layout, sizeof(g_layout));
        cli_process_command(&g_cli, cmd);
      }

      continue;
    }

#if defined USE_BUTTON && defined USE_POWER_MANAGER
    if (signalled.read_ready & (1 << SYSHANDLE_BUTTON)) {
      button_event_t btn_event = {0};
      if (button_get_event(&btn_event) && btn_event.button == BTN_POWER) {
        if (btn_event.event_type == BTN_EVENT_DOWN) {
          btn_deadline = ticks_timeout(1000);
        } else if (btn_event.event_type == BTN_EVENT_UP) {
          if (ticks_expired(btn_deadline)) {
            pm_hibernate();
#ifdef USE_RGB_LED
            rgb_led_set_color(RGBLED_YELLOW);
            systick_delay_ms(1000);
            rgb_led_set_color(0);
#endif
          }
        }
      }
    }
    if (button_is_down(BTN_POWER) && ticks_expired(btn_deadline)) {
#ifdef USE_RGB_LED
      rgb_led_set_color(RGBLED_RED);
#endif
    }
#endif

#ifdef USE_RGB_LED
    if (ticks_expired(led_start_deadline) && !g_rgbled_control_disabled) {
      g_rgbled_control_disabled = true;
      rgb_led_set_color(0);
    }
#endif

    if (signalled.read_ready == 0) {
      // timeout, let's wait again
      continue;
    }

    // proceed to UI

    if (g_layout.set) {
      screen_prodtest_event(&g_layout.layout, &signalled);
    }
  }

  return 0;
}
