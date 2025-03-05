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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "wire_iface_ble.h"

#include <io/ble.h>
#include <sys/systick.h>

static bool is_connected(void) {
  ble_state_t state = {0};
  ble_get_state(&state);
  return state.connected;
}

static bool ble_write_(uint8_t* data, size_t size) {
  if (size != BLE_TX_PACKET_SIZE) {
    return false;
  }

  uint32_t deadline = ticks_timeout(500);

  while (true) {
    if (ticks_expired(deadline)) {
      return false;
    }
    if (!is_connected()) {
      return false;
    }
    if (ble_can_write()) {
      break;
    }
  }

  return ble_write(data, size);
}

static int ble_read_(uint8_t* buffer, size_t buffer_size) {
  if (buffer_size != BLE_RX_PACKET_SIZE) {
    return -1;
  }

  uint32_t deadline = ticks_timeout(500);

  while (true) {
    if (ticks_expired(deadline)) {
      return false;
    }
    if (!is_connected()) {
      return false;
    }
    if (ble_can_read()) {
      break;
    }
  }

  int r = ble_read(buffer, buffer_size);

  return r;
}

static void ble_error(void) {
  error_shutdown_ex("BLE ERROR",
                    "Error reading from BLE. Try different BLE cable.", NULL);
}

void ble_iface_init(wire_iface_t* iface) {
  ble_start();

  memset(iface, 0, sizeof(wire_iface_t));

  iface->poll_iface_id = 16;
  iface->tx_packet_size = BLE_TX_PACKET_SIZE;
  iface->rx_packet_size = BLE_RX_PACKET_SIZE;
  iface->write = &ble_write_;
  iface->read = &ble_read_;
  iface->error = &ble_error;

  ble_start();

  ble_state_t state = {0};

  ble_get_state(&state);

  if (!state.connectable && !state.pairing) {
    if (state.peer_count > 0) {
      ble_command_t cmd = {
          .cmd_type = BLE_SWITCH_ON,
          .data = {.adv_start =
                       {
                           .name = "Trezor Bootloader",
                           .static_mac = false,
                       }},
      };
      ble_issue_command(&cmd);
    } else {
      ble_iface_start_pairing();
    }
  }
}

void ble_iface_deinit(wire_iface_t* iface) { ble_stop(); }

void ble_iface_start_pairing(void) {
  ble_command_t cmd = {
      .cmd_type = BLE_PAIRING_MODE,
      .data = {.adv_start =
                   {
                       .name = "Trezor Bootloader",
                       .static_mac = false,
                   }},
      .data_len = 0,
  };
  ble_issue_command(&cmd);
}
