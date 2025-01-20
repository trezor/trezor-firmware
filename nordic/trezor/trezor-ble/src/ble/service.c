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

#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>

#include <zephyr/logging/log.h>

#include "ble_internal.h"

LOG_MODULE_REGISTER(ble_service);

static service_received_cb received_cb;

static void service_ccc_cfg_changed(const struct bt_gatt_attr *attr,
                                    uint16_t value) {
  LOG_DBG("Notification has been turned %s",
          value == BT_GATT_CCC_NOTIFY ? "on" : "off");
}

static ssize_t on_receive(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                          const void *buf, uint16_t len, uint16_t offset,
                          uint8_t flags) {
  LOG_DBG("Received data, handle %d, conn %p", attr->handle, (void *)conn);

  if (received_cb != NULL) {
    received_cb(conn, buf, len);
  }
  return len;
}

static void on_sent(struct bt_conn *conn, void *user_data) {
  trz_packet_t *data = (trz_packet_t *)user_data;

  k_free(data);

  LOG_DBG("Data send, conn %p", (void *)conn);
}

/* Trezor Service Declaration */
BT_GATT_SERVICE_DEFINE(
    trz_svc, BT_GATT_PRIMARY_SERVICE(BT_UUID_TRZ_SERVICE),
    BT_GATT_CHARACTERISTIC(BT_UUID_TRZ_TX, BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, NULL, NULL, NULL),
    BT_GATT_CCC(service_ccc_cfg_changed,
                BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT),
    BT_GATT_CHARACTERISTIC(BT_UUID_TRZ_RX,
                           BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
                           BT_GATT_PERM_READ_ENCRYPT |
                               BT_GATT_PERM_WRITE_ENCRYPT,
                           NULL, on_receive, NULL), );

int service_init(service_received_cb callback) {
  received_cb = callback;
  return 0;
}

int service_send(struct bt_conn *conn, trz_packet_t *data) {
  struct bt_gatt_notify_params params = {0};
  const struct bt_gatt_attr *attr = &trz_svc.attrs[2];

  params.attr = attr;
  params.data = data->data;
  params.len = data->len;
  params.func = on_sent;
  params.user_data = (void *)data;

  if (conn && bt_gatt_is_subscribed(conn, attr, BT_GATT_CCC_NOTIFY)) {
    return bt_gatt_notify_cb(conn, &params);
  } else {
    return -EINVAL;
  }
}
