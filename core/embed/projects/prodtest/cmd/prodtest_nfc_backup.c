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

static const uint8_t trezor_aid_select_cmd[] = {
  0x00, 0xA4, 0x04, 0x00, 0x07, 0xA0, 0x00, 0x00, 0x09, 0x59, 0x00, 0x01
};

static ts_t nfc_backup_handshake(void){

  TSH_DECLARE;
  ts_t status = TS_OK;

  uint8_t tx_buf[128] = {0};
  uint8_t rx_buf[128] = {0};
  uint16_t resp_len = sizeof(rx_buf);

  memcpy(tx_buf, trezor_aid_select_cmd, sizeof(trezor_aid_select_cmd));

  nfc_apdu_cmd_t cmd = {.data = tx_buf, .data_len = sizeof(trezor_aid_select_cmd)};
  nfc_apdu_response_t resp = {.data = rx_buf,
                              .data_len = &resp_len};

  status = nfc_transceive(cmd, resp);
  
  TSH_CHECK(*(resp.data_len) == 2U, TS_EINVAL);
  TSH_CHECK(resp.data[0] == 0x90U && resp.data[1] == 0x00U, TS_EINVAL);

cleanup:
  return status;

}

static void prodtest_nfc_backup_handshake(cli_t* cli) {
  
  if(cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  ts_t status;

  status = nfc_init();
  if(ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_INIT, "NFC initialization failed");
    goto cleanup;
  }

  status = nfc_start_discovery();
  if(ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_DISCOVERY, "NFC start discovery failed");
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
        cli_error(cli, PRODTEST_ERR_NFC_BACKUP_UNEXPECTED_CARD_TYPE, "Unexpected card type (%d)", dev_info.type);
        goto cleanup;
      }

      status = nfc_backup_handshake();
      if(ts_error(status)) {
        cli_error(cli, PRODTEST_ERR_NFC_BACKUP_HANDSHAKE_FAILED, "NFC backup handshake failed");
        goto cleanup;
      }

      break;
    }

  }

  cli_ok(cli, "NFC backup handshake successful.");

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
