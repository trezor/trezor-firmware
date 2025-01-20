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

#define LOG_MODULE_NAME ble_pairing
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static struct bt_conn *auth_conn;

void passkey_to_str(uint8_t buf[6], unsigned int passkey) {
  buf[5] = (passkey % 10) + '0';
  buf[4] = ((passkey / 10) % 10) + '0';
  buf[3] = ((passkey / 100) % 10) + '0';
  buf[2] = ((passkey / 1000) % 10) + '0';
  buf[1] = ((passkey / 10000) % 10) + '0';
  buf[0] = ((passkey / 100000) % 10) + '0';
}

void auth_passkey_display(struct bt_conn *conn, unsigned int passkey) {}

void auth_passkey_confirm(struct bt_conn *conn, unsigned int passkey) {
  char addr[BT_ADDR_LE_STR_LEN];

  auth_conn = bt_conn_ref(conn);

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  uint8_t passkey_str[6];
  passkey_to_str(passkey_str, passkey);
  management_send_pairing_request_event(passkey_str, 6);

  management_send_status_event();
}

void pairing_auth_cancel(struct bt_conn *conn) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  connection_disconnect();

  management_send_pairing_cancelled_event();
  management_send_status_event();

  LOG_INF("Pairing cancelled: %s", addr);
}

static struct bt_conn_auth_cb conn_auth_callbacks = {
    //  .pairing_accept = pairing_accept,
    .passkey_display = auth_passkey_display,
    .passkey_confirm = auth_passkey_confirm,
    .cancel = pairing_auth_cancel,
};

void pairing_complete(struct bt_conn *conn, bool bonded) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  LOG_INF("Pairing completed: %s, bonded: %d", addr, bonded);
}

void pairing_failed(struct bt_conn *conn, enum bt_security_err reason) {
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  LOG_INF("Pairing failed conn: %s, reason %d", addr, reason);
}

static struct bt_conn_auth_info_cb conn_auth_info_callbacks = {
    .pairing_complete = pairing_complete, .pairing_failed = pairing_failed};

void pairing_num_comp_reply(bool accept) {
  if (auth_conn != NULL) {
    if (accept) {
      bt_conn_auth_passkey_confirm(auth_conn);
      LOG_INF("Numeric Match, conn %p", (void *)auth_conn);
    } else {
      bt_conn_auth_cancel(auth_conn);
      LOG_INF("Numeric Reject, conn %p", (void *)auth_conn);
      bt_conn_disconnect(auth_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
    }

    bt_conn_unref(auth_conn);
    auth_conn = NULL;
  }
}

void pairing_reset(void) {
  if (auth_conn) {
    bt_conn_unref(auth_conn);
    auth_conn = NULL;
  }
}

bool pairing_init(void) {
  int err = bt_conn_auth_cb_register(&conn_auth_callbacks);
  if (err) {
    printk("Failed to register authorization callbacks.\n");
    return false;
  }

  err = bt_conn_auth_info_cb_register(&conn_auth_info_callbacks);
  if (err) {
    printk("Failed to register authorization info callbacks.\n");
    return false;
  }

  return true;
}
