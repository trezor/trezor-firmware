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

#define PPCP_SUSPEND BT_LE_CONN_PARAM(50, 100, 0, 600)
#define PPCP_HIGH_SPEED BT_LE_CONN_PARAM(12, 12, 0, 400)
#define PPCP_LOW_SPEED BT_LE_CONN_PARAM(24, 36, 0, 400)

static K_MUTEX_DEFINE(conn_mutex);

static struct bt_conn *current_conn = NULL;
static struct bt_conn *next_conn = NULL;
static bool bonded_connection = false;
static bool high_speed_requested = false;

static void show_params(struct bt_conn *conn) {
  struct bt_conn_info info;
  if (bt_conn_get_info(conn, &info) == 0 && info.type == BT_CONN_TYPE_LE) {
    const struct bt_conn_le_info *le = &info.le;
    /* Bluetooth units: interval = 1.25 ms, timeout = 10 ms */
    uint32_t interval_ms = le->interval * 125 / 100;  // 1.25 ms units → ms
    uint32_t timeout_ms = le->timeout * 10;           // 10 ms units  → ms
    LOG_INF("Conn params: interval=%u.%02u ms, latency=%u, timeout=%u ms",
            interval_ms, (le->interval * 125) % 100, le->latency, timeout_ms);
  }
}

/* Called when central updates params */
static void le_param_updated(struct bt_conn *conn, uint16_t interval,
                             uint16_t latency, uint16_t timeout) {
  uint32_t interval_ms = interval * 125 / 100;
  uint32_t timeout_ms = timeout * 10;
  LOG_INF("Params updated: interval=%u.%02u ms, latency=%u, timeout=%u ms",
          interval_ms, (interval * 125) % 100, latency, timeout_ms);
}

static void connection_update_params(void) {
  struct bt_conn *conn = connection_get_current();
  if (conn != NULL) {
    const struct bt_le_conn_param *param =
        high_speed_requested ? PPCP_HIGH_SPEED : PPCP_LOW_SPEED;
    bt_conn_le_param_update(conn, param);
  }
}

void connected(struct bt_conn *conn, uint8_t err) {
  char addr[BT_ADDR_LE_STR_LEN];

  if (err) {
    LOG_ERR("Connection failed (err %u)", err);
    return;
  }

  show_params(conn);

  // Prefer 2M both directions; 0 options = no specific constraints
  // const struct bt_conn_le_phy_param phy_2m = {
  //    .options = 0,
  //    .pref_tx_phy = BT_GAP_LE_PHY_2M,
  //    .pref_rx_phy = BT_GAP_LE_PHY_2M,
  //};
  //
  // bt_conn_le_phy_update(conn, &phy_2m);

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
  LOG_INF("Connected %s", addr);

  if (current_conn != NULL) {
    if (next_conn) {
      // should not happen as we only allow two connections, but just in case
      // deref
      LOG_WRN("Replacing next_conn with current_conn");
      bt_conn_unref(next_conn);
    }

    next_conn = bt_conn_ref(conn);
    connection_disconnect();
  } else {
    current_conn = bt_conn_ref(conn);
  }
  k_mutex_lock(&conn_mutex, K_FOREVER);

  connection_update_params();

  k_mutex_unlock(&conn_mutex);

  ble_reconfigure_tx_power();

  advertising_stop();

  ble_management_send_status_event();
}

void disconnected(struct bt_conn *conn, uint8_t reason) {
  char addr[BT_ADDR_LE_STR_LEN];

  bonded_connection = false;

  advertising_stop();

  pairing_reset();

  if (current_conn && conn == current_conn) {
    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
    LOG_INF("Disconnected: %s (reason %u)", addr, reason);
    bt_conn_unref(current_conn);
    current_conn = NULL;
  }

  if (next_conn && current_conn == NULL) {
    current_conn = next_conn;
    next_conn = NULL;
  } else if (next_conn) {
    bt_conn_unref(next_conn);
    next_conn = NULL;
  }

  ble_management_send_status_event();
}

static void security_changed(struct bt_conn *conn, bt_security_t level,
                             enum bt_security_err err) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  if (!err) {
    LOG_INF("Security changed: %s level %u", addr, level);

    if (level == BT_SECURITY_L4) {
      bonded_connection = true;
    } else {
      bonded_connection = false;
    }
  } else {
    bonded_connection = false;
    LOG_WRN("Security failed: %s level %u err %d", addr, level, err);
  }
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
    .security_changed = security_changed,
    .le_param_updated = le_param_updated,
};

bool connection_init(void) { return true; }

bool connection_is_connected(void) { return current_conn != NULL; }

void connection_disconnect(void) {
  if (current_conn) {
    LOG_INF("Internal disconnect request");
    bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
  }
}

struct bt_conn *connection_get_current(void) { return current_conn; }

void connection_suspend(void) {
  k_mutex_lock(&conn_mutex, K_FOREVER);
  struct bt_conn *conn = connection_get_current();

  if (conn != NULL) {
    const struct bt_le_conn_param *param = PPCP_SUSPEND;
    bt_conn_le_param_update(conn, param);
  }

  k_mutex_unlock(&conn_mutex);
}

void connection_resume(void) {
  k_mutex_lock(&conn_mutex, K_FOREVER);
  connection_update_params();
  k_mutex_unlock(&conn_mutex);
}

bool connection_is_bonded(void) { return bonded_connection; }

bool connection_is_high_speed(void) { return high_speed_requested; }

void connection_set_high_speed(void) {
  k_mutex_lock(&conn_mutex, K_FOREVER);

  high_speed_requested = true;

  connection_update_params();
  k_mutex_unlock(&conn_mutex);
}

void connection_set_low_speed(void) {
  k_mutex_lock(&conn_mutex, K_FOREVER);

  high_speed_requested = false;

  connection_update_params();

  k_mutex_unlock(&conn_mutex);
}
