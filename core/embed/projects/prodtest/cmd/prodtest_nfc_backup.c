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
#include <rfal_t4t.h>
#include <rtl/cli.h>
#include <stdlib.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>
#include "rfal_nfc.h"
#include "noise_xx.h"

static nfc_dev_info_t dev_info = {0};
static uint8_t cli_cmd_byte_idx = 0;
static uint8_t cli_cmd_byte_buf[256] = {0};

static const uint8_t aid_select_ndef_app[7] = {0xd2, 0x76, 0x00, 0x00,
                                               0x85, 0x01, 0x01};

static const uint8_t select_ndef_file[2] = {0xe1, 0x04};
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
            cli_error(cli, CLI_ERROR, "Too many bytes in command.");
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
        nfc_status_t nfc_status = nfc_transceive(
            (const uint8_t*)byte_array, byte_idx, &apdu_resp, &apdu_resp_len);

        if (nfc_status != NFC_OK) {
          cli_error(cli, CLI_ERROR, "NFC transceive failed");
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

static nfc_status_t nfc_select_app(cli_t* cli, const uint8_t* aid_select_app,
                                   size_t aid_len) {
  rfalIsoDepApduBufFormat apdu_buffer;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;
  nfc_status_t nfc_status = NFC_ERROR;

  ReturnCode ret_code = rfalT4TPollerComposeSelectAppl(
      &apdu_buffer, aid_select_app, aid_len, &apdu_buffer_len);

  if (ret_code == RFAL_ERR_NONE) {
    nfc_status = nfc_transceive((const uint8_t*)&apdu_buffer.apdu,
                                apdu_buffer_len, &apdu_resp, &apdu_resp_len);
    if (apdu_resp[0] != 0x90 || apdu_resp[1] != 0x00) {
      nfc_status = NFC_ERROR;
    }

    cli_trace(cli, "nfc_transceive: stat=%d, rsp=0x%02X 0x%02X, len=%d",
              nfc_status, apdu_resp[0], apdu_resp[1], *apdu_resp_len);
  }
  return nfc_status;
}

static nfc_status_t nfc_select_file(cli_t* cli, const uint8_t* select_file,
                                    size_t file_len) {
  rfalIsoDepApduBufFormat apdu_buffer;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;
  nfc_status_t nfc_status = NFC_ERROR;

  ReturnCode ret_code = rfalT4TPollerComposeSelectFile(
      &apdu_buffer, select_file, file_len, &apdu_buffer_len);

  if (ret_code == RFAL_ERR_NONE) {
    nfc_status = nfc_transceive((const uint8_t*)&apdu_buffer.apdu,
                                apdu_buffer_len, &apdu_resp, &apdu_resp_len);
    if ((nfc_status == NFC_OK) &&
        ((apdu_resp[0] != 0x90) || (apdu_resp[1] != 0x00))) {
      nfc_status = NFC_ERROR;
    }

    cli_trace(cli, "nfc_transceive: stat=%d, rsp=0x%02X 0x%02X, len=%d",
              nfc_status, apdu_resp[0], apdu_resp[1], *apdu_resp_len);
  }
  return nfc_status;
}

static nfc_status_t nfc_read_file(cli_t* cli, uint16_t offset,
                                  uint16_t* exp_len, uint8_t* read_data) {
  rfalIsoDepApduBufFormat apdu_buffer;
  uint16_t apdu_buffer_len;
  uint8_t* apdu_resp = NULL;
  uint16_t* apdu_resp_len = NULL;
  uint8_t exp_to_read = (exp_len != NULL) ? (uint8_t)*exp_len : 0;
  nfc_status_t nfc_status = NFC_ERROR;

  ReturnCode ret_code = rfalT4TPollerComposeReadData(
      &apdu_buffer, offset, exp_to_read, &apdu_buffer_len);
  if (ret_code == RFAL_ERR_NONE) {
    nfc_status = nfc_transceive((const uint8_t*)&apdu_buffer.apdu,
                                apdu_buffer_len, &apdu_resp, &apdu_resp_len);

    if ((nfc_status == NFC_OK) && ((apdu_resp[*apdu_resp_len - 2] != 0x90) ||
                                   (apdu_resp[*apdu_resp_len - 1] != 0x00))) {
      nfc_status = NFC_ERROR;
    } else {
      if (read_data != NULL) {
        memcpy(read_data, apdu_resp, *apdu_resp_len - 2);
      }
      if (exp_len != NULL) {
        *exp_len = *apdu_resp_len - 2;
      }
    }

    cli_trace(cli, "nfc_transceive: stat=%d, rsp=0x%02X 0x%02X, len=%d",
              nfc_status, apdu_resp[*apdu_resp_len - 2],
              apdu_resp[*apdu_resp_len - 1], *apdu_resp_len);
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

  nfc_status_t nfc_status = nfc_start_discovery(NFC_DISCOVERY_TYPE_CARD_READER);
  if (nfc_status == NFC_NOT_INITIALIZED) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC not initialized");
    goto cleanup;
  } else if (nfc_status != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC activation failed");
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
      cli_error(cli, CLI_ERROR_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, CLI_ERROR, "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");

      nfc_dev_read_info(&dev_info);
      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        default:
          cli_error(cli, CLI_ERROR_ABORT, "NFC ERROR Unexpected");
          goto cleanup;
      }

      cli_trace(cli, "Select NDEF APP");
      nfc_status = nfc_select_app(cli, &aid_select_ndef_app[0],
                                  sizeof(aid_select_ndef_app));
      if (nfc_status != NFC_OK) {
        cli_error(cli, CLI_ERROR, "NFC select app failed");
        goto cleanup;
      }

      cli_trace(cli, "Select NDEF File");
      nfc_status =
          nfc_select_file(cli, &select_ndef_file[0], sizeof(select_ndef_file));
      if (nfc_status != NFC_OK) {
        cli_error(cli, CLI_ERROR, "NFC select file failed");
        goto cleanup;
      }

      cli_trace(cli, "Read NDEF File length");
      uint8_t ndef_file[32];
      uint16_t ndef_file_size = 0;
      uint16_t ndef_file_len = 2u;
      nfc_status = nfc_read_file(cli, 0x00, &ndef_file_len, ndef_file);
      ndef_file_size = (ndef_file[0] << 8) | ndef_file[1];
      if (nfc_status != NFC_OK) {
        cli_error(cli, CLI_ERROR, "NFC read file failed");
        goto cleanup;
      }

      cli_trace(cli, "Read NDEF File (len=%d)", ndef_file_size);
      memset(ndef_file, 0, sizeof(ndef_file));
      if (ndef_file_size > sizeof(ndef_file)) {
        cli_error(cli, CLI_ERROR, "NDEF file too big");
        goto cleanup;
      }
      nfc_status = nfc_read_file(cli, 0x02, &ndef_file_size, ndef_file);
      if (nfc_status != NFC_OK) {
        cli_error(cli, CLI_ERROR, "NFC read file failed");
        goto cleanup;
      }
      cli_trace(cli, "NDEF-URI: %s", &ndef_file[ndef_file_header_size]);
    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      break;
    }

    systick_delay_ms(1);
  }
  cli_ok(cli, "");

cleanup:
  nfc_stop_discovery();
}

static void prodtest_nfc_backup_cli_cmd(cli_t* cli) {
  memset(&dev_info, 0, sizeof(dev_info));

  nfc_status_t nfc_status = nfc_start_discovery(NFC_DISCOVERY_TYPE_CARD_READER);
  if (nfc_status == NFC_NOT_INITIALIZED) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC not initialized");
    goto cleanup;
  } else if (nfc_status != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC activation failed");
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

    nfc_state_t nfc_state;
    nfc_get_state(&nfc_state);
    if (nfc_state.connected) {
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
      cli_error(cli, CLI_ERROR, "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");

      nfc_dev_read_info(&dev_info);
      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        default:
          cli_error(cli, CLI_ERROR_ABORT,
                    "NFC ERROR: Unexpected card type (%d)", dev_info.type);
          goto cleanup;
      }
      nfc_cli_flush_input_console();
      nfc_cli_prefix(cli);

    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      break;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_stop_discovery();
}

typedef struct{
  uint8_t data[256];
  uint16_t len;
  uint16_t status;
} apdu_resp_t;

//nfc_transceive(const uint8_t *tx_data, uint16_t tx_data_len,
//                           uint8_t **rx_data, uint16_t **rx_data_len)


static void assamble_apdu_cmd(uint8_t *transfer_buf,
                              size_t transfer_buf_size,
                              size_t *transfer_buf_len,
                              uint8_t cla,
                              uint8_t ins,
                              uint8_t p1,
                              uint8_t p2,
                              const uint8_t* tx_data,
                              uint16_t tx_data_len){

  if(transfer_buf_size < (tx_data_len + 5)){
    return;
  }

  transfer_buf[0] = cla;
  transfer_buf[1] = ins;
  transfer_buf[2] = p1;
  transfer_buf[3] = p2;
  transfer_buf[4] = tx_data_len;
  memcpy(&transfer_buf[5], tx_data, tx_data_len);
  
  if (transfer_buf_len) {
    *transfer_buf_len = tx_data_len + 5;
  }

}


      // Do a Hanshake
  uint8_t B_static_private_key[DHLEN] = {
      0x5f, 0x8a, 0x0d, 0x3b, 0x6c, 0x9e, 0x1f, 0x4a, 0x7d, 0x2b, 0x8c,
      0x5e, 0x0f, 0x3a, 0x6d, 0x9b, 0x7c, 0x1e, 0x4f, 0x2a, 0x8d, 0x3b,
      0x5c, 0x0e, 0x6a, 0x9f, 0x7b, 0x1d, 0x2e, 0x8c, 0xa3, 0xf4};


static const uint8_t psk[DHLEN] = {'P', 'S', 'K', 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
                        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
                        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0};

// static void cli_log_hex(cli_t* cli, const char* prefix, const uint8_t* data, size_t len) {
//   char text[256];
//   cstr_encode_hex(text, sizeof(text), data, len);
//   cli_trace(cli, "%s: %s", prefix, text);
// }

static void prodtest_nfc_backup_handshake_cmd(cli_t* cli){

  nfc_status_t nfc_status = nfc_start_discovery(NFC_DISCOVERY_TYPE_CARD_READER);

  if (nfc_status == NFC_NOT_INITIALIZED) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC not initialized");
    goto cleanup;
  } else if (nfc_status != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC activation failed");
    goto cleanup;
  } else {
    cli_trace(cli, "");
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
      goto cleanup;
    }
    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, CLI_ERROR, "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");

      nfc_dev_read_info(&dev_info);
      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        default:
          cli_error(cli, CLI_ERROR_ABORT,
                    "NFC ERROR: Unexpected card type (%d)", dev_info.type);
          goto cleanup;
      }

      /** Noise protocol handshake */

      ts_t status;
      uint8_t transfer_buf[256] = {0};
      size_t transfer_buf_len = 0;
      uint8_t *receive_buf = NULL;
      uint16_t *receive_buf_len = NULL;

      uint32_t tic = systick_ms();

      initiator_xxpsk3_t initiator = {0};
      status = noise_initiator_init(&initiator, psk, B_static_private_key);

      if(!ts_ok(status)) {
        cli_error(cli, CLI_ERROR_ABORT, "Noise handshake initialization failed");
        goto cleanup;
      }

      uint8_t request_buf[256] = {0};
      size_t request_buf_size;
      status = noise_initiator_create_request1(&initiator,
                                      request_buf,
                                      sizeof(request_buf),
                                      &request_buf_size);


      if(!ts_ok(status)) {
        cli_error(cli, CLI_ERROR_ABORT, "Noise handshake request creation failed");
        goto cleanup;
      }

      // Parse apdu message
      assamble_apdu_cmd(transfer_buf, sizeof(transfer_buf),&transfer_buf_len,
                        0x80, 0x01, 0x00, 0x00,
                        request_buf, request_buf_size);

      nfc_status_t nfc_status = nfc_transceive(transfer_buf,
                                               (uint16_t)transfer_buf_len,
                                               &receive_buf,
                                               &receive_buf_len);

      if (nfc_status != NFC_OK || receive_buf == NULL ||
          receive_buf_len == NULL) {
        cli_error(cli, CLI_ERROR_ABORT, "NFC transceive failed");
        goto cleanup;
      }

      uint8_t decrypted_payload[256] = {0};
      size_t decrypted_payload_len = 0;

      noise_initiator_handle_response1(&initiator, receive_buf, *receive_buf_len - 2,
                                       decrypted_payload, sizeof(decrypted_payload),
                                       &decrypted_payload_len);
      uint32_t toc = systick_ms();

      status = noise_initiator_create_request2(&initiator, request_buf,
                                      sizeof(request_buf),
                                      &request_buf_size);

      if(!ts_ok(status)) {
        cli_error(cli, CLI_ERROR_ABORT, "Noise handshake request2 creation failed");
        goto cleanup;
      }

      assamble_apdu_cmd(transfer_buf, sizeof(transfer_buf),&transfer_buf_len,
                        0x80, 0x01, 0x01, 0x00,
                        request_buf, request_buf_size);

      nfc_status = nfc_transceive(transfer_buf,
                                  (uint16_t)transfer_buf_len,
                                  &receive_buf,
                                  &receive_buf_len);
  
      status = noise_initiator_handle_response2(&initiator, receive_buf,
                                                *receive_buf_len - 2);
    
      if(ts_ok(status)) {
        cli_trace(cli, "Noise handshake completed successfully.");
      } else {
        cli_error(cli, CLI_ERROR_ABORT, "Noise handshake failed with status: %d", status);
        goto cleanup;
      }

    uint32_t toc2 = systick_ms();

    cli_trace(cli, "Noise handshake timing: request1: %d ms, request2: %d ms, total: %d ms",
              toc - tic, toc2 - toc, toc2 - tic);


    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
      goto cleanup;
    }

    systick_delay_ms(1);
  }

cleanup:
  nfc_stop_discovery();

} 

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-cli",
  .func = prodtest_nfc_backup_cli_cmd,
  .info = "Open dedicated NFC cli for manual testing of NFC.",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-handshake",
  .func = prodtest_nfc_backup_handshake_cmd,
  .info = "Perform NFC backup handshake with NFC card",
  .args = ""
)

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-ndef",
  .func = prodtest_nfc_backup_read_ndef_cmd,
  .info = "Read NDEF data from NFC backup card",
  .args = "[<timeout>]"
);

#endif  // USE_NFC
