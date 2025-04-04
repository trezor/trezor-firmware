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

#ifdef USE_BLE

#include <trezor_rtl.h>

#include <io/ble.h>
#include <rtl/cli.h>
#include <sys/systick.h>
#include <sys/systimer.h>

void ble_timer_cb(void* context) {
  ble_event_t e = {0};
  ble_command_t cmd = {0};

  bool event_received = ble_get_event(&e);

  if (event_received) {
    switch (e.type) {
      case BLE_PAIRING_REQUEST:
        cmd.cmd_type = BLE_ALLOW_PAIRING;
        memcpy(cmd.data.raw, e.data, BLE_PAIRING_CODE_LEN);
        cmd.data_len = BLE_PAIRING_CODE_LEN;
        ble_issue_command(&cmd);
      default:
        break;
    }
  }
}

static bool ensure_ble_init(cli_t* cli) {
  cli_trace(cli, "Initializing the BLE...");
  if (!ble_init()) {
    cli_error(cli, CLI_ERROR, "Cannot initialize BLE.");
    return false;
  }

  static systimer_t* timer = NULL;

  if (timer == NULL) {
    timer = systimer_create(ble_timer_cb, NULL);
    if (timer == NULL) {
      cli_error(cli, CLI_ERROR, "Cannot create timer.");
      return false;
    }
    systimer_set_periodic(timer, 10);
  }

  return true;
}

static void prodtest_ble_adv_start(cli_t* cli) {
  const char* name = cli_arg(cli, "name");

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  uint16_t name_len =
      strlen(name) > BLE_ADV_NAME_LEN ? BLE_ADV_NAME_LEN : strlen(name);

  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_PAIRING_MODE;
  cmd.data_len = sizeof(cmd.data.adv_start);
  cmd.data.adv_start.static_mac = true;
  memcpy(cmd.data.adv_start.name, name, name_len);

  if (!ble_issue_command(&cmd)) {
    cli_error(cli, CLI_ERROR, "Could not start advertising.");
    return;
  }

  uint32_t timeout = ticks_timeout(1000);

  bool result = false;
  while (!ticks_expired(timeout)) {
    ble_state_t state = {0};
    ble_get_state(&state);

    if (state.pairing) {
      result = true;
      break;
    }
  }

  if (!result) {
    cli_error(cli, CLI_ERROR, "Could not start advertising.");
    return;
  }

  cli_trace(cli, "Advertising started.");
  cli_ok(cli, "");
}

static void prodtest_ble_adv_stop(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_SWITCH_OFF;
  cmd.data_len = 0;

  if (!ble_issue_command(&cmd)) {
    cli_error(cli, CLI_ERROR, "Could not stop advertising.");
    return;
  }

  uint32_t timeout = ticks_timeout(1000);

  bool result = false;
  while (!ticks_expired(timeout)) {
    ble_state_t state = {0};
    ble_get_state(&state);

    if (!state.pairing && !state.connectable) {
      result = true;
      break;
    }
  }

  if (!result) {
    cli_error(cli, CLI_ERROR, "Could not stop advertising.");
    return;
  }

  cli_trace(cli, "Advertising stopped.");
  cli_ok(cli, "");
}

static void prodtest_ble_info(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  uint8_t mac[6] = {0};

  if (!ble_get_mac(mac, 6)) {
    cli_error(cli, CLI_ERROR, "Could not read MAC.");
    return;
  }

  cli_trace(cli, "MAC: %02x:%02x:%02x:%02x:%02x:%02x", mac[5], mac[4], mac[3],
            mac[2], mac[1], mac[0]);
  cli_ok(cli, "");
}

bool prodtest_ble_erase_bonds(cli_t* cli) {
  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_ERASE_BONDS;

  ble_state_t state = {0};
  ble_issue_command(&cmd);

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    ble_get_state(&state);
    if (state.peer_count == 0 && state.state_known) {
      return true;
    }
  }

  return false;
}

static void prodtest_ble_erase_bonds_cmd(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  ble_state_t state = {0};

  ble_get_state(&state);

  if (!state.state_known) {
    cli_error(cli, CLI_ERROR, "BLE state unknown.");
  }

  if (state.peer_count == 0) {
    cli_ok(cli, "No bonds to erase.");
    return;
  }

  if (!prodtest_ble_erase_bonds(cli)) {
    cli_error(cli, CLI_ERROR, "Could not erase bonds.");
  }

  cli_trace(cli, "Erased %d bonds.", state.peer_count);
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "ble-adv-start",
  .func = prodtest_ble_adv_start,
  .info = "Start BLE advertising",
  .args = "<name>"
);

PRODTEST_CLI_CMD(
  .name = "ble-adv-stop",
  .func = prodtest_ble_adv_stop,
  .info = "Stop BLE advertising",
  .args = "<name>"
);

PRODTEST_CLI_CMD(
  .name = "ble-info",
  .func = prodtest_ble_info,
  .info = "Get BLE information",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "ble-erase-bonds",
  .func = prodtest_ble_erase_bonds_cmd,
  .info = "Erase all BLE bonds",
  .args = ""
);

#endif
