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

#ifdef USE_NFC
#include <trezor_rtl.h>

#include <io/nfc.h>
#include <rtl/cli.h>
#include <stdlib.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>

#include "prodtest_error_codes.h"
#include "src/utils/noise.h"

static nfc_dev_info_t dev_info = {0};
static uint8_t cli_cmd_byte_idx = 0;
static uint8_t cli_cmd_byte_buf[256] = {0};

static const uint8_t aid_select_ndef_app[] = {0xd2, 0x76, 0x00, 0x00,
                                              0x85, 0x01, 0x01};
static const uint8_t aid_select_trezor_app[] = {0xA0, 0x00, 0x00, 0x09,
                                                0x59, 0x00, 0x01};
static const uint8_t select_ndef_file[] = {0xe1, 0x04};
static const uint8_t ndef_file_header_size = 5u;

//==============================================================================
// Helper functions
//==============================================================================

static void nfc_cli_prefix(cli_t* cli) {
  cli->write(cli, ESC_COLOR_YELLOW, 5);
  cli->write(cli, "nfc-cli> ", 9);
  cli->write(cli, ESC_COLOR_RESET, 5);
}

static void nfc_cli_flush_input_console() {
  uint8_t dummy;
  while (syshandle_read(SYSHANDLE_USB_VCP, &dummy, 1) > 0) {
  }
}

#define ESC_SEQ(ch) (0x200 + (ch))
// Reads a character from the console input and return it.
// Comple escape sequences translates into ESC_SEQ values
//   - ESC[<letter> => ESC_SEQ(letter),   e.g. ESC[A => ESC_SEQ('A')
//   - ESC[<number>~ => ESC_SEQ(number) , e.g. ESC[3~ => ESC_SEQ(3)
// Reused from cli_readch() in rtl/cli.c with modifications for NFC CLI
static int nfc_cli_readch(void) {
  int esc_len = 0;   // >0 if we are in the middle of an escape sequence
  int esc_code = 0;  // numeric code of the escape sequence

  for (;;) {
    char ch;
    ssize_t len = syshandle_read(SYSHANDLE_USB_VCP, &ch, 1);

    if (len != 1) {
      return 0;
    }

    if (ch == '\e') {
      // Escape sequence start
      esc_len = 1;
    } else if (esc_len == 1) {
      if (ch == '\e') {
        return 'e';
      } else if (ch == '[') {
        // Control sequence introducer
        esc_len = 2;
        esc_code = 0;
      } else {
        esc_len = 0;
      }
    } else if (esc_len == 2 && ch >= 'A' && ch <= 'Z') {
      // XTERM sequences - ESC[<letter>
      return ESC_SEQ(ch);
    } else if (esc_len >= 2 && ch >= '0' && ch <= '9') {
      // VT sequences - ESC[<number>~
      esc_code = esc_code * 10 + (ch - '0');
      esc_len++;
    } else if (esc_len >= 3 && ch == '~') {
      // End of VT sequence
      return ESC_SEQ(esc_code);
    } else if (esc_len >= 3) {
      // Invalid VT sequence
      esc_len = 0;
    } else {
      // Non-escape character
      return ch;
    }
  }
}

static void skip_space_character(char** char_ptr) {
  while (**char_ptr == ' ') {
    (*char_ptr)++;
  }
}

static void nfc_cli_process_char(cli_t* cli, int ch) {
  switch (ch) {
    case '\r':  // ENTER key
      if (cli_cmd_byte_idx > 0) {
        uint8_t byte_array[256] = {0};
        uint8_t byte_idx = 0;
        uint32_t decoded_byte;
        char* endptr;
        char* buf_ptr = (char*)cli_cmd_byte_buf;

        do {
          skip_space_character(&buf_ptr);
          const char buf_backup = buf_ptr[2];
          buf_ptr[2] = '\0';
          decoded_byte = (uint32_t)strtoul(buf_ptr, &endptr, 16);
          buf_ptr[2] = buf_backup;

          if (endptr == buf_ptr) {
            break;
          }
          if (byte_idx >= sizeof(byte_array)) {
            cli->write(cli, "\r\n", 2);
            cli_error(cli, CLI_ERROR_INVALID_ARG, "Too many bytes in command.");
            goto clean_up;
          }

          byte_array[byte_idx++] = (uint8_t)decoded_byte;
          buf_ptr = endptr;
        } while (1);

        cli->write(cli, "\r\n", 2);
        cli_trace(cli, "Sending to NFC:");
        cli_ok_hexdata(cli, byte_array, byte_idx);

        uint8_t* apdu_resp = NULL;
        uint16_t* apdu_resp_len = NULL;
        nfc_apdu_cmd_t tx_buf = {.data = byte_array, .data_len = byte_idx};
        nfc_apdu_response_t rx_buf = {.data = &apdu_resp,
                                      .data_len = &apdu_resp_len};
        ts_t nfc_status = nfc_transceive(tx_buf, rx_buf);

        if (ts_error(nfc_status)) {
          cli_error(cli, PRODTEST_ERR_NFC_CLI_CARD_ERROR,
                    "NFC transceive failed");
        } else {
          cli_trace(cli, "Received from NFC:");
          cli_ok_hexdata(cli, apdu_resp, *apdu_resp_len);
        }

      clean_up:
        cli_cmd_byte_idx = 0;
        memset(cli_cmd_byte_buf, 0, sizeof(cli_cmd_byte_buf));
        nfc_cli_prefix(cli);
      }
      break;
    case '\b':
    case 0x7F:  // Backspace key
      if (cli_cmd_byte_idx > 0) {
        cli_cmd_byte_buf[--cli_cmd_byte_idx] = 0;
        cli->write(cli, "\e[D ", 3);
        cli->write(cli, " ", 1);
        cli->write(cli, "\e[D", 3);
      }
      break;
    default:  // Regular character + space
      if (((ch >= '0' && ch <= '9') || (ch >= 'A' && ch <= 'F') ||
           (ch >= 'a' && ch <= 'f') || (ch == ' ')) &&
          (cli_cmd_byte_idx < sizeof(cli_cmd_byte_buf))) {
        cli_cmd_byte_buf[cli_cmd_byte_idx++] = ch;
        cli->write(cli, (const char*)&ch, 1);
      }
      break;
  }
}

// clang-format off
// # | Method                                | Requires PIN | Requires Trezor |
// # | ------------------------------------- | -----------: | --------------: |
// # | check_integrity                       |           no |              no |
// # | refresh_memory                        |           no |              no |
// # | read_last_refresh_timestamp           |           no |              no |
// # | read_flash_bit_error_count            |           no |              no |
// # | wipe                                  |           no |             yes |
// # | authenticate                          |           no |             yes |
// # | set_pin                               |          yes |             yes |
// # | read_pin_counter                      |           no |              no |
// # | read_successful_access_log_record     |           no |              no |
// # | read_unsuccessful_access_log_records  |           no |              no |
// # | read_metadata                         |           no |              no |
// # | read_seed                             |          yes |             yes |
// # | write_metadata                        |          yes |             yes |
// # | write_seed                            |          yes |             yes |
// clang-format on

static ts_t nfc_select_app(cli_t* cli, const uint8_t* aid_select_app,
                           size_t aid_len) {
  uint8_t* apdu_buffer_ptr;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;

  const nfc_apdu_header_t apdu_header = {.cla = NFC_APDU_CLA_DEFAULT,
                                         .ins = NFC_APDU_INS_SELECT,
                                         .p1 = 0x04,
                                         .p2 = 0x00,
                                         .lc = aid_len,
                                         .le = 0x00,
                                         .has_lc = true,
                                         .has_le = true};

  ts_t nfc_status = nfc_compose_apdu(&apdu_header, aid_select_app,
                                     &apdu_buffer_ptr, &apdu_buffer_len);

  if (ts_ok(nfc_status)) {
    nfc_apdu_cmd_t tx_buf = {.data = apdu_buffer_ptr,
                             .data_len = apdu_buffer_len};
    nfc_apdu_response_t rx_buf = {.data = &apdu_resp,
                                  .data_len = &apdu_resp_len};
    nfc_status = nfc_transceive(tx_buf, rx_buf);
    cli_trace(cli, "nfc_select_app: stat=%d", nfc_status);
    if (ts_error(nfc_status)) {
      cli_ok_hexdata(cli, apdu_resp, *apdu_resp_len);
    }
  }
  return nfc_status;
}

static ts_t nfc_select_file(cli_t* cli, const uint8_t* select_file,
                            size_t file_len) {
  uint8_t* apdu_buffer_ptr;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;

  const nfc_apdu_header_t apdu_header = {.cla = NFC_APDU_CLA_DEFAULT,
                                         .ins = NFC_APDU_INS_SELECT,
                                         .p1 = 0x00,
                                         .p2 = 0x0C,
                                         .lc = file_len,
                                         .le = 0x00,
                                         .has_lc = true,
                                         .has_le = false};

  ts_t nfc_status = nfc_compose_apdu(&apdu_header, select_file,
                                     &apdu_buffer_ptr, &apdu_buffer_len);

  cli_ok_hexdata(cli, apdu_buffer_ptr, apdu_buffer_len);
  if (ts_ok(nfc_status)) {
    nfc_apdu_cmd_t tx_buf = {.data = apdu_buffer_ptr,
                             .data_len = apdu_buffer_len};
    nfc_apdu_response_t rx_buf = {.data = &apdu_resp,
                                  .data_len = &apdu_resp_len};
    nfc_status = nfc_transceive(tx_buf, rx_buf);
    cli_trace(cli, "nfc_select_file: stat=%d", nfc_status);
  }
  return nfc_status;
}

static ts_t nfc_read_file(cli_t* cli, uint16_t offset, uint16_t* exp_len,
                          uint8_t* read_data) {
  uint8_t* apdu_buffer_ptr;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;
  uint8_t exp_to_read = (exp_len != NULL) ? (uint8_t)*exp_len : 0;

  const nfc_apdu_header_t apdu_header = {
      .cla = NFC_APDU_CLA_DEFAULT,
      .ins = NFC_APDU_INS_READBINARY,
      .p1 = (uint8_t)((offset >> 8U) & 0xFFU),
      .p2 = (uint8_t)((offset >> 0U) & 0xFFU),
      .lc = 0x00,
      .le = exp_to_read,
      .has_lc = false,
      .has_le = true};

  ts_t nfc_status =
      nfc_compose_apdu(&apdu_header, NULL, &apdu_buffer_ptr, &apdu_buffer_len);

  cli_ok_hexdata(cli, apdu_buffer_ptr, apdu_buffer_len);
  if (ts_ok(nfc_status)) {
    nfc_apdu_cmd_t tx_buf = {.data = apdu_buffer_ptr,
                             .data_len = apdu_buffer_len};
    nfc_apdu_response_t rx_buf = {.data = &apdu_resp,
                                  .data_len = &apdu_resp_len};
    nfc_status = nfc_transceive(tx_buf, rx_buf);
    if (ts_ok(nfc_status)) {
      if (read_data != NULL) {
        memcpy(read_data, apdu_resp, *apdu_resp_len);
      }
      if (exp_len != NULL) {
        *exp_len = *apdu_resp_len;
      }
    }

    cli_trace(cli, "nfc_read_file: stat=%d, len=%d", nfc_status,
              *apdu_resp_len);
    cli_ok_hexdata(cli, apdu_resp, *apdu_resp_len);
  }
  return nfc_status;
}

//==============================================================================
//=============================================================================

static void prodtest_nfc_backup_read_ndef_cmd(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  ts_t nfc_status = nfc_init();
  if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_NDEF_CARD_INIT,
              "NFC initialization failed");
    return;
  }

  nfc_status = nfc_start_discovery();
  if (ts_eq(nfc_status, TS_ENOINIT)) {
    cli_error(cli, PRODTEST_ERR_NFC_NDEF_CARD_START, "NFC not initialized");
    goto cleanup;
  } else if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_NDEF_ACTIVATION, "NFC activation failed");
    goto cleanup;
  } else if (timeout_set) {
    cli_trace(cli, "NFC activated in reader mode for %d ms.", timeout);
  } else {
    cli_trace(cli, "NFC activated in reader mode");
  }

  // Clear leftover events
  nfc_event_t event_flag;
  nfc_get_event(&event_flag);
  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  uint32_t expire_time = ticks_timeout(timeout);
  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "NFC test aborted");
      break;
    }

    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_NDEF_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, PRODTEST_ERR_NFC_NDEF_CARD_ERROR,
                "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");

      cli_trace(cli, "Select NDEF APP");
      nfc_status = nfc_select_app(cli, &aid_select_ndef_app[0],
                                  sizeof(aid_select_ndef_app));
      if (ts_error(nfc_status)) {
        cli_trace(cli, "NFC select app failed");
        goto cleanup;
      }

      cli_trace(cli, "Select NDEF File");
      nfc_status =
          nfc_select_file(cli, &select_ndef_file[0], sizeof(select_ndef_file));
      if (ts_error(nfc_status)) {
        cli_trace(cli, "NFC select file failed");
        goto cleanup;
      }

      cli_trace(cli, "Read NDEF File length");
      uint8_t ndef_file[32];
      uint16_t ndef_file_size = 0;
      uint16_t ndef_file_len = 2u;
      nfc_status = nfc_read_file(cli, 0x00, &ndef_file_len, ndef_file);
      ndef_file_size = (ndef_file[0] << 8) | ndef_file[1];
      if (ts_error(nfc_status)) {
        cli_trace(cli, "NFC read file failed");
        goto cleanup;
      }

      cli_trace(cli, "Read NDEF File (len=%d)", ndef_file_size);
      memset(ndef_file, 0, sizeof(ndef_file));
      if (ndef_file_size > sizeof(ndef_file)) {
        cli_trace(cli, "NDEF file too big");
        goto cleanup;
      }
      nfc_status = nfc_read_file(cli, 0x02, &ndef_file_size, ndef_file);
      if (ts_error(nfc_status)) {
        cli_trace(cli, "NFC read file failed");
        goto cleanup;
      }
      cli_trace(cli, "Read NDEF-URI: %s", &ndef_file[ndef_file_header_size]);
    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      break;
    }

    systick_delay_ms(1);
  }
  cli_ok(cli, "");

cleanup:
  nfc_stop_discovery();
  nfc_deinit();
}

static void prodtest_nfc_backup_cli_cmd(cli_t* cli) {
  bool nfc_connected = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  ts_t nfc_status = nfc_init();
  if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_CLI_CARD_INIT, "NFC initialization failed");
    return;
  }

  nfc_status = nfc_start_discovery();
  if (ts_eq(nfc_status, TS_ENOINIT)) {
    cli_error(cli, PRODTEST_ERR_NFC_CLI_CARD_START, "NFC not initialized");
    goto cleanup;
  } else if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_CLI_ACTIVATION, "NFC activation failed");
    goto cleanup;
  } else {
    cli_trace(cli, "");
    cli_trace(cli,
              "NFC activated in reader mode. Read only [0-9, A-F]. Input "
              "format: <byte1>[ ]<byte2> ... E.g. \"01 ff 5aa5\"");
    cli_trace(cli, "Attach the NFC card.");
    cli_trace(cli, "");
  }

  // Clear leftover events
  nfc_event_t event_flag;
  nfc_get_event(&event_flag);
  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "NFC test aborted");
      break;
    }

    if (nfc_connected) {
      int cmd_line_char = nfc_cli_readch();
      if (cmd_line_char > 0) {
        nfc_cli_process_char(cli, cmd_line_char);
      }
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, PRODTEST_ERR_NFC_CLI_CARD_ERROR,
                "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");
      nfc_connected = true;

      nfc_cli_flush_input_console();
      nfc_cli_prefix(cli);

    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      nfc_connected = false;
      break;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_stop_discovery();
  nfc_deinit();
}

static void prodtest_nfc_backup_noise_cmd(cli_t* cli) {
  uint8_t* apdu_buffer_ptr = NULL;
  uint16_t apdu_buffer_len = 0;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;

  uint8_t request_buf[256];
  size_t request_buf_size;
  nfc_apdu_cmd_t tx_buf;
  nfc_apdu_response_t rx_buf = {.data = &apdu_resp, .data_len = &apdu_resp_len};

  uint8_t A_static_private_key[DHLEN] = {
      0x4a, 0x3f, 0x8c, 0x2e, 0x1d, 0x7b, 0x9f, 0x6a, 0x0e, 0x5c, 0x3b,
      0x8d, 0x2a, 0x4f, 0x1e, 0x7c, 0x9b, 0x6d, 0x3a, 0x0f, 0x5e, 0x8c,
      0x2b, 0x7d, 0x4a, 0x1f, 0x9e, 0x6c, 0x3b, 0x0d, 0x8a, 0x5f};

  uint8_t psk[DHLEN] = {'P', 'S', 'K', 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
                        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
                        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0};

  uint32_t timeout = 0;
  bool timeout_set = false;
  memset(&dev_info, 0, sizeof(dev_info));

  if (cli_has_arg(cli, "timeout")) {
    if (!cli_arg_uint32(cli, "timeout", &timeout)) {
      cli_error_arg(cli, "Expecting timeout argument.");
      return;
    }
    timeout_set = true;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  ts_t nfc_status = nfc_init();
  if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_NOISE_CARD_INIT,
              "NFC initialization failed");
    return;
  }

  nfc_status = nfc_start_discovery();
  if (ts_eq(nfc_status, TS_ENOINIT)) {
    cli_error(cli, PRODTEST_ERR_NFC_NOISE_CARD_START, "NFC not initialized");
    goto cleanup;
  } else if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_NOISE_ACTIVATION, "NFC activation failed");
    goto cleanup;
  } else if (timeout_set) {
    cli_trace(cli, "NFC activated in reader mode for %d ms.", timeout);
  } else {
    cli_trace(cli, "NFC activated in reader mode");
  }

  // Clear leftover events
  nfc_event_t event_flag;
  nfc_get_event(&event_flag);
  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  uint32_t expire_time = ticks_timeout(timeout);
  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "NFC test aborted");
      break;
    }

    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, PRODTEST_ERR_NFC_NOISE_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, PRODTEST_ERR_NFC_NOISE_CARD_ERROR,
                "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");
      initiator_xxpsk3_t initiator;
      noise_initiator_init(&initiator, psk, A_static_private_key);

      cli_trace(cli, "Select Trezor app");
      nfc_status = nfc_select_app(cli, &aid_select_trezor_app[0],
                                  sizeof(aid_select_trezor_app));
      if (ts_error(nfc_status)) {
        cli_trace(cli, "NFC select app failed");
        goto cleanup;
      }

      cli_trace(cli, "Handshake #1");
      nfc_status = noise_initiator_create_request1(
          &initiator, request_buf, sizeof(request_buf), &request_buf_size);
      if (ts_error(nfc_status)) {
        cli_trace(cli, "create_request1 failed: %d", nfc_status);
        goto cleanup;
      }

      nfc_apdu_header_t apdu_header = {.cla = NFC_APDU_CLA_TREZOR,
                                       .ins = NFC_APDU_INS_NOISE_1,
                                       .p1 = 0x00,
                                       .p2 = 0X00,
                                       .lc = request_buf_size,
                                       .le = 0X00,
                                       .has_lc = true,
                                       .has_le = false};
      nfc_status = nfc_compose_apdu(&apdu_header, request_buf, &apdu_buffer_ptr,
                                    &apdu_buffer_len);
      if (ts_ok(nfc_status)) {
        tx_buf.data = apdu_buffer_ptr;
        tx_buf.data_len = apdu_buffer_len;
        nfc_status = nfc_transceive(tx_buf, rx_buf);
        cli_trace(cli, "nfc_transceive: stat=%d", nfc_status);
        cli_ok_hexdata(cli, *rx_buf.data, **rx_buf.data_len);
      }
      if (ts_error(nfc_status)) {
        goto cleanup;
      }

      nfc_status = noise_initiator_handle_response1(
          &initiator, apdu_resp, *apdu_resp_len, request_buf,
          sizeof(request_buf), &request_buf_size);
      if (ts_error(nfc_status)) {
        cli_trace(cli, "handle_response1 failed: %d", nfc_status);
        goto cleanup;
      }

      cli_trace(cli, "Handshake #2");
      nfc_status = noise_initiator_create_request2(
          &initiator, request_buf, sizeof(request_buf), &request_buf_size);
      if (ts_error(nfc_status)) {
        cli_trace(cli, "create_request2 failed: %d", nfc_status);
        goto cleanup;
      }

      apdu_header.p1 = 0x01;
      apdu_header.lc = request_buf_size;
      nfc_status = nfc_compose_apdu(&apdu_header, request_buf, &apdu_buffer_ptr,
                                    &apdu_buffer_len);

      if (ts_ok(nfc_status)) {
        tx_buf.data = apdu_buffer_ptr;
        tx_buf.data_len = apdu_buffer_len;
        nfc_status = nfc_transceive(tx_buf, rx_buf);

        cli_trace(cli, "nfc_transceive: stat=%d", nfc_status);
      }
      if (ts_error(nfc_status)) {
        goto cleanup;
      }

      nfc_status = noise_initiator_handle_response2(&initiator, apdu_resp,
                                                    *apdu_resp_len);
      if (ts_ok(nfc_status)) {
        cli_ok(cli, "NFC handshake passed");
      } else {
        cli_error(cli, PRODTEST_ERR_NFC_NOISE_HANDSHAKE,
                  "NFC handshake error: err=%d", nfc_status);
      }
    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      break;
    }

    systick_delay_ms(1);
  }

cleanup:
  nfc_stop_discovery();
  nfc_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-ndef",
  .func = prodtest_nfc_backup_read_ndef_cmd,
  .info = "Read NDEF data from NFC backup card",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-cli",
  .func = prodtest_nfc_backup_cli_cmd,
  .info = "Open dedicated NFC cli for manual testing of NFC.",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-noise",
  .func = prodtest_nfc_backup_noise_cmd,
  .info = "Initiate Noise protocol handshake with NFC backup card.",
  .args = ""
);

#endif  // USE_NFC
