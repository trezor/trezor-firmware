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
#include <io/nfc_backup.h>
#include <rtl/cli.h>
#include <rust_ui_prodtest.h>
#include <sys/systick.h>
#include "prodtest.h"

static nfc_dev_info_t dev_info = {0};

static void prodtest_nfc_read_card(cli_t* cli) {
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

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "NFC activated in reader mode for %d ms.", timeout);
    } else {
      cli_trace(cli, "NFC activated in reader mode");
    }
  }

  nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B | NFC_POLLER_TECH_F |
                    NFC_POLLER_TECH_V);
  nfc_activate_stm();

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, CLI_ERROR, "NFC error");
      goto cleanup;
    }

    if (nfc_event == NFC_EVENT_ACTIVATED) {
      nfc_dev_read_info(&dev_info);

      cli_trace(cli, "NFC card detected.");

      switch (dev_info.type) {
        case NFC_DEV_TYPE_A:
          cli_trace(cli, "NFC Type A: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_B:
          cli_trace(cli, "NFC Type B: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_F:
          cli_trace(cli, "NFC Type F: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_V:
          cli_trace(cli, "NFC Type V: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_ST25TB:
          cli_trace(cli, "NFC Type ST25TB: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_AP2P:
          cli_trace(cli, "NFC Type AP2P: UID: %s", dev_info.uid);
          break;
        case NFC_DEV_TYPE_UNKNOWN:
          cli_trace(cli, "NFC Type UNKNOWN");
          break;
        default:
          cli_error(cli, CLI_ERROR_ABORT, "NFC ERROR Unexpected");
          goto cleanup;
      }

      if (timeout_set) {
        nfc_dev_deactivate();
        cli_trace(cli, "NFC reader mode over");
        break;
      }

      systick_delay_ms(100);
      nfc_dev_deactivate();
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_emulate_card(cli_t* cli) {
  uint32_t timeout = 0;
  bool timeout_set = false;

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

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli, "Emulation started for %d ms", timeout);
    } else {
      cli_trace(cli, "Emulation started");
    }
  }

  nfc_register_tech(NFC_CARD_EMU_TECH_A);
  nfc_activate_stm();

  uint32_t expire_time = ticks_timeout(timeout);
  nfc_event_t nfc_event;

  while (!timeout_set || !ticks_expired(expire_time)) {
    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, CLI_ERROR, "NFC error");
      goto cleanup;
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }
    systick_delay_ms(1);
  }

  cli_trace(cli, "Emulation over");

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

static void prodtest_nfc_write_card(cli_t* cli) {
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

  nfc_status_t ret = nfc_init();

  if (ret != NFC_OK) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC init failed");
    goto cleanup;
  } else {
    if (timeout_set) {
      cli_trace(cli,
                "NFC reader on, put the card on the reader (timeout %d ms)",
                timeout);
    } else {
      cli_trace(cli, "NFC reader on, put the card on the reader");
    }
  }

  nfc_register_tech(NFC_POLLER_TECH_A | NFC_POLLER_TECH_B | NFC_POLLER_TECH_F |
                    NFC_POLLER_TECH_V);
  nfc_activate_stm();

  nfc_event_t nfc_event;
  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (timeout_set && ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "NFC timeout");
      goto cleanup;
    }

    nfc_status_t nfc_status = nfc_get_event(&nfc_event);

    if (nfc_status != NFC_OK) {
      cli_error(cli, CLI_ERROR_FATAL, "NFC error");
      goto cleanup;
    }

    if (nfc_event == NFC_EVENT_ACTIVATED) {
      nfc_dev_read_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, CLI_ERROR_ABORT, "Only NFC type A cards supported");
        goto cleanup;
      }

      cli_trace(cli, "Writing URI to NFC tag %s", dev_info.uid);
      nfc_dev_write_ndef_uri();

      if (timeout_set) {
        nfc_dev_deactivate();
        cli_trace(cli, "NFC reader mode over");
        break;
      }

      systick_delay_ms(100);
      nfc_dev_deactivate();
    }

    if (cli_aborted(cli)) {
      goto cleanup;
    }

    systick_delay_ms(1);
  }

  cli_ok(cli, "");

cleanup:
  nfc_deinit();
}

/*******************************************************************************
 *                              NFC BACKUP
 ******************************************************************************/

static void prodtest_nfc_backup_monitor(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      cli_trace(cli, "NFC backup tag connected.");
      screen_prodtest_nfc(true);
    } else if (event == NFC_BACKUP_DISCONNECTED) {
      cli_trace(cli, "NFC backup tag disconnected.");
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_read_info(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_system_info_t tag_info;
      if (!nfc_backup_read_system_info(&tag_info)) {
        cli_trace(cli, "Failed to read system info from NFC backup tag.");
        continue;
      }

      // Copy the hex UID in printable string
      char uid[17];
      cstr_encode_hex(uid, 17, tag_info.uid, 8);
      cli_trace(cli, "UID: %s", uid);
      cli_trace(cli, "DSFID: 0x%02X", tag_info.dsfid);
      cli_trace(cli, "AFI: 0x%02X", tag_info.afi);
      cli_trace(cli, "Memory size: %d bytes",
                tag_info.mem_block_size * tag_info.mem_block_count);
      cli_trace(cli, "IC reference: 0x%02X", tag_info.ic_reference);

      cli_ok(cli, "%s 0x%02X 0x%02X %d 0x%02X", uid, tag_info.dsfid,
             tag_info.afi, tag_info.mem_block_size * tag_info.mem_block_count,
             tag_info.ic_reference);

      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_store_secret(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* secret = cli_arg(cli, "secret");
  size_t secret_length = strlen(secret);

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_system_info_t tag_info;
      if (!nfc_backup_read_system_info(&tag_info)) {
        cli_trace(cli, "Failed to read system info from NFC backup tag.");
        continue;
      }

      // Verify that secret fits into tag memory
      if (secret_length >
          (tag_info.mem_block_size * tag_info.mem_block_count)) {
        cli_trace(cli, "Secret too long to fit into NFC backup tag memory.");
        continue;
      }

      if (!nfc_backup_write_data(0, (const uint8_t*)secret, secret_length)) {
        cli_trace(cli, "Failed to store secret into NFC backup tag.");
        continue;
      }

      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_read_secret(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  char data_buffer[320];

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_system_info_t tag_info;
      if (!nfc_backup_read_system_info(&tag_info)) {
        cli_trace(cli, "Failed to read system info from NFC backup tag.");
        continue;
      }

      size_t read_size = MIN(sizeof(data_buffer), tag_info.mem_block_size *
                                                      tag_info.mem_block_count);

      if (!nfc_backup_read_data(0, (uint8_t*)data_buffer, read_size)) {
        cli_trace(cli, "Failed to read secret from NFC backup tag.");
        continue;
      }

      data_buffer[sizeof(data_buffer) - 1] = '\0';  // Ensure null termination
      cli_trace(cli, "NFC backup secret: %s", data_buffer);

      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_dump_memory(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t data_buffer[320];

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_system_info_t tag_info;
      if (!nfc_backup_read_system_info(&tag_info)) {
        cli_trace(cli, "Failed to read system info from NFC backup tag.");
        continue;
      }

      if (tag_info.mem_block_size * tag_info.mem_block_count >
          sizeof(data_buffer)) {
        cli_trace(cli, "NFC backup tag memory too large to dump.");
        continue;
      }

      if (!nfc_backup_read_data(
              0, data_buffer,
              tag_info.mem_block_size * tag_info.mem_block_count)) {
        cli_trace(cli, "Failed to dump NFC backup memory.");
        continue;
      }

      for (uint16_t i = 0; i < tag_info.mem_block_count; i++) {
        cli_trace(cli, "Block %03d: %02X %02X %02X %02X", i,
                  data_buffer[i * tag_info.mem_block_size + 0],
                  data_buffer[i * tag_info.mem_block_size + 1],
                  data_buffer[i * tag_info.mem_block_size + 2],
                  data_buffer[i * tag_info.mem_block_size + 3]);
      }

      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_wipe_memory(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      if (!nfc_backup_wipe_memory()) {
        cli_trace(cli, "Failed to wipe NFC backup memory.");
      }

      cli_trace(cli, "NFC backup memory wiped.");

      break;
    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_reset_silent(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_set_silent_mode(false);

      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

static void prodtest_nfc_backup_set_silent(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_backup_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup init failed");
    goto cleanup;
  }

  if (!nfc_backup_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC backup start discovery failed");
    goto cleanup;
  }

  nfc_backup_event_t event;

  // Clean leftover event
  nfc_backup_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_BACKUP;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_BACKUP) == 0) {
      // Nothing to do
      continue;
    }

    nfc_backup_get_events(&event);

    if (event == NFC_BACKUP_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_backup_set_silent_mode(true);

      systick_delay_ms(500);
      break;

    } else if (event == NFC_BACKUP_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_backup_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_backup_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-read-card",
  .func = prodtest_nfc_read_card,
  .info = "Activate NFC in reader mode",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-emulate-card",
  .func = prodtest_nfc_emulate_card,
  .info = "Activate NFC in card emulation (CE) mode",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-write-card",
  .func = prodtest_nfc_write_card,
  .info = "Activate NFC in reader mode and write a URI to the attached card",
  .args = "[<timeout>]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-monitor",
  .func = prodtest_nfc_backup_monitor,
  .info = "Monitor NFC backup tag connection",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-info",
  .func = prodtest_nfc_backup_read_info,
  .info = "Read NFC backup tag system info",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-enable-silent-mode",
  .func = prodtest_nfc_backup_set_silent,
  .info = "Enable nfc backup silent mode",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-disable-silent-mode",
  .func = prodtest_nfc_backup_reset_silent,
  .info = "Disable NFC backup silent mode",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-store-secret",
  .func = prodtest_nfc_backup_store_secret,
  .info = "Store secret data to NFC backup tag",
  .args = "<secret>"
);  

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-secret",
  .func = prodtest_nfc_backup_read_secret,
  .info = "Read secret data from NFC backup tag",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-dump-memory",
  .func = prodtest_nfc_backup_dump_memory,
  .info = "Dump entire NFC backup tag memory",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-wipe-memory",
  .func = prodtest_nfc_backup_wipe_memory,
  .info = "Wipe NFC backup memory",
  .args = ""
)

#endif  // USE_NFC
