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

#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include STM32_HAL_H

#include "button.h"
#include "common.h"
#include "display.h"
#include "flash.h"
#include "i2c.h"
#include "mini_printf.h"
#include "model.h"
#include "mpu.h"
#include "random_delays.h"
#include "rng.h"
#include "sbu.h"
#include "sdcard.h"
#include "secbool.h"
#include "secret.h"
#include "touch.h"
#include "usb.h"

#ifdef USE_OPTIGA
#include "aes/aes.h"
#include "ecdsa.h"
#include "nist256p1.h"
#include "optiga_commands.h"
#include "optiga_hal.h"
#include "optiga_transport.h"
#include "rand.h"
#include "sha2.h"
#endif

#include "memzero.h"
#include "stm32f4xx_ll_utils.h"

#ifdef TREZOR_MODEL_T
#define MODEL_IDENTIFIER "TREZOR2-"
#elif TREZOR_MODEL_R
#define MODEL_IDENTIFIER "T2B1-"
#endif

enum { VCP_IFACE = 0x00 };

static secbool startswith(const char *s, const char *prefix) {
  return sectrue * (0 == strncmp(s, prefix, strlen(prefix)));
}

static void vcp_intr(void) {
  display_clear();
  ensure(secfalse, "vcp_intr");
}

static void vcp_puts(const char *s, size_t len) {
  int r = usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)s, len, -1);
  (void)r;
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

static void vcp_print(const char *fmt, ...) {
  static char buf[128];
  va_list va;
  va_start(va, fmt);
  int r = mini_vsnprintf(buf, sizeof(buf), fmt, va);
  va_end(va);
  vcp_puts(buf, r);
}

static void vcp_println(const char *fmt, ...) {
  static char buf[128];
  va_list va;
  va_start(va, fmt);
  int r = mini_vsnprintf(buf, sizeof(buf), fmt, va);
  va_end(va);
  vcp_puts(buf, r);
  vcp_puts("\r\n", 2);
}

static void vcp_println_hex(uint8_t *data, uint16_t len) {
  for (int i = 0; i < len; i++) {
    vcp_print("%02X", data[i]);
  }
  vcp_puts("\r\n", 2);
}

#ifdef USE_OPTIGA
static secbool is_optiga_locked(void);

static uint16_t get_byte_from_hex(const char **hex) {
  uint8_t result = 0;

  // Skip whitespace.
  while (**hex == ' ') {
    *hex += 1;
  }

  for (int i = 0; i < 2; i++) {
    result <<= 4;
    char c = **hex;
    if (c >= '0' && c <= '9') {
      result |= c - '0';
    } else if (c >= 'A' && c <= 'F') {
      result |= c - 'A' + 10;
    } else if (c >= 'a' && c <= 'f') {
      result |= c - 'a' + 10;
    } else if (c == '\0') {
      return 0x100;
    } else {
      return 0xFFFF;
    }
    *hex += 1;
  }
  return result;
}

static int get_from_hex(uint8_t *buf, uint16_t buf_len, const char *hex) {
  int len = 0;
  uint16_t b = get_byte_from_hex(&hex);
  for (len = 0; len < buf_len && b <= 0xff; ++len) {
    buf[len] = b;
    b = get_byte_from_hex(&hex);
  }

  if (b == 0x100) {
    // Success.
    return len;
  }

  if (b > 0xff) {
    // Non-hexadecimal character.
    return -1;
  }

  // Buffer too small.
  return -2;
}
#endif

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
      .manufacturer = "SatoshiLabs",
      .product = "TREZOR",
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
      .ep_cmd = 0x82,
      .ep_in = 0x81,
      .ep_out = 0x01,
      .polling_interval = 10,
      .max_packet_len = VCP_PACKET_LEN,
  };

  usb_init(&dev_info);
  ensure(usb_vcp_add(&vcp_info), "usb_vcp_add");
  usb_start();
}

static void draw_border(int width, int padding) {
  const int W = width, P = padding, RX = DISPLAY_RESX, RY = DISPLAY_RESY;
  display_clear();
  display_bar(P, P, RX - 2 * P, RY - 2 * P, 0xFFFF);
  display_bar(P + W, P + W, RX - 2 * (P + W), RY - 2 * (P + W), 0x0000);
  display_refresh();
}

static void test_border(void) {
  draw_border(2, 0);
  vcp_println("OK");
}

static void test_display(const char *colors) {
  display_clear();

  size_t l = strlen(colors);
  size_t w = DISPLAY_RESX / l;

  for (size_t i = 0; i < l; i++) {
    uint16_t c = 0x0000;  // black
    switch (colors[i]) {
      case 'R':
        c = 0xF800;
        break;
      case 'G':
        c = 0x07E0;
        break;
      case 'B':
        c = 0x001F;
        break;
      case 'W':
        c = 0xFFFF;
        break;
    }
    display_bar(i * w, 0, i * w + w, DISPLAY_RESY, c);
  }
  display_refresh();
  vcp_println("OK");
}

#ifdef USE_BUTTON

static secbool test_btn_press(uint32_t deadline, uint32_t btn) {
  while (button_read() != (btn | BTN_EVT_DOWN)) {
    if (HAL_GetTick() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }
  while (button_read() != (btn | BTN_EVT_UP)) {
    if (HAL_GetTick() > deadline) {
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
    uint32_t buttons = button_read();
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
    if (HAL_GetTick() > deadline) {
      vcp_println("ERROR TIMEOUT");
      return secfalse;
    }
  }

  while (true) {
    uint32_t buttons = button_read();
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
    if (HAL_GetTick() > deadline) {
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
    uint32_t deadline = HAL_GetTick() + timeout * 1000;
    secbool r = test_btn_press(deadline, BTN_LEFT);
    if (r == sectrue) vcp_println("OK");
  }

  if (startswith(args, "RIGHT ")) {
    timeout = args[6] - '0';
    uint32_t deadline = HAL_GetTick() + timeout * 1000;
    secbool r = test_btn_press(deadline, BTN_RIGHT);
    if (r == sectrue) vcp_println("OK");
  }

  if (startswith(args, "BOTH ")) {
    timeout = args[5] - '0';
    uint32_t deadline = HAL_GetTick() + timeout * 1000;
    secbool r = test_btn_all(deadline);
    if (r == sectrue) vcp_println("OK");
  }
}

#endif

#ifdef USE_TOUCH
static secbool touch_click_timeout(uint32_t *touch, uint32_t timeout_ms) {
  uint32_t deadline = HAL_GetTick() + timeout_ms;
  uint32_t r = 0;

  while (touch_read())
    ;
  while ((touch_read() & TOUCH_START) == 0) {
    if (HAL_GetTick() > deadline) return secfalse;
  }
  while (((r = touch_read()) & TOUCH_END) == 0) {
    if (HAL_GetTick() > deadline) return secfalse;
  }
  while (touch_read())
    ;

  *touch = r;
  return sectrue;
}

static void test_touch(const char *args) {
  int column = args[0] - '0';
  int timeout = args[1] - '0';

  display_clear();
  switch (column) {
    case 1:
      display_bar(0, 0, 120, 120, 0xFFFF);
      break;
    case 2:
      display_bar(120, 0, 120, 120, 0xFFFF);
      break;
    case 3:
      display_bar(120, 120, 120, 120, 0xFFFF);
      break;
    default:
      display_bar(0, 120, 120, 120, 0xFFFF);
      break;
  }
  display_refresh();

  touch_power_on();

  uint32_t evt = 0;
  if (touch_click_timeout(&evt, timeout * 1000)) {
    uint16_t x = touch_unpack_x(evt);
    uint16_t y = touch_unpack_y(evt);
    vcp_println("OK %d %d", x, y);
  } else {
    vcp_println("ERROR TIMEOUT");
  }
  display_clear();
  display_refresh();

  touch_power_off();
}

static void test_sensitivity(const char *args) {
  int v = atoi(args);

  touch_power_on();
  touch_sensitivity(v & 0xFF);

  display_clear();
  display_refresh();

  for (;;) {
    uint32_t evt = touch_read();
    if (evt & TOUCH_START || evt & TOUCH_MOVE) {
      int x = touch_unpack_x(evt);
      int y = touch_unpack_y(evt);
      display_clear();
      display_bar(x - 48, y - 48, 96, 96, 0xFFFF);
      display_refresh();
    } else if (evt & TOUCH_END) {
      display_clear();
      display_refresh();
    }
  }

  touch_power_off();
}
#endif

static void test_pwm(const char *args) {
  int v = atoi(args);

  display_backlight(v);
  display_refresh();
  vcp_println("OK");
}

#ifdef USE_SD_CARD
static void test_sd(void) {
#define BLOCK_SIZE (32 * 1024)
  static uint32_t buf1[BLOCK_SIZE / sizeof(uint32_t)];
  static uint32_t buf2[BLOCK_SIZE / sizeof(uint32_t)];

  if (sectrue != sdcard_is_present()) {
    vcp_println("ERROR NOCARD");
    return;
  }

  ensure(sdcard_power_on(), NULL);
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
    HAL_Delay(1000);
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

static void test_wipe(void) {
  // erase start of the firmware (metadata) -> invalidate FW
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < 1024 / sizeof(uint32_t); i++) {
    ensure(
        flash_area_write_word(&FIRMWARE_AREA, i * sizeof(uint32_t), 0x00000000),
        NULL);
  }
  ensure(flash_lock_write(), NULL);
  display_clear();
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY / 2 + 10, "WIPED", -1,
                      FONT_BOLD, COLOR_WHITE, COLOR_BLACK);
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

static void test_otp_read(void) {
  uint8_t data[32];
  memzero(data, sizeof(data));
  ensure(flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, data, sizeof(data)), NULL);

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
  char data[32];
  memzero(data, sizeof(data));
  strncpy(data, args, sizeof(data) - 1);
  ensure(flash_otp_write(FLASH_OTP_BLOCK_BATCH, 0, (const uint8_t *)data,
                         sizeof(data)),
         NULL);
  ensure(flash_otp_lock(FLASH_OTP_BLOCK_BATCH), NULL);
  vcp_println("OK");
}

static void test_otp_write_device_variant(const char *args) {
#ifdef USE_OPTIGA
  if (sectrue != is_optiga_locked()) {
    vcp_println("ERROR NOT LOCKED");
    return;
  }
#endif

  volatile char data[32];
  memzero((char *)data, sizeof(data));
  data[0] = 1;

  int arg_start = 0;
  int arg_num = 1;
  int arg_len = 0;
  int n = 0;
  while (args[n] != 0) {
    if (args[n] == ' ') {
      if (arg_len != 0) {
        if (arg_num < 32) {
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

  if (arg_len != 0 && arg_num < 32) {
    data[arg_num] = (uint8_t)atoi(&args[arg_start]);
  }

  ensure(flash_otp_write(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0,
                         (const uint8_t *)data, sizeof(data)),
         NULL);
  ensure(flash_otp_lock(FLASH_OTP_BLOCK_DEVICE_VARIANT), NULL);
  vcp_println("OK");
}

void cpuid_read(void) {
  uint32_t cpuid[3];
  cpuid[0] = LL_GetUID_Word0();
  cpuid[1] = LL_GetUID_Word1();
  cpuid[2] = LL_GetUID_Word2();

  vcp_print("OK ");
  vcp_println_hex((uint8_t *)cpuid, sizeof(cpuid));
}

#ifdef USE_OPTIGA
static const uint16_t OID_CERT_INF = 0xE0E0;
static const uint16_t OID_CERT_DEV = 0xE0E1;
static const uint16_t OID_CERT_FIDO = 0xE0E2;
static const uint16_t OID_KEY_DEV = 0xE0F0;
static const uint16_t OID_KEY_FIDO = 0xE0F2;
static const uint16_t OID_KEY_PAIRING = 0xE140;
static const uint16_t OID_OPTIGA_UID = 0xE0C2;

static bool set_metadata(uint16_t oid, const optiga_metadata *metadata) {
  uint8_t serialized[258] = {0};
  size_t size = 0;
  optiga_result ret = optiga_serialize_metadata(metadata, serialized,
                                                sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_serialize_metadata error %d for OID 0x%04x.", ret,
                oid);
    return false;
  }

  optiga_set_data_object(oid, true, serialized, size);

  ret =
      optiga_get_data_object(oid, true, serialized, sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_metadata error %d for OID 0x%04x.", ret, oid);
    return false;
  }

  optiga_metadata metadata_stored = {0};
  ret = optiga_parse_metadata(serialized, size, &metadata_stored);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_parse_metadata error %d.", ret);
    return false;
  }

  if (!optiga_compare_metadata(metadata, &metadata_stored)) {
    vcp_println("ERROR optiga_compare_metadata failed.");
    return false;
  }

  return true;
}

static bool pair_optiga(void) {
  // The pairing key may already be written and locked. The success of the
  // pairing procedure is determined by optiga_sec_chan_handshake(). Therefore
  // it is OK for some of the intermediate operations to fail.

  // Enable writing the pairing secret to OPTIGA.
  optiga_metadata metadata = {0};
  metadata.change = OPTIGA_ACCESS_ALWAYS;
  set_metadata(OID_KEY_PAIRING, &metadata);  // Ignore result.

  // Generate pairing secret.
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  optiga_result ret = optiga_get_random(secret, sizeof(secret));
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_random error %d,", ret);
    return false;
  }

  // Store pairing secret.
  ret = optiga_set_data_object(OID_KEY_PAIRING, false, secret, sizeof(secret));
  /*
   * TODO: Uncomment. Right now this code will render the device unusable with
   * unofficial firmware. We need to be able to call AttestationDelete before
   * this code is enabled.
   *
  if (OPTIGA_SUCCESS == ret) {
    secret_erase();
    secret_write_header();
    secret_write(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
  }

  // Verify whether the secret was stored correctly in flash and OPTIGA.
  memzero(secret, sizeof(secret));
  if (secret_read(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN) !=
      sectrue) {
    vcp_println("ERROR Failed to read pairing secret.");
    return false;
  }
  */

  ret = optiga_sec_chan_handshake(secret, sizeof(secret));
  memzero(secret, sizeof(secret));
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_sec_chan_handshake error %d.", ret);
    return false;
  }

  return true;
}

static void optiga_lock(void) {
  if (!pair_optiga()) {
    return;
  }

  // Delete trust anchor.
  optiga_result ret =
      optiga_set_data_object(0xe0e8, false, (const uint8_t *)"\0", 1);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_data error %d for 0xe0e8.", ret);
    return;
  }

  // Set data object metadata.
  static const optiga_metadata_item ACCESS_PAIRED = {
      (const uint8_t *)"\x20\xE1\x40", 3};
  static const optiga_metadata_item KEY_USE_SIGN = {(const uint8_t *)"\x10", 1};
  static const optiga_metadata_item TYPE_PTFBIND = {(const uint8_t *)"\x22", 1};
  optiga_metadata metadata = {0};

  // Set metadata for device certificate.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  if (!set_metadata(OID_CERT_DEV, &metadata)) {
    return;
  }

  // Set metadata for FIDO attestation certificate.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  if (!set_metadata(OID_CERT_FIDO, &metadata)) {
    return;
  }

  // Set metadata for device private key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(OID_KEY_DEV, &metadata)) {
    return;
  }

  // Set metadata for FIDO attestation private key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(OID_KEY_FIDO, &metadata)) {
    return;
  }

  // Set metadata for pairing key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  metadata.data_type = TYPE_PTFBIND;
  if (!set_metadata(OID_KEY_PAIRING, &metadata)) {
    return;
  }

  vcp_println("OK");
}

static secbool is_optiga_locked(void) {
  const uint16_t oids[] = {OID_CERT_DEV, OID_CERT_FIDO, OID_KEY_DEV,
                           OID_KEY_FIDO, OID_KEY_PAIRING};

  optiga_metadata locked_metadata = {0};
  locked_metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  for (size_t i = 0; i < sizeof(oids) / sizeof(oids[0]); ++i) {
    uint8_t metadata_buffer[258] = {0};
    size_t metadata_size = 0;
    optiga_result ret =
        optiga_get_data_object(oids[i], true, metadata_buffer,
                               sizeof(metadata_buffer), &metadata_size);
    if (OPTIGA_SUCCESS != ret) {
      vcp_println("ERROR optiga_get_metadata error %d for OID 0x%04x.", ret,
                  oids[i]);
      return secfalse;
    }

    optiga_metadata stored_metadata = {0};
    ret =
        optiga_parse_metadata(metadata_buffer, metadata_size, &stored_metadata);
    if (OPTIGA_SUCCESS != ret) {
      vcp_println("ERROR optiga_parse_metadata error %d.", ret);
      return secfalse;
    }

    if (!optiga_compare_metadata(&locked_metadata, &stored_metadata)) {
      return secfalse;
    }
  }

  return sectrue;
}

static void optigaid_read(void) {
  uint8_t optiga_id[27] = {0};
  size_t optiga_id_size = 0;

  optiga_result ret = optiga_get_data_object(
      OID_OPTIGA_UID, false, optiga_id, sizeof(optiga_id), &optiga_id_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_data_object error %d for 0x%04x.", ret,
                OID_OPTIGA_UID);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(optiga_id, optiga_id_size);
}

static void cert_read(uint16_t oid) {
  uint8_t cert[1024] = {0};
  size_t cert_size = 0;
  optiga_result ret =
      optiga_get_data_object(oid, false, cert, sizeof(cert), &cert_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_data_object error %d for 0x%04x.", ret, oid);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(cert, cert_size);
}

static void cert_write(uint16_t oid, char *data) {
  // Enable writing to the certificate slot.
  optiga_metadata metadata = {0};
  metadata.change = OPTIGA_ACCESS_ALWAYS;
  set_metadata(oid, &metadata);  // Ignore result.

  uint8_t data_bytes[1024];

  int len = get_from_hex(data_bytes, sizeof(data_bytes), data);
  if (len < 0) {
    vcp_println("ERROR Hexadecimal decoding error %d.", len);
    return;
  }

  optiga_result ret = optiga_set_data_object(oid, false, data_bytes, len);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_data error %d for 0x%04x.", ret, oid);
    return;
  }

  vcp_println("OK");
}

static void pubkey_read(uint16_t oid) {
  // Enable key agreement usage.

  optiga_metadata metadata = {0};
  uint8_t key_usage = OPTIGA_KEY_USAGE_KEYAGREE;
  metadata.key_usage.ptr = &key_usage;
  metadata.key_usage.len = 1;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;

  if (!set_metadata(oid, &metadata)) {
    return;
  }

  // Execute ECDH with base point to get the x-coordinate of the public key.
  static const uint8_t BASE_POINT[] = {
      0x03, 0x42, 0x00, 0x04, 0x6b, 0x17, 0xd1, 0xf2, 0xe1, 0x2c, 0x42, 0x47,
      0xf8, 0xbc, 0xe6, 0xe5, 0x63, 0xa4, 0x40, 0xf2, 0x77, 0x03, 0x7d, 0x81,
      0x2d, 0xeb, 0x33, 0xa0, 0xf4, 0xa1, 0x39, 0x45, 0xd8, 0x98, 0xc2, 0x96,
      0x4f, 0xe3, 0x42, 0xe2, 0xfe, 0x1a, 0x7f, 0x9b, 0x8e, 0xe7, 0xeb, 0x4a,
      0x7c, 0x0f, 0x9e, 0x16, 0x2b, 0xce, 0x33, 0x57, 0x6b, 0x31, 0x5e, 0xce,
      0xcb, 0xb6, 0x40, 0x68, 0x37, 0xbf, 0x51, 0xf5};
  uint8_t public_key[32] = {0};
  size_t public_key_size = 0;
  optiga_result ret = optiga_calc_ssec(
      OPTIGA_CURVE_P256, OID_KEY_DEV, BASE_POINT, sizeof(BASE_POINT),
      public_key, sizeof(public_key), &public_key_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_calc_ssec error %d.", ret);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(public_key, public_key_size);
}

static void keyfido_write(char *data) {
  static const size_t EPH_PUB_KEY_SIZE = 33;
  static const size_t PAYLOAD_SIZE = 32;
  static const size_t CIPHERTEXT_OFFSET = EPH_PUB_KEY_SIZE;
  static const size_t EXPECTED_SIZE = EPH_PUB_KEY_SIZE + PAYLOAD_SIZE;

  // Enable key agreement usage for device key.

  optiga_metadata metadata = {0};
  uint8_t key_usage = OPTIGA_KEY_USAGE_KEYAGREE;
  metadata.key_usage.ptr = &key_usage;
  metadata.key_usage.len = 1;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;

  if (!set_metadata(OID_KEY_DEV, &metadata)) {
    return;
  }

  // Read encrypted FIDO attestation private key.

  uint8_t data_bytes[EXPECTED_SIZE];
  int len = get_from_hex(data_bytes, sizeof(data_bytes), data);
  if (len < 0) {
    vcp_println("ERROR Hexadecimal decoding error %d.", len);
    return;
  }

  if (len != EXPECTED_SIZE) {
    vcp_println("ERROR Unexpected input length.");
    return;
  }

  // Expand sender's ephemeral public key.
  curve_point pub = {0};
  if (0 == ecdsa_read_pubkey(&nist256p1, data_bytes, &pub)) {
    vcp_println("ERROR Failed to decode public key.");
    return;
  }
  uint8_t public_key[4 + 64] = {0x03, 0x42, 0x00, 0x04};
  bn_write_be(&pub.x, public_key + 4);
  bn_write_be(&pub.y, public_key + 4 + 32);

  // Execute ECDH with device private key.
  uint8_t secret[32] = {0};
  size_t secret_size = 0;
  optiga_result ret = optiga_calc_ssec(OPTIGA_CURVE_P256, OID_KEY_DEV,
                                       public_key, sizeof(public_key), secret,
                                       sizeof(secret), &secret_size);
  if (OPTIGA_SUCCESS != ret) {
    memzero(secret, sizeof(secret));
    vcp_println("ERROR optiga_calc_ssec error %d.", ret);
    return;
  }

  // Hash the shared secret. Use the result as the decryption key.
  sha256_Raw(secret, secret_size, secret);
  aes_decrypt_ctx ctx = {0};
  AES_RETURN aes_ret = aes_decrypt_key256(secret, &ctx);
  if (EXIT_SUCCESS != aes_ret) {
    vcp_println("ERROR aes_decrypt_key256 error.");
    memzero(&ctx, sizeof(ctx));
    memzero(secret, sizeof(secret));
    return;
  }

  // Decrypt the FIDO attestation key.
  uint8_t fido_key[32] = {0};

  // The IV is intentionally all-zero, which is not a problem, because the
  // encryption key is unique for each ciphertext.
  uint8_t iv[AES_BLOCK_SIZE] = {0};
  aes_ret = aes_cbc_decrypt(&data_bytes[CIPHERTEXT_OFFSET], fido_key,
                            sizeof(fido_key), iv, &ctx);
  memzero(&ctx, sizeof(ctx));
  memzero(secret, sizeof(secret));
  if (EXIT_SUCCESS != aes_ret) {
    memzero(fido_key, sizeof(fido_key));
    vcp_println("ERROR aes_cbc_decrypt error.");
    return;
  }

  // Write trust anchor certificate to OID 0xE0E8
  ret = optiga_set_trust_anchor();
  if (OPTIGA_SUCCESS != ret) {
    memzero(fido_key, sizeof(fido_key));
    vcp_println("ERROR optiga_set_trust_anchor error %d.", ret);
    return;
  }

  // Set change access condition for the FIDO key to Int(0xE0E8), so that we
  // can write the FIDO key using the trust anchor in OID 0xE0E8.
  memzero(&metadata, sizeof(metadata));
  metadata.change.ptr = (const uint8_t *)"\x21\xe0\xe8";
  metadata.change.len = 3;
  if (!set_metadata(OID_KEY_FIDO, &metadata)) {
    return;
  }

  // Store the FIDO attestation key.
  ret = optiga_set_priv_key(OID_KEY_FIDO, fido_key);
  memzero(fido_key, sizeof(fido_key));
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_priv_key error %d.", ret);
    return;
  }

  vcp_println("OK");
}

#endif

#define BACKLIGHT_NORMAL 150

int main(void) {
  display_orientation(0);
  random_delays_init();
#ifdef USE_SD_CARD
  sdcard_init();
#endif
#ifdef USE_BUTTON
  button_init();
#endif
#ifdef USE_I2C
  i2c_init();
#endif
#ifdef USE_TOUCH
  touch_init();
#endif
#ifdef USE_SBU
  sbu_init();
#endif
  usb_init_all();

#ifdef USE_OPTIGA
  optiga_init();
  optiga_open_application();
#endif

  display_reinit();

  mpu_config_prodtest();
  drop_privileges();

  display_clear();
  draw_border(1, 3);

  char dom[32];
  // format: TREZOR2-YYMMDD
  if (sectrue == flash_otp_read(FLASH_OTP_BLOCK_BATCH, 0, (uint8_t *)dom, 32) &&
      sectrue == startswith(dom, MODEL_IDENTIFIER) && dom[31] == 0) {
    display_qrcode(DISPLAY_RESX / 2, DISPLAY_RESY / 2, dom, 4);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 30, dom + 8, -1,
                        FONT_BOLD, COLOR_WHITE, COLOR_BLACK);
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
    } else if (startswith(line, "TOUCH ")) {
      test_touch(line + 6);

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

#endif

    } else if (startswith(line, "OTP READ")) {
      test_otp_read();

    } else if (startswith(line, "OTP WRITE ")) {
      test_otp_write(line + 10);

    } else if (startswith(line, "VARIANT ")) {
      test_otp_write_device_variant(line + 8);

    } else if (startswith(line, "WIPE")) {
      test_wipe();

    } else {
      vcp_println("UNKNOWN");
    }
  }

  return 0;
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR!", "(HF)"); }
