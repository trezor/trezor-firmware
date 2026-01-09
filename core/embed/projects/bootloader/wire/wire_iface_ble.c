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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "wire_iface_ble.h"

#include <io/ble.h>
#include <rtl/strutils.h>
#include <sys/rng.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

static wire_iface_t g_ble_iface = {0};

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
      return 0;
    }
    if (!is_connected()) {
      return 0;
    }
    if (ble_can_read()) {
      break;
    }
  }

  int r = ble_read(buffer, buffer_size);

  return r;
}

static void ble_error(void) {
  error_shutdown_ex("Connection Error",
                    "Move your Trezor closer to your computer/phone.", NULL);
}

wire_iface_t* ble_iface_init(void) {
  wire_iface_t* iface = &g_ble_iface;

  if (iface->initialized) {
    return iface;
  }

  memset(iface, 0, sizeof(wire_iface_t));

  iface->poll_iface_id = SYSHANDLE_BLE_IFACE_0;
  iface->tx_packet_size = BLE_TX_PACKET_SIZE;
  iface->rx_packet_size = BLE_RX_PACKET_SIZE;
  iface->write = &ble_write_;
  iface->read = &ble_read_;
  iface->error = &ble_error;
  iface->wireless = true;

  ble_start();

  ble_state_t state = {0};

  ble_get_state(&state);

  if (!state.connectable && !state.pairing) {
    if (state.peer_count > 0) {
      ble_set_name((const uint8_t*)MODEL_FULL_NAME, sizeof(MODEL_FULL_NAME));
      ble_switch_on();
    }
  }

  iface->initialized = true;

  return iface;
}

void ble_iface_deinit(void) {
  wire_iface_t* iface = &g_ble_iface;

  if (!iface->initialized) {
    return;
  }

  ble_keep_connection();
  ble_stop();

  memset(iface, 0, sizeof(wire_iface_t));
}

void ble_iface_end_pairing(void) {
  ble_state_t state = {0};

  ble_reject_pairing();
  ble_set_name((const uint8_t*)MODEL_FULL_NAME, sizeof(MODEL_FULL_NAME));

  ble_get_state(&state);

  if (state.peer_count > 0) {
    ble_switch_on();
  } else {
    ble_switch_off();
  }
}

static char get_random_from_charset(const char* charset) {
  const size_t max_index = strlen(charset);

  if (max_index == 0) {
    return '\0';
  }

  return charset[rng_get() % max_index];
}

bool ble_iface_start_pairing(void) {
  ble_state_t state = {0};

  ble_get_state(&state);

  uint16_t retry_cnt = 0;

  static const char DIGITS[] = "0123456789";
  static const char UPPERCASE[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

  char suffix[] = {
      ' ',
      '(',
      get_random_from_charset(UPPERCASE),
      get_random_from_charset(DIGITS),
      get_random_from_charset(UPPERCASE),
      ')',
      '\0',
  };

  char adv_name[BLE_ADV_NAME_LEN] = "";
  cstr_append(adv_name, sizeof(adv_name), MODEL_FULL_NAME);
  cstr_append(adv_name, sizeof(adv_name), suffix);

  if (!ble_enter_pairing_mode((const uint8_t*)adv_name,
                              strnlen(adv_name, BLE_ADV_NAME_LEN))) {
    return false;
  }

  retry_cnt = 0;
  ble_get_state(&state);
  while (!state.pairing && retry_cnt < 10) {
    systick_delay_ms(20);
    ble_get_state(&state);
    retry_cnt++;
  }

  if (!state.pairing) {
    ble_iface_end_pairing();
    return false;
  }

  return true;
}

wire_iface_t* ble_iface_get(void) {
  if (!g_ble_iface.initialized) {
    return NULL;
  }
  return &g_ble_iface;
}

#endif
