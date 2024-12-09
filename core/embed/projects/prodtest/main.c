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

#include <trezor_bsp.h>  // required by #ifdef STM32U5 below (see #4306 issue)
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <ctype.h>
#include <stdlib.h>
#include <sys/types.h>

#include <gfx/fonts.h>
#include <gfx/gfx_draw.h>
#include <io/display.h>
#include <io/display_utils.h>
#include <io/usb.h>
#include <sec/random_delays.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <util/board_capabilities.h>
#include <util/flash.h>
#include <util/flash_otp.h>
#include <util/fwutils.h>
#include <util/image.h>
#include <util/rsod.h>
#include "prodtest_common.h"
#include "version.h"

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_SBU
#include <io/sbu.h>
#endif

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
#include "optiga_prodtest.h"
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#include "memzero.h"

#ifdef USE_POWERCTL
#include <sys/powerctl.h>
#include "../../sys/powerctl/npm1300/npm1300.h"
#include "../../sys/powerctl/stwlc38/stwlc38.h"
#endif

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef STM32U5
#include "stm32u5xx_ll_utils.h"
#else
#include "stm32f4xx_ll_utils.h"
#endif

#ifdef TREZOR_MODEL_T
#define MODEL_IDENTIFIER "TREZOR2-"
#else
#define MODEL_IDENTIFIER MODEL_INTERNAL_NAME "-"
#endif

static gfx_text_attr_t bold = {
    .font = FONT_BOLD,
    .fg_color = COLOR_WHITE,
    .bg_color = COLOR_BLACK,
};

static secbool startswith(const char *s, const char *prefix) {
  return sectrue * (0 == strncmp(s, prefix, strlen(prefix)));
}

static void vcp_intr(void) {
  gfx_clear();
  error_shutdown("vcp_intr");
}

static char vcp_getchar(void) {
  uint8_t c = 0;
  int r = usb_vcp_read_blocking(VCP_IFACE, &c, 1, -1);
  (void)r;
  return (char)c;
}

static void vcp_readline(char *buf, size_t len) {
  for (;;) {
    char c = vcp_getchar();
    if (c == '\r') {
      vcp_puts("\r\n", 2);
      break;
    }
    if (c < 32 || c > 126) {  // not printable
      continue;
    }
    if (len > 1) {  // leave space for \0
      *buf = c;
      buf++;
      len--;
      vcp_puts(&c, 1);
    }
  }
  if (len > 0) {
    *buf = '\0';
  }
}

static void usb_init_all(void) {
  enum {
    VCP_PACKET_LEN = 64,
    VCP_BUFFER_LEN = 1024,
  };

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
      .ep_cmd = 0x02,
      .ep_in = 0x01,
      .ep_out = 0x01,
      .polling_interval = 10,
      .max_packet_len = VCP_PACKET_LEN,
  };

  ensure(usb_init(&dev_info), NULL);
  ensure(usb_vcp_add(&vcp_info), "usb_vcp_add");
  ensure(usb_start(), NULL);
}

void extract_params(const char *str, int *numbers, int *count, int max_count) {
  int i = 0;
  int num_index = 0;
  int len = strlen(str);
  char buffer[20];  // buffer to hold the current number string

  while (i < len && num_index < max_count) {
    if (isdigit((int)str[i])) {
      int buffer_index = 0;
      // Extract the number
      while (isdigit((int)str[i]) && i < len) {
        buffer[buffer_index++] = str[i++];
      }
      buffer[buffer_index] = '\0';  // null-terminate the string

      // Convert the extracted string to an integer
      numbers[num_index++] = atoi(buffer);
    } else {
      i++;
    }
  }
  *count = num_index;
}

static void draw_border(int width, int padding) {
  const int W = width, P = padding, RX = DISPLAY_RESX, RY = DISPLAY_RESY;

  gfx_clear();

  gfx_rect_t r_out = gfx_rect_wh(P, P, RX - 2 * P, RY - 2 * P);
  gfx_rect_t r_in =
      gfx_rect_wh(P + W, P + W, RX - 2 * (P + W), RY - 2 * (P + W));

  gfx_draw_bar(r_out, COLOR_WHITE);
  gfx_draw_bar(r_in, COLOR_BLACK);

  display_refresh();
}

static void draw_welcome_screen(void) {
#if defined TREZOR_MODEL_R || defined TREZOR_MODEL_T3B1
  gfx_draw_bar(gfx_rect_wh(0, 0, DISPLAY_RESX, DISPLAY_RESY), COLOR_WHITE);
  display_refresh();
#else
  draw_border(1, 3);
#endif
}

static void test_border(void) {
  draw_border(2, 0);
  vcp_println("OK");
}

static void test_display(const char *colors) {
  gfx_clear();

  size_t l = strlen(colors);
  size_t w = DISPLAY_RESX / l;

  for (size_t i = 0; i < l; i++) {
    gfx_color_t c = COLOR_BLACK;  // black
    switch (colors[i]) {
      case 'R':
        c = gfx_color_rgb(255, 0, 0);
        break;
      case 'G':
        c = gfx_color_rgb(0, 255, 0);
        break;
      case 'B':
        c = gfx_color_rgb(0, 0, 255);
        break;
      case 'W':
        c = COLOR_WHITE;
        break;
    }

    gfx_rect_t r = gfx_rect_wh(i * w, 0, i * w + w, DISPLAY_RESY);
    gfx_draw_bar(r, c);
  }
  display_refresh();
  vcp_println("OK");
}

#ifdef USE_BUTTON

static secbool test_btn_press(uint32_t deadline, uint32_t btn) {
  while (button_get_event() != (btn | BTN_EVT_DOWN)) {
    if (systick_ms() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }
  while (button_get_event() != (btn | BTN_EVT_UP)) {
    if (systick_ms() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }

  return sectrue;
}

static secbool test_btn_all(uint32_t deadline) {
  bool left_pressed = 0;
  bool right_pressed = 0;
  while (true) {
    uint32_t buttons = button_get_event();
    if (buttons == (BTN_LEFT | BTN_EVT_DOWN)) {
      left_pressed = 1;
    }
    if (buttons == (BTN_RIGHT | BTN_EVT_DOWN)) {
      right_pressed = 1;
    }
    if (buttons == (BTN_LEFT | BTN_EVT_UP)) {
      left_pressed = 0;
    }
    if (buttons == (BTN_RIGHT | BTN_EVT_UP)) {
      right_pressed = 0;
    }
    if (left_pressed && right_pressed) {
      break;
    }
    if (systick_ms() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }

  while (true) {
    uint32_t buttons = button_get_event();
    if (buttons == (BTN_LEFT | BTN_EVT_DOWN)) {
      left_pressed = 1;
    }
    if (buttons == (BTN_RIGHT | BTN_EVT_DOWN)) {
      right_pressed = 1;
    }
    if (buttons == (BTN_LEFT | BTN_EVT_UP)) {
      left_pressed = 0;
    }
    if (buttons == (BTN_RIGHT | BTN_EVT_UP)) {
      right_pressed = 0;
    }
    if (!left_pressed && !right_pressed) {
      break;
    }
    if (systick_ms() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }
  return sectrue;
}

static void test_button(const char *args) {
  int timeout = 0;

  if (startswith(args, "LEFT ")) {
    timeout = args[5] - '0';
    uint32_t deadline = systick_ms() + timeout * 1000;
    secbool r = test_btn_press(deadline, BTN_LEFT);
    if (r == sectrue) vcp_println("OK");
  }

  if (startswith(args, "RIGHT ")) {
    timeout = args[6] - '0';
    uint32_t deadline = systick_ms() + timeout * 1000;
    secbool r = test_btn_press(deadline, BTN_RIGHT);
    if (r == sectrue) vcp_println("OK");
  }

  if (startswith(args, "BOTH ")) {
    timeout = args[5] - '0';
    uint32_t deadline = systick_ms() + timeout * 1000;
    secbool r = test_btn_all(deadline);
    if (r == sectrue) vcp_println("OK");
  }
}

#endif

#ifdef USE_TOUCH
static secbool touch_click_timeout(uint32_t *touch, uint32_t timeout_ms) {
  uint32_t deadline = systick_ms() + timeout_ms;
  uint32_t r = 0;

  while (touch_get_event())
    ;
  while ((touch_get_event() & TOUCH_START) == 0) {
    if (systick_ms() > deadline) return secfalse;
  }
  while (((r = touch_get_event()) & TOUCH_END) == 0) {
    if (systick_ms() > deadline) return secfalse;
  }
  while (touch_get_event())
    ;

  *touch = r;
  return sectrue;
}

static void test_touch(const char *args) {
  int column = args[0] - '0';
  int timeout = args[1] - '0';

  const int width = DISPLAY_RESX / 2;
  const int height = DISPLAY_RESY / 2;

  gfx_clear();
  switch (column) {
    case 1:
      gfx_draw_bar(gfx_rect_wh(0, 0, width, height), COLOR_WHITE);
      break;
    case 2:
      gfx_draw_bar(gfx_rect_wh(width, 0, width, height), COLOR_WHITE);
      break;
    case 3:
      gfx_draw_bar(gfx_rect_wh(width, height, width, height), COLOR_WHITE);
      break;
    default:
      gfx_draw_bar(gfx_rect_wh(0, height, width, height), COLOR_WHITE);
      break;
  }
  display_refresh();

  touch_init();

  uint32_t evt = 0;
  if (touch_click_timeout(&evt, timeout * 1000)) {
    uint16_t x = touch_unpack_x(evt);
    uint16_t y = touch_unpack_y(evt);
    vcp_println("OK %d %d", x, y);
  } else {
    vcp_println("ERROR TIMEOUT");
  }
  gfx_clear();
  display_refresh();

  touch_deinit();
}

static void test_touch_custom(const char *args) {
  static const int expected_params = 5;

  int params[expected_params];
  int num_params = 0;

  extract_params(args, params, &num_params, expected_params);

  if (num_params != expected_params) {
    vcp_println("ERROR PARAM");
    return;
  }

#undef NUM_PARAMS

  int x = params[0];
  int y = params[1];
  int width = params[2];
  int height = params[3];
  int timeout = params[4];

  uint32_t ticks_start = hal_ticks_ms();

  gfx_clear();
  gfx_draw_bar(gfx_rect_wh(x, y, width, height), COLOR_WHITE);
  display_refresh();

  touch_init();

  while (true) {
    if (hal_ticks_ms() - ticks_start > timeout * 1000) {
      vcp_println("ERROR TIMEOUT");
      break;
    }

    uint32_t touch_event = touch_get_event();
    if (touch_event != 0) {
      uint16_t touch_x = touch_unpack_x(touch_event);
      uint16_t touch_y = touch_unpack_y(touch_event);

      if (touch_event & TOUCH_START) {
        vcp_println("TOUCH D %d %d %d", touch_x, touch_y, hal_ticks_ms());
      }
      if (touch_event & TOUCH_MOVE) {
        vcp_println("TOUCH C %d %d %d", touch_x, touch_y, hal_ticks_ms());
      }
      if (touch_event & TOUCH_END) {
        vcp_println("TOUCH U %d %d %d", touch_x, touch_y, hal_ticks_ms());
        vcp_println("OK");
        break;
      }
    }
  }

  gfx_clear();
  display_refresh();

  touch_deinit();
}

static void test_touch_idle(const char *args) {
  static const int expected_params = 1;
  int num_params = 0;

  int params[expected_params];

  extract_params(args, params, &num_params, expected_params);

  if (num_params != expected_params) {
    vcp_println("ERROR PARAM");
    return;
  }

  int timeout = params[0];

  uint32_t ticks_start = hal_ticks_ms();

  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2);
  gfx_draw_text(pos, "DON'T TOUCH", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();

  touch_init();

  while (true) {
    if (hal_ticks_ms() - ticks_start > timeout * 1000) {
      vcp_println("OK");
      break;
    }

    if (touch_activity() == sectrue) {
      vcp_println("ERROR TOUCH DETECTED");
      break;
    }
  }

  gfx_clear();
  display_refresh();

  touch_deinit();
}

static void test_touch_power(const char *args) {
  static const int expected_params = 1;
  int num_params = 0;

  int params[expected_params];

  extract_params(args, params, &num_params, expected_params);

  if (num_params != expected_params) {
    vcp_println("ERROR PARAM");
    return;
  }

  int timeout = params[0];

  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2);
  gfx_draw_text(pos, "MEASURING", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();

  touch_power_set(true);

  systick_delay_ms(timeout);

  vcp_println("OK");

  touch_power_set(false);

  gfx_clear();
  display_refresh();
}

static void test_sensitivity(const char *args) {
  int v = atoi(args);

  touch_init();
  touch_set_sensitivity(v & 0xFF);

  gfx_clear();
  display_refresh();

  for (;;) {
    uint32_t evt = touch_get_event();
    if (evt & TOUCH_START || evt & TOUCH_MOVE) {
      int x = touch_unpack_x(evt);
      int y = touch_unpack_y(evt);
      gfx_clear();
      gfx_draw_bar(gfx_rect_wh(x - 48, y - 48, 96, 96), COLOR_WHITE);
      display_refresh();
    } else if (evt & TOUCH_END) {
      gfx_clear();
      display_refresh();
    }
  }

  touch_deinit();
}

static void touch_version(void) {
  touch_init();
  uint8_t version = touch_get_version();
  vcp_println("OK %d", version);
  touch_deinit();
}
#endif

static void test_pwm(const char *args) {
  int v = atoi(args);

  display_set_backlight(v);
  display_refresh();
  vcp_println("OK");
}

#ifdef USE_SD_CARD
static void test_sd(void) {
#define BLOCK_SIZE (32 * 1024)
  static uint32_t buf1[BLOCK_SIZE / sizeof(uint32_t)];
  static uint32_t buf2[BLOCK_SIZE / sizeof(uint32_t)];

  bool low_speed = false;
#ifndef TREZOR_MODEL_T3T1
  if (sectrue != sdcard_is_present()) {
    vcp_println("ERROR NOCARD");
    return;
  }
#else
  low_speed = true;
#endif

  if (sectrue != sdcard_power_on_unchecked(low_speed)) {
    vcp_println("ERROR POWER ON");
    return;
  }
  if (sectrue != sdcard_read_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
    vcp_println("ERROR sdcard_read_blocks (0)");
    goto power_off;
  }
  for (int j = 1; j <= 2; j++) {
    for (int i = 0; i < BLOCK_SIZE / sizeof(uint32_t); i++) {
      buf1[i] ^= 0xFFFFFFFF;
    }
    if (sectrue !=
        sdcard_write_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
      vcp_println("ERROR sdcard_write_blocks (%d)", j);
      goto power_off;
    }
    systick_delay_ms(1000);
    if (sectrue !=
        sdcard_read_blocks(buf2, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
      vcp_println("ERROR sdcard_read_blocks (%d)", j);
      goto power_off;
    }
    if (0 != memcmp(buf1, buf2, sizeof(buf1))) {
      vcp_println("ERROR DATA MISMATCH");
      goto power_off;
    }
  }
  vcp_println("OK");

power_off:
  sdcard_power_off();
}
#endif

static void test_firmware_version(void) {
  vcp_println("OK %d.%d.%d", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH);
}

static uint32_t read_bootloader_version(void) {
  uint32_t version = 0;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  const image_header *header =
      read_image_header((const uint8_t *)BOOTLOADER_START,
                        BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  if (header != NULL) {
    version = header->version;
  }

  mpu_restore(mpu_mode);
  return version;
}

static void test_bootloader_version(uint32_t version) {
  vcp_println("OK %d.%d.%d", version & 0xFF, (version >> 8) & 0xFF,
              (version >> 16) & 0xFF);
}

static const boardloader_version_t *read_boardloader_version(void) {
  parse_boardloader_capabilities();
  return get_boardloader_version();
}

static void test_boardloader_version(const boardloader_version_t *version) {
  vcp_println("OK %d.%d.%d", version->version_major, version->version_minor,
              version->version_patch);
}

static void test_wipe(void) {
  firmware_invalidate_header();
  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2 + 10);
  gfx_draw_text(pos, "WIPED", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();
  vcp_println("OK");
}

#ifdef USE_SBU
static void test_sbu(const char *args) {
  secbool sbu1 = sectrue * (args[0] == '1');
  secbool sbu2 = sectrue * (args[1] == '1');
  sbu_set(sbu1, sbu2);
  vcp_println("OK");
}
#endif

#ifdef USE_HAPTIC
static void test_haptic(const char *args) {
  int duration_ms = atoi(args);

  if (duration_ms <= 0) {
    vcp_println("ERROR HAPTIC DURATION");
    return;
  }

  if (haptic_test(duration_ms)) {
    vcp_println("OK");

  } else {
    vcp_println("ERROR HAPTIC");
  }
}
#endif

static void test_otp_read(void) {
  uint8_t data[FLASH_OTP_BLOCK_SIZE + 1];
  memzero(data, sizeof(data));
  ensure(flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, data, FLASH_OTP_BLOCK_SIZE),
         NULL);

  // strip trailing 0xFF
  for (size_t i = 0; i < sizeof(data); i++) {
    if (data[i] == 0xFF) {
      data[i] = 0x00;
      break;
    }
  }

  // use (null) for empty data
  if (data[0] == 0x00) {
    vcp_println("OK (null)");
  } else {
    vcp_println("OK %s", (const char *)data);
  }
}

static void test_otp_write(const char *args) {
  if (sectrue == flash_otp_is_locked(FLASH_OTP_BLOCK_BATCH)) {
    vcp_println("ERROR ALREADY WRITTEN");
    return;
  }

  char data[FLASH_OTP_BLOCK_SIZE];
  memzero(data, sizeof(data));
  strncpy(data, args, sizeof(data) - 1);
  ensure(flash_otp_write(FLASH_OTP_BLOCK_BATCH, 0, (const uint8_t *)data,
                         sizeof(data)),
         NULL);
  ensure(flash_otp_lock(FLASH_OTP_BLOCK_BATCH), NULL);
  vcp_println("OK");
}

static void test_otp_read_device_variant() {
  uint8_t data[FLASH_OTP_BLOCK_SIZE] = {0};
  if (sectrue !=
      flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, data, sizeof(data))) {
    vcp_println("ERROR");
    return;
  }

  vcp_print("OK ");
  for (int i = 0; i < sizeof(data); i++) {
    vcp_print("%d ", data[i]);
  }
  vcp_println("");
}

static void test_otp_write_device_variant(const char *args) {
#ifdef USE_OPTIGA
  optiga_locked_status status = get_optiga_locked_status();
  if (status == OPTIGA_LOCKED_FALSE) {
    vcp_println("ERROR NOT LOCKED");
    return;
  }

  if (status != OPTIGA_LOCKED_TRUE) {
    // Error reported by get_optiga_locked_status().
    return;
  }
#endif

  if (sectrue == flash_otp_is_locked(FLASH_OTP_BLOCK_DEVICE_VARIANT)) {
    vcp_println("ERROR ALREADY WRITTEN");
    return;
  }

  volatile char data[FLASH_OTP_BLOCK_SIZE];
  memzero((char *)data, sizeof(data));
  data[0] = 1;

  int arg_start = 0;
  int arg_num = 1;
  int arg_len = 0;
  int n = 0;
  while (args[n] != 0) {
    if (args[n] == ' ') {
      if (arg_len != 0) {
        if (arg_num < sizeof(data)) {
          data[arg_num] = (uint8_t)atoi(&args[arg_start]);
        }
        arg_num++;
      }
      arg_start = n + 1;
      arg_len = 0;
    } else {
      arg_len++;
    }
    n++;
  }

  if (arg_len != 0 && arg_num < sizeof(data)) {
    data[arg_num] = (uint8_t)atoi(&args[arg_start]);
  }

  ensure(flash_otp_write(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0,
                         (const uint8_t *)data, sizeof(data)),
         NULL);
  ensure(flash_otp_lock(FLASH_OTP_BLOCK_DEVICE_VARIANT), NULL);
  vcp_println("OK");
}

static void test_reboot(void) { reboot_device(); }

void cpuid_read(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  uint32_t cpuid[3];
  cpuid[0] = LL_GetUID_Word0();
  cpuid[1] = LL_GetUID_Word1();
  cpuid[2] = LL_GetUID_Word2();

  mpu_restore(mpu_mode);

  vcp_print("OK ");
  vcp_println_hex((uint8_t *)cpuid, sizeof(cpuid));
}

#ifdef USE_POWERCTL
void test_pmic(const char *args) {
  if (strcmp(args, "INIT") == 0) {
    npm1300_deinit();
    bool ok = npm1300_init();
    if (ok) {
      vcp_println("OK");
    } else {
      vcp_println("ERROR # I/O error");
    }
  } else if (strcmp(args, "CHGSTART") == 0) {
    bool ok = npm1300_set_charging(true);
    if (ok) {
      vcp_println("OK # Charging started with %dmA current limit",
                  npm1300_get_charging_limit());
    } else {
      vcp_println("ERROR");
    }
  } else if (strcmp(args, "CHGSTOP") == 0) {
    bool ok = npm1300_set_charging(false);
    if (ok) {
      vcp_println("OK # Charging stopped");
    } else {
      vcp_println("ERROR # I/O error");
    }
  } else if (strncmp(args, "CHGLIMIT", 8) == 0) {
    int i_charge = atoi(&args[8]);
    if (i_charge < NPM1300_CHARGING_LIMIT_MIN ||
        i_charge > NPM1300_CHARGING_LIMIT_MAX) {
      vcp_println("ERROR # Out of range");
      return;
    } else {
      bool ok = npm1300_set_charging_limit(i_charge);
      if (ok) {
        vcp_println("OK # %dmA current limit", npm1300_get_charging_limit());
      } else {
        vcp_println("ERROR # I/O error");
      }
    }
  } else if (strcmp(args, "BUCK PWM") == 0) {
    bool ok = npm1300_set_buck_mode(NPM1300_BUCK_MODE_PWM);
    if (ok) {
      vcp_println("OK # PWM mode set");
    } else {
      vcp_println("ERROR # I/O error");
    }
  } else if (strcmp(args, "BUCK PFM") == 0) {
    bool ok = npm1300_set_buck_mode(NPM1300_BUCK_MODE_PFM);
    if (ok) {
      vcp_println("OK # PFM mode set");
    } else {
      vcp_println("ERROR # I/O error");
    }
  } else if (strcmp(args, "BUCK AUTO") == 0) {
    bool ok = npm1300_set_buck_mode(NPM1300_BUCK_MODE_AUTO);
    if (ok) {
      vcp_println("OK # AUTO mode set");
    } else {
      vcp_println("ERROR # I/O error");
    }
  } else if (strncmp(args, "MEASURE", 7) == 0) {
    int seconds = atoi(&args[7]);
    uint32_t ticks = hal_ticks_ms();
    vcp_println(
        "time; vbat; ibat; ntc_temp; vsys; die_temp; iba_meas_status; "
        "buck_status; mode");
    do {
      npm1300_report_t report;
      bool ok = npm1300_measure_sync(&report);
      if (!ok) {
        vcp_println("ERROR # I/O error");
        break;
      }

      vcp_print("%09d; ", ticks);
      vcp_print("%d.%03d; ", (int)report.vbat,
                (int)(report.vbat * 1000) % 1000);
      vcp_print("%d.%03d; ", (int)report.ibat,
                (int)abs(report.ibat * 1000) % 1000);
      vcp_print("%d.%03d; ", (int)report.ntc_temp,
                (int)abs(report.ntc_temp * 1000) % 1000);
      vcp_print("%d.%03d; ", (int)report.vsys,
                (int)(report.vsys * 1000) % 1000);
      vcp_print("%d.%03d; ", (int)report.die_temp,
                (int)abs(report.die_temp * 1000) % 1000);
      vcp_print("%02X; ", report.ibat_meas_status);
      vcp_print("%02X; ", report.buck_status);

      bool ibat_discharging = ((report.ibat_meas_status >> 2) & 0x03) == 1;
      bool ibat_charging = ((report.ibat_meas_status >> 2) & 0x03) == 3;

      if (ibat_discharging) {
        vcp_print("DISCHARGING");
      } else if (ibat_charging) {
        vcp_print("CHARGING");
      } else {
        vcp_print("IDLE");
      }

      vcp_println("");

      while (!ticks_expired(ticks + 1000)) {
      };

      ticks += 1000;

    } while (seconds-- > 0);

    vcp_println("OK # Measurement finished");
  }
}
#endif  // USE_POWERCTL

#ifdef USE_POWERCTL
void test_wpc(const char *args) {
  stwlc38_init();

  if (strcmp(args, "UPDATE") == 0) {
    vcp_println("Trying to update STWLC38 ... ");

    uint32_t update_time_ms = systick_ms();
    bool status = stwlc38_patch_and_config();
    update_time_ms = systick_ms() - update_time_ms;

    if (status == false) {
      vcp_println("ERROR # Some problem occured");
    } else {
      vcp_println("WPC update completed {%d ms}", update_time_ms);
      vcp_println("OK");
    }

  } else if (strcmp(args, "CHIP_INFO") == 0) {
    stwlc38_chip_info_t chip_info;

    if (!stwlc38_read_chip_info(&chip_info)) {
      vcp_println("ERROR # STWLC38 not initialized");
      return;
    }

    vcp_println("chip_id  0x%d", chip_info.chip_id);
    vcp_println("chip_rev 0x%d ", chip_info.chip_rev);
    vcp_println("cust_id  0x%d ", chip_info.cust_id);
    vcp_println("rom_id   0x%X ", chip_info.rom_id);
    vcp_println("patch_id 0x%X ", chip_info.patch_id);
    vcp_println("cfg_id   0x%X ", chip_info.cfg_id);
    vcp_println("pe_id    0x%X ", chip_info.pe_id);
    vcp_println("op_mode  0x%X ", chip_info.op_mode);

    vcp_print("device_id : ");
    for (uint8_t i = 0; i < sizeof(chip_info.device_id); i++) {
      vcp_print("%x", chip_info.device_id[i]);
    }
    vcp_println("");

    vcp_println("sys_err  0x%X ", chip_info.sys_err);
    vcp_println(" - core_hard_fault:   0x%X ", chip_info.core_hard_fault);
    vcp_println(" - nvm_ip_err:        0x%X ", chip_info.nvm_ip_err);
    vcp_println(" - nvm_boot_err:      0x%X ", chip_info.nvm_boot_err);
    vcp_println(" - nvm_pe_error:      0x%X ", chip_info.nvm_pe_error);
    vcp_println(" - nvm_config_err:    0x%X ", chip_info.nvm_config_err);
    vcp_println(" - nvm_patch_err:     0x%X ", chip_info.nvm_patch_err);
    vcp_println(" - nvm_prod_info_err: 0x%X ", chip_info.nvm_prod_info_err);

    vcp_println("OK");

  } else if (strcmp(args, "EN") == 0) {
    if (!stwlc38_enable(true)) {
      vcp_println("ERROR # STWLC38 not initialized");
      return;
    }
    vcp_println("OK");
  } else if (strcmp(args, "DIS") == 0) {
    if (!stwlc38_enable(false)) {
      vcp_println("ERROR # STWLC38 not initialized");
      return;
    }
    vcp_println("OK");
  } else if (strcmp(args, "VEN") == 0) {
    if (!stwlc38_enable_vout(true)) {
      vcp_println("ERROR # STWLC38 not initialized");
      return;
    }
    vcp_println("OK");
  } else if (strcmp(args, "VDIS") == 0) {
    if (!stwlc38_enable_vout(false)) {
      vcp_println("ERROR # STWLC38 not initialized");
      return;
    }
    vcp_println("OK");
  } else if (strncmp(args, "MEASURE", 7) == 0) {
    stwlc38_report_t report;

    int seconds = atoi(&args[7]);
    uint32_t ticks = hal_ticks_ms();

    vcp_println(
        "time; ready; vout_ready; vrect; vout; icur; tmeas; opfreq; ntc");
    do {
      if (!stwlc38_get_report(&report)) {
        vcp_println("ERROR # STWLC38 not initialized");
        return;
      } else {
        vcp_print("%09d; ", ticks);
        vcp_print("%d; ", report.ready ? 1 : 0);
        vcp_print("%d; ", report.vout_ready ? 1 : 0);
        vcp_print("%d.%03d; ", (int)report.vrect,
                  (int)abs(report.vrect * 1000) % 1000);
        vcp_print("%d.%03d; ", (int)report.vout,
                  (int)(report.vout * 1000) % 1000);
        vcp_print("%d.%03d; ", (int)report.icur,
                  (int)abs(report.icur * 1000) % 1000);
        vcp_print("%d.%03d; ", (int)report.tmeas,
                  (int)abs(report.tmeas * 1000) % 1000);
        vcp_print("%d; ", report.opfreq);
        vcp_print("%d.%03d; ", (int)report.ntc,
                  (int)abs(report.ntc * 1000) % 1000);

        vcp_println("");
      }

      while (!ticks_expired(ticks + 1000)) {
      };

      ticks += 1000;

    } while (seconds-- > 0);

    vcp_println("OK # Measurement finished");
  }
}
#endif  // USE_POWERCTL

#ifdef USE_POWERCTL
void test_suspend(void) {
  vcp_println("# Going to suspend mode (press power button to resume)");
  systick_delay_ms(500);

  powerctl_suspend();

  systick_delay_ms(1500);
  vcp_println("OK # Resumed");
}
#endif  // USE_POWERCTL

#define BACKLIGHT_NORMAL 150

int main(void) {
  system_init(&rsod_panic_handler);

#ifdef USE_POWERCTL
  npm1300_init();
#endif

  display_init(DISPLAY_JUMP_BEHAVIOR);

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
  usb_init_all();

  uint32_t bootloader_version = read_bootloader_version();
  const boardloader_version_t *boardloader_version = read_boardloader_version();

#ifdef USE_OPTIGA
  optiga_init();
  optiga_open_application();
  pair_optiga();
#endif

  gfx_clear();
  draw_welcome_screen();

  char dom[32];
  // format: {MODEL_IDENTIFIER}-YYMMDD
  if (sectrue == flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, (uint8_t *)dom, 32) &&
      sectrue == startswith(dom, MODEL_IDENTIFIER) && dom[31] == 0) {
    gfx_offset_t pos;

    pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2);
    gfx_draw_qrcode(pos, 4, dom);

    pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY - 30);
    gfx_draw_text(pos, dom + 8, -1, &bold, GFX_ALIGN_CENTER);

    display_refresh();
  }

  display_fade(0, BACKLIGHT_NORMAL, 1000);

  char line[2048];  // expecting hundreds of bytes represented as hexadecimal
                    // characters

  for (;;) {
    vcp_readline(line, sizeof(line));

    if (startswith(line, "PING")) {
      vcp_println("OK");

    } else if (startswith(line, "CPUID READ")) {
      cpuid_read();

    } else if (startswith(line, "BORDER")) {
      test_border();

    } else if (startswith(line, "DISP ")) {
      test_display(line + 5);
#ifdef USE_BUTTON
    } else if (startswith(line, "BUTTON ")) {
      test_button(line + 7);
#endif
#ifdef USE_TOUCH
    } else if (startswith(line, "TOUCH VERSION")) {
      touch_version();

    } else if (startswith(line, "TOUCH ")) {
      test_touch(line + 6);

    } else if (startswith(line, "TOUCH_CUSTOM ")) {
      test_touch_custom(line + 13);

    } else if (startswith(line, "TOUCH_IDLE ")) {
      test_touch_idle(line + 11);

    } else if (startswith(line, "TOUCH_POWER ")) {
      test_touch_power(line + 12);

    } else if (startswith(line, "SENS ")) {
      test_sensitivity(line + 5);

#endif
    } else if (startswith(line, "PWM ")) {
      test_pwm(line + 4);
#ifdef USE_SD_CARD
    } else if (startswith(line, "SD")) {
      test_sd();
#endif
#ifdef USE_SBU
    } else if (startswith(line, "SBU ")) {
      test_sbu(line + 4);
#endif
#ifdef USE_HAPTIC
    } else if (startswith(line, "HAPTIC ")) {
      test_haptic(line + 7);
#endif
#ifdef USE_OPTIGA
    } else if (startswith(line, "OPTIGAID READ")) {
      optigaid_read();
    } else if (startswith(line, "CERTINF READ")) {
      cert_read(OID_CERT_INF);
    } else if (startswith(line, "CERTDEV WRITE ")) {
      cert_write(OID_CERT_DEV, line + 14);
    } else if (startswith(line, "CERTDEV READ")) {
      cert_read(OID_CERT_DEV);
    } else if (startswith(line, "CERTFIDO WRITE ")) {
      cert_write(OID_CERT_FIDO, line + 15);
    } else if (startswith(line, "CERTFIDO READ")) {
      cert_read(OID_CERT_FIDO);
    } else if (startswith(line, "KEYFIDO WRITE ")) {
      keyfido_write(line + 14);
    } else if (startswith(line, "KEYFIDO READ")) {
      pubkey_read(OID_KEY_FIDO);
    } else if (startswith(line, "LOCK")) {
      optiga_lock();
    } else if (startswith(line, "CHECK LOCKED")) {
      check_locked();
    } else if (startswith(line, "SEC READ")) {
      sec_read();

#endif

    } else if (startswith(line, "OTP READ")) {
      test_otp_read();

    } else if (startswith(line, "OTP WRITE ")) {
      test_otp_write(line + 10);

    } else if (startswith(line, "VARIANT READ")) {
      test_otp_read_device_variant();

    } else if (startswith(line, "VARIANT ")) {
      test_otp_write_device_variant(line + 8);

    } else if (startswith(line, "FIRMWARE VERSION")) {
      test_firmware_version();
    } else if (startswith(line, "BOOTLOADER VERSION")) {
      test_bootloader_version(bootloader_version);
    } else if (startswith(line, "BOARDLOADER VERSION")) {
      test_boardloader_version(boardloader_version);
    } else if (startswith(line, "WIPE")) {
      test_wipe();
    } else if (startswith(line, "REBOOT")) {
      test_reboot();
#ifdef USE_POWERCTL
    } else if (startswith(line, "PMIC ")) {
      test_pmic(line + 5);
    } else if (startswith(line, "WPC ")) {
      test_wpc(line + 4);
    } else if (startswith(line, "SUSPEND")) {
      test_suspend();
#endif
    } else {
      vcp_println("UNKNOWN");
    }
  }

  return 0;
}
