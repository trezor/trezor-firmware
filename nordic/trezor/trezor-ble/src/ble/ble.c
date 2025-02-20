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

#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/uuid.h>

#include <signals/signals.h>

#include "ble_internal.h"

#define LOG_MODULE_NAME ble
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(ble_init_ok, 0, 1);

static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data,
                          uint16_t len) {
  if (!signals_is_trz_ready()) {
    LOG_INF("Trezor not ready, rejecting data");
    //    send_error_response();
    return;
  }

  char addr[BT_ADDR_LE_STR_LEN] = {0};

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, ARRAY_SIZE(addr));

  LOG_DBG("Received data from: %s, %d", addr, len);

  trz_comm_send_msg(NRF_SERVICE_BLE, data, len);
}

bool ble_init(void) {
  int err = 0;

  connection_init();
  pairing_init();

  err = bt_enable(NULL);
  if (err) {
    return false;
  }

  if (IS_ENABLED(CONFIG_SETTINGS)) {
    settings_load();
  }

  err = service_init(bt_receive_cb);
  if (err) {
    LOG_ERR("Failed to initialize UART service (err: %d)", err);
    return 0;
  }

  advertising_init();
  ble_management_init();

  k_sem_give(&ble_init_ok);
  LOG_INF("Bluetooth initialized");

  ble_management_send_status_event();

  return true;
}

void ble_write_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&ble_init_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to be sent over bluetooth */
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_BLE);

    if (service_send(connection_get_current(), buf)) {
      LOG_WRN("Failed to send data over BLE connection: %d", buf->len);
      k_free(buf);
    }

    LOG_DBG("Freeing UART data");
  }
}

K_THREAD_DEFINE(ble_write_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                ble_write_thread, NULL, NULL, NULL, 7, 0, 0);
