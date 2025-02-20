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

#include <zephyr/kernel.h>
#include <zephyr/types.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/uuid.h>

#include <zephyr/logging/log.h>

#include "ble_internal.h"

#define LOG_MODULE_NAME ble_connection
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static struct bt_conn *current_conn;

void connected(struct bt_conn *conn, uint8_t err) {
  char addr[BT_ADDR_LE_STR_LEN];

  if (err) {
    LOG_ERR("Connection failed (err %u)", err);
    return;
  }

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
  LOG_INF("Connected %s", addr);

  current_conn = bt_conn_ref(conn);

  //  struct bt_le_conn_param params = BT_LE_CONN_PARAM_INIT(6,6,0,400);
  //
  //  bt_conn_le_param_update(conn, &params);

  // err = bt_conn_le_phy_update(current_conn, BT_CONN_LE_PHY_PARAM_2M);
  // if (err) {
  //   LOG_ERR("Phy update request failed: %d",  err);
  // }

  ble_management_send_status_event();
}

void disconnected(struct bt_conn *conn, uint8_t reason) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  LOG_INF("Disconnected: %s (reason %u)", addr, reason);

  pairing_reset();

  if (current_conn) {
    bt_conn_unref(current_conn);
    current_conn = NULL;
  }

  ble_management_send_status_event();
}

static void security_changed(struct bt_conn *conn, bt_security_t level,
                             enum bt_security_err err) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  if (!err) {
    LOG_INF("Security changed: %s level %u", addr, level);
  } else {
    LOG_WRN("Security failed: %s level %u err %d", addr, level, err);
  }
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
    .security_changed = security_changed,
};

bool connection_init(void) { return true; }

bool connection_is_connected(void) { return current_conn != NULL; }

void connection_disconnect(void) {
  if (current_conn) {
    LOG_INF("Remotely disconnected");
    bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
    bt_conn_unref(current_conn);
  }
}

struct bt_conn *connection_get_current(void) { return current_conn; }
