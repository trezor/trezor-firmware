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
#include <sys/sysevent.h>
#include <sys/systick.h>

#include "prodtest_error_codes.h"

static uint8_t nfc_compose_uri(const char* uri, uint8_t* buffer,
                               uint8_t buffer_size) {
  size_t uri_len = strlen(uri);
  const uint8_t uri_header[] = {0x03,    uri_len + 5, 0xD1, 0x01,
                                uri_len, 0x55,        0x01};

  if (buffer_size < (uri_len + sizeof(uri_header))) {
    return 0;  // Not enough room to create URI
  }

  memcpy(buffer, uri_header, sizeof(uri_header));
  buffer = buffer + sizeof(uri_header);
  memcpy(buffer, uri, uri_len);
  buffer = buffer + uri_len;
  *buffer = 0xFE;

  return uri_len + sizeof(uri_header);  // return buffer len
}

static void prodtest_nfc_read_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  nfc_dev_info_t dev_info;
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
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_INIT,
              "NFC initialization failed");
    return;
  }

  nfc_status = nfc_start_discovery();
  if (ts_eq(nfc_status, TS_ENOINIT)) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_INIT, "NFC not initialized");
    goto cleanup;
  } else if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_READ_ACTIVATION, "NFC activation failed");
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
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, PRODTEST_ERR_NFC_READ_CARD_ERROR,
                "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      nfc_get_device_info(&dev_info);
      cli_trace(cli, "NFC card detected.");

      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_B:
          cli_trace(cli, "NFC Type B: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_UNKNOWN:
          cli_trace(cli, "NFC Type UNKNOWN");
          break;
        default:
          cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED_TYPE,
                    "Unknown NFC card type!");
          goto cleanup;
      }

      switch (dev_info.interface) {
        case NFC_DEV_INTERFACE_RF:
          cli_trace(cli, "NFC Tag Type: RF (%d)", dev_info.interface);
          break;
        case NFC_DEV_INTERFACE_ISODEP:
          cli_trace(cli, "NFC Tag Type: ISO-DEP (%d)", dev_info.interface);
          break;
        case NFC_DEV_INTERFACE_UNKNOWN:
        default:
          cli_error(cli, PRODTEST_ERR_NFC_UNEXPECTED_IF,
                    "NFC Unexpected Tag Type (%d)", dev_info.interface);
          goto cleanup;
      }

    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_write_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;
  nfc_dev_info_t dev_info;
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
    cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_INIT,
              "NFC initialization failed");
    return;
  }

  nfc_status = nfc_start_discovery();
  if (ts_eq(nfc_status, TS_ENOINIT)) {
    cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_START, "NFC not initialized");
    goto cleanup;
  } else if (ts_error(nfc_status)) {
    cli_error(cli, PRODTEST_ERR_NFC_WRITE_ACTIVATION, "NFC activation failed");
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
      cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_ERROR,
                "Failed to get NFC events");
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");
      nfc_get_device_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, PRODTEST_ERR_NFC_WRITE_TYPE_A_ONLY,
                  "Only NFC type A cards supported");
        goto cleanup;
      }

      cli_trace(cli, "Writing URI to NFC tag %s", dev_info.uid);
      uint8_t uri_buffer[128] = {0};
      uint8_t* rx_buff_ptr = NULL;
      uint16_t* rx_buff_len = NULL;
      nfc_apdu_cmd_t tx_buf = {.data = uri_buffer, .data_len = 0};
      nfc_apdu_response_t rx_buf = {.data = &rx_buff_ptr,
                                    .data_len = &rx_buff_len};

      tx_buf.data_len =
          nfc_compose_uri("trezor.io/", uri_buffer, sizeof(uri_buffer));
      nfc_status = nfc_transceive(tx_buf, rx_buf);
      if (ts_ok(nfc_status)) {
        cli_trace(cli, "URI write success");
      } else {
        cli_error(cli, PRODTEST_ERR_NFC_WRITE_CARD_ERROR,
                  "URI write failed: err=%d", ts_code(nfc_status));
      }

    } else if (event_flag == NFC_EVENT_DISCONNECTED) {
      cli_trace(cli, "NFC card removed.");
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-read-card",
  .func = prodtest_nfc_read_card,
  .info = "Activate NFC in reader mode",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-write-card",
  .func = prodtest_nfc_write_card,
  .info = "Activate NFC in reader mode and write a URI to the attached card",
  .args = "[<timeout>]"
);

#endif  // USE_NFC
