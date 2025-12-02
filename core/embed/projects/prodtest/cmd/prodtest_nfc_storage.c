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

#ifdef USE_NFC_STORAGE

#include <trezor_rtl.h>

#include <io/nfc_storage.h>
#include <rtl/cli.h>
#include <rust_ui_prodtest.h>
#include <sys/systick.h>
#include "prodtest.h"

static void prodtest_nfc_storage_monitor(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_storage_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage init failed");
    goto cleanup;
  }

  if (!nfc_storage_register_device(NFC_STORAGE_ST25TV)) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage register device failed");
    goto cleanup;
  }

  if (!nfc_storage_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage start discovery failed");
    goto cleanup;
  }

  nfc_storage_event_t event;

  // Clean leftover event
  nfc_storage_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_STORAGE;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_STORAGE) == 0) {
      // Nothing to do
      continue;
    }

    nfc_storage_get_events(&event);

    if (event == NFC_STORAGE_DEVICE_CONNECTED) {
      cli_trace(cli, "NFC storage device connected.");
      screen_prodtest_nfc(true);
    } else if (event == NFC_STORAGE_DEVICE_DISCONNECTED) {
      cli_trace(cli, "NFC storage device disconnected.");
      screen_prodtest_nfc(false);
    }
  }

  nfc_storage_stop_discovery();
  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_storage_deinit();
}

static void prodtest_nfc_storage_store_secret(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* secret = cli_arg(cli, "secret");
  size_t secret_length = strlen(secret);

  if (!nfc_storage_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage init failed");
    goto cleanup;
  }

  if (!nfc_storage_register_device(NFC_STORAGE_ST25TV)) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage register device failed");
    goto cleanup;
  }

  if (!nfc_storage_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage start discovery failed");
    goto cleanup;
  }

  nfc_storage_event_t event;

  // Clean leftover event
  nfc_storage_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_STORAGE;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_STORAGE) == 0) {
      // Nothing to do
      continue;
    }

    nfc_storage_get_events(&event);

    if (event == NFC_STORAGE_DEVICE_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_storage_mem_struct_t mem_struct;
      if (!nfc_storage_device_get_mem_struct(&mem_struct)) {
        cli_trace(cli, "Failed to get memory structure from NFC storage tag.");
        continue;
      }

      // Verify that secret fits into tag memory
      if (secret_length > mem_struct.total_size_bytes) {
        cli_trace(cli, "Secret too long to fit into NFC storage tag memory.");
        continue;
      }

      if (!nfc_storage_device_write_data(0, (const uint8_t*)secret,
                                         secret_length)) {
        cli_trace(cli, "Failed to store secret into NFC storage tag.");
        continue;
      }

      break;

    } else if (event == NFC_STORAGE_DEVICE_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_storage_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_storage_deinit();
}

static void prodtest_nfc_storage_read_secret(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  char data_buffer[320];

  if (!nfc_storage_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage init failed");
    goto cleanup;
  }

  if (!nfc_storage_register_device(NFC_STORAGE_ST25TV)) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage register device failed");
    goto cleanup;
  }

  if (!nfc_storage_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage start discovery failed");
    goto cleanup;
  }

  nfc_storage_event_t event;

  // Clean leftover event
  nfc_storage_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_STORAGE;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_STORAGE) == 0) {
      // Nothing to do
      continue;
    }

    nfc_storage_get_events(&event);

    if (event == NFC_STORAGE_DEVICE_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_storage_mem_struct_t mem_struct;
      if (!nfc_storage_device_get_mem_struct(&mem_struct)) {
        cli_trace(cli, "Failed to get memory structure from NFC storage tag.");
        continue;
      }

      size_t read_size = MIN(sizeof(data_buffer), mem_struct.total_size_bytes);

      if (!nfc_storage_device_read_data(0, (uint8_t*)data_buffer, read_size)) {
        cli_trace(cli, "Failed to read secret from NFC storage tag.");
        continue;
      }

      data_buffer[sizeof(data_buffer) - 1] = '\0';  // Ensure null
      cli_trace(cli, "NFC storage secret: %s", data_buffer);

      break;

    } else if (event == NFC_STORAGE_DEVICE_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_storage_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_storage_deinit();
}

static void prodtest_nfc_storage_dump_memory(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t data_buffer[320];

  if (!nfc_storage_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage init failed");
    goto cleanup;
  }

  if (nfc_storage_register_device(NFC_STORAGE_ST25TV) == false) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage register device failed");
    goto cleanup;
  }

  if (!nfc_storage_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage start discovery failed");
    goto cleanup;
  }

  nfc_storage_event_t event;

  // Clean leftover event
  nfc_storage_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_STORAGE;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_STORAGE) == 0) {
      // Nothing to do
      continue;
    }

    nfc_storage_get_events(&event);

    if (event == NFC_STORAGE_DEVICE_CONNECTED) {
      screen_prodtest_nfc(true);

      nfc_storage_mem_struct_t mem_struct;
      if (!nfc_storage_device_get_mem_struct(&mem_struct)) {
        cli_trace(cli, "Failed to get memory structure from NFC storage tag.");
        continue;
      }

      size_t read_size = MIN(sizeof(data_buffer), mem_struct.total_size_bytes);

      if (!nfc_storage_device_read_data(0, (uint8_t*)data_buffer, read_size)) {
        cli_trace(cli, "Failed to read secret from NFC storage tag.");
        continue;
      }

      for (size_t i = 0; i < read_size / 4; i++) {
        cli_trace(cli, "%08X: %02X %02X %02X %02X", (uint32_t)(i * 4),
                  data_buffer[i * 4], data_buffer[i * 4 + 1],
                  data_buffer[i * 4 + 2], data_buffer[i * 4 + 3]);
      }

      break;

    } else if (event == NFC_STORAGE_DEVICE_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_storage_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_storage_deinit();
}

static void prodtest_nfc_storage_wipe_memory(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!nfc_storage_init()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage init failed");
    goto cleanup;
  }

  if (!nfc_storage_register_device(NFC_STORAGE_ST25TV)) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage register device failed");
    goto cleanup;
  }

  if (!nfc_storage_start_discovery()) {
    cli_error(cli, CLI_ERROR_FATAL, "NFC storage start discovery failed");
    goto cleanup;
  }

  nfc_storage_event_t event;

  // Clean leftover event
  nfc_storage_get_events(&event);

  sysevents_t awaited_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC_STORAGE;
  sysevents_t signalled_events = {0};
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  screen_prodtest_nfc(false);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
      break;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(10));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC_STORAGE) == 0) {
      // Nothing to do
      continue;
    }

    nfc_storage_get_events(&event);

    if (event == NFC_STORAGE_DEVICE_CONNECTED) {
      screen_prodtest_nfc(true);

      if (!nfc_storage_device_wipe_memory()) {
        cli_trace(cli, "Failed to wipe NFC storage memory.");
      }

      cli_trace(cli, "NFC storage memory wiped.");
      break;
    } else if (event == NFC_STORAGE_DEVICE_DISCONNECTED) {
      screen_prodtest_nfc(false);
    }
  }

  nfc_storage_stop_discovery();

  prodtest_show_homescreen();

  cli_ok(cli, "");

cleanup:
  nfc_storage_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-storage-monitor",
  .func = prodtest_nfc_storage_monitor,
  .info = "Monitor NFC storage tag connection",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-storage-store-secret",
  .func = prodtest_nfc_storage_store_secret,
  .info = "Store secret data to NFC storage tag",
  .args = "<secret>"
);  

PRODTEST_CLI_CMD(
  .name = "nfc-storage-read-secret",
  .func = prodtest_nfc_storage_read_secret,
  .info = "Read secret data from NFC storage tag",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-storage-dump-memory",
  .func = prodtest_nfc_storage_dump_memory,
  .info = "Dump entire NFC storage tag memory",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-storage-wipe-memory",
  .func = prodtest_nfc_storage_wipe_memory,
  .info = "Wipe NFC storage memory",
  .args = ""
)

#endif  // USE_NFC_STORAGE
