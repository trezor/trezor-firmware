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
#include <io/usb.h>
#include <rtl/cli.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/board_capabilities.h>
#include <util/flash_otp.h>
#include <util/rsod.h>
#include <util/unit_properties.h>

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
#include <sys/backup_ram.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
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
#include <sys/power_manager.h>
#endif

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef USE_BLE
#include <io/ble.h>
#include <util/unit_properties.h>
#include "cmd/prodtest_ble.h"
#endif

#ifdef USE_HW_REVISION
#include <util/hw_revision.h>
#endif

#ifdef USE_TAMPER
#include <sys/tamper.h>
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

#define VCP_IFACE 0

static size_t console_read(void *context, char *buf, size_t size) {
  return usb_vcp_read(VCP_IFACE, (uint8_t *)buf, size);
}

static size_t console_write(void *context, const char *buf, size_t size) {
  return usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)buf, size, 100);
}

static void vcp_intr(void) { cli_abort(&g_cli); }

#if defined(USE_USB_HS)
#define VCP_PACKET_LEN 512
#elif defined(USE_USB_FS)
#define VCP_PACKET_LEN 64
#elif defined(TREZOR_EMULATOR)
#define VCP_PACKET_LEN 64
#else
#error "USB type not defined"
#endif

#define VCP_BUFFER_LEN 2048

static void usb_init_all(void) {
  static const usb_dev_info_t dev_info = {
      .device_class = 0xEF,     // Composite Device Class
      .device_subclass = 0x02,  // Common Class
      .device_protocol = 0x01,  // Interface Association Descriptor
      .vendor_id = 0x1209,
      .product_id = 0x53C1,
      .release_num = 0x0400,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
      .serial_number = "000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = secfalse,
      .usb21_landing = secfalse,
  };

  static uint8_t tx_packet[VCP_PACKET_LEN];
  static uint8_t tx_buffer[VCP_BUFFER_LEN];
  static uint8_t rx_packet[VCP_PACKET_LEN];
  static uint8_t rx_buffer[VCP_BUFFER_LEN];

  static const usb_vcp_info_t vcp_info = {
      .tx_packet = tx_packet,
      .tx_buffer = tx_buffer,
      .rx_packet = rx_packet,
      .rx_buffer = rx_buffer,
      .tx_buffer_len = VCP_BUFFER_LEN,
      .rx_buffer_len = VCP_BUFFER_LEN,
      .rx_intr_fn = vcp_intr,
      .rx_intr_byte = 3,  // Ctrl-C
      .iface_num = VCP_IFACE,
      .data_iface_num = 0x01,
#ifdef TREZOR_EMULATOR
      .emu_port = 21424,
#else
      .ep_cmd = 0x02,
      .ep_in = 0x01,
      .ep_out = 0x01,
#endif
      .polling_interval = 10,
      .max_packet_len = VCP_PACKET_LEN,
  };

  ensure(usb_init(&dev_info), NULL);
  ensure(usb_vcp_add(&vcp_info), "usb_vcp_add");
  ensure(usb_start(), NULL);
}

// Set if the RGB LED must not be controlled by the main loop
static bool g_rgbled_control_disabled = false;

void prodtest_disable_rgbled_control(void) { g_rgbled_control_disabled = true; }

static void drivers_init(void) {
  parse_boardloader_capabilities();
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
  unit_properties_init();
  ble_init();
#endif
#ifdef USE_TROPIC
  tropic_init();
#endif
#ifdef USE_HW_REVISION
  hw_revision_init();
#endif
}

void prodtest_show_homescreen(void) {
  memset(&g_layout, 0, sizeof(g_layout));
  g_layout.set = true;

  static char device_sn[FLASH_OTP_BLOCK_SIZE] = {0};

  if (sectrue == flash_otp_read(FLASH_OTP_BLOCK_DEVICE_SN, 0,
                                (uint8_t *)device_sn, sizeof(device_sn)) &&
      (device_sn[0] != 0xFF)) {
    screen_prodtest_welcome(&g_layout.layout, device_sn,
                            strnlen(device_sn, sizeof(device_sn) - 1));
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
  usb_init_all();

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

  display_set_backlight(150);
  prodtest_show_homescreen();

  while (true) {
    sysevents_t awaited = {0};
    awaited.read_ready |= 1 << VCP_IFACE;
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

    if (signalled.read_ready & (1 << VCP_IFACE)) {
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
            rgb_led_set_color(RGBLED_YELLOW);
            systick_delay_ms(1000);
            rgb_led_set_color(0);
          }
        }
      }
    }
    if (button_is_down(BTN_POWER) && ticks_expired(btn_deadline)) {
      rgb_led_set_color(RGBLED_RED);
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
