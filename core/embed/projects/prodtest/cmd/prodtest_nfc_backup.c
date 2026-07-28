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
#include <noise_xxpsk3.h>
#include <rtl/cli.h>
#include <sys/rng.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

#include "prodtest_error_codes.h"

static noise_xxpsk3_initiator_t intr = {0};

static ts_t nfc_backup_compose_apdu(uint8_t cla, uint8_t ins, uint8_t p1,
                                    uint8_t p2, const uint8_t* data,
                                    size_t data_len, nfc_apdu_message_t* apdu) {
  TSH_DECLARE;

  TSH_CHECK_ARG(apdu != NULL);
  TSH_CHECK_ARG(data_len <= NFC_MAX_APDU_LEN);
  TSH_CHECK_ARG(data != NULL || data_len == 0);

  apdu->data[0] = cla;
  apdu->data[1] = ins;
  apdu->data[2] = p1;
  apdu->data[3] = p2;
  apdu->data[4] = (uint8_t)data_len;
  memcpy(&apdu->data[5], data, data_len);
  apdu->data_len = 5 + data_len;

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_noise(cli_t* cli, uint8_t (*psk)[32]) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(*psk != NULL);
  bool noise_status = false;

  // Generate static private key for initiator
  uint8_t static_private_key[NOISE_XXPSK3_DHLEN] = {0};
  rng_fill_buffer(static_private_key, sizeof(static_private_key));

  noise_status = noise_xxpsk3_initiator_init(&intr, *psk, static_private_key);
  TSH_CHECK(noise_status, TS_EINVAL);

  uint8_t request[256] = {0};
  size_t request_size = 0;

  noise_status = noise_xxpsk3_initiator_create_request1(
      &intr, NULL, 0, request, sizeof(request), &request_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};
  status = nfc_backup_compose_apdu(0x80, 0x01, 0x00, 0x00, request,
                                   request_size, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  uint8_t certificate[256] = {0};
  size_t certificate_size = 0;

  noise_status = noise_xxpsk3_initiator_handle_response1(
      &intr, rsp.data, rsp.data_len - 2, certificate, sizeof(certificate),
      &certificate_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  // print obtained certificate
  char text[500] = {0};
  cstr_encode_hex(text, sizeof(text), certificate, certificate_size);
  cli_trace(cli, "Card certificate: %s", text);

  noise_status = noise_xxpsk3_initiator_create_request2(
      &intr, NULL, 0, request, sizeof(request), &request_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  status = nfc_backup_compose_apdu(0x80, 0x01, 0x01, 0x00, request,
                                   request_size, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  uint8_t plain_text[256] = {0};
  size_t plain_text_size = 0;
  noise_status = noise_xxpsk3_receive_message(
      &intr.transport_state, rsp.data, rsp.data_len - 2, plain_text,
      sizeof(plain_text), &plain_text_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  cli_trace(cli, "Card welcome message: %.*s", (int)plain_text_size,
            plain_text);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_handshake(cli_t* cli) {
  TSH_DECLARE;
  ts_t status = TS_OK;

  // Clear the initiator structure
  memset(&intr, 0, sizeof(intr));

  cli_trace(cli, "++++++ NFC backup handshake start ++++++");

  nfc_apdu_message_t cmd = {.data = {0x00, 0xA4, 0x04, 0x00, 0x07, 0xA0, 0x00,
                                     0x00, 0x09, 0x59, 0x00, 0x01},
                            .data_len = 12};

  nfc_apdu_message_t resp = {0};

  status = nfc_transceive(&cmd, &resp);

  TSH_CHECK(resp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(resp.data[0] == 0x90U && resp.data[1] == 0x00U, TS_EINVAL);

  uint8_t pcd_psk[16] = {0};
  uint8_t picc_psk[16] = {0};
  uint16_t picc_psk_len = 0;

  rng_fill_buffer(pcd_psk, sizeof(pcd_psk));

  status = nfc_transceive_psk(pcd_psk, sizeof(pcd_psk), picc_psk,
                              sizeof(picc_psk), &picc_psk_len);

  if (ts_error(status) || picc_psk_len != sizeof(picc_psk)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_PSK_EXCHANGE_FAILED,
              "NFC PSK exchange failed");
    goto cleanup;
  }

  // Combine both share into PSK
  uint8_t psk[32] = {0};
  memcpy(psk, pcd_psk, 16);
  memcpy(psk + 16, picc_psk, 16);

  char text[256] = {0};
  cstr_encode_hex(text, sizeof(text), &psk, sizeof(psk));
  cli_trace(cli, "Exchanged PSK: %s", text);

  status = nfc_backup_noise(cli, &psk);
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_NOISE_HANDSHAKE_FAILED,
              "NFC noise handshake failed");
    goto cleanup;
  }

  cli_trace(cli, "++++++ NFC backup completed ++++++++++++");

cleanup:
  return status;
}

static void prodtest_nfc_backup_handshake(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  ts_t status;

  status = nfc_init();
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_INIT, "NFC initialization failed");
    goto cleanup;
  }

  status = nfc_start_discovery();
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_DISCOVERY,
              "NFC start discovery failed");
    goto cleanup;
  }

  cli_trace(cli, "Tap NFC backup card.");

  // Clear leftover events
  nfc_event_t event_flag;
  sysevents_t awaited_events = {0};
  sysevents_t signalled_events = {0};

  nfc_get_event(&event_flag);
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "NFC card detected.");

      nfc_dev_info_t dev_info;
      nfc_get_device_info(&dev_info);
      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, PRODTEST_ERR_NFC_BACKUP_UNEXPECTED_CARD_TYPE,
                  "Unexpected card type (%d)", dev_info.type);
        goto cleanup;
      }

      status = nfc_backup_handshake(cli);

      break;
    }
  }

  cli_ok(cli, "");

cleanup:
  nfc_stop_discovery();
  nfc_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-backup-handshake",
  .func = prodtest_nfc_backup_handshake,
  .info = "Run nfc-backup handshake test",
  .args = ""
);

#endif  // USE_NFC
