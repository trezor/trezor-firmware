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

// BLE console service.
//
// A second GATT service, separate from the wire-protocol service in
// service.c, that carries an opaque byte console between the STM32 and a
// bonded host: the prodtest CLI on production-test firmware, debug logs on
// debug firmware. The nRF does not interpret the bytes. Framing and flow
// control are the auxiliary channel's (aux_chan.h); this file is the
// instance: its UUIDs, attribute table, thread and inter-MCU service id
// (NRF_SERVICE_CONSOLE).
//
// Today the service is registered unconditionally whenever CONFIG_TRZ_CONSOLE
// is set; production STM32 firmware simply never routes it. A later version
// can register it only on MGMT_CMD_CONSOLE_ENABLE.

#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "aux_chan.h"
#include "ble_internal.h"

LOG_MODULE_REGISTER(ble_console);

static K_SEM_DEFINE(console_ready, 0, 1);

static const aux_chan_t console_chan;

static void console_ccc_cfg_changed(const struct bt_gatt_attr *attr,
                                    uint16_t value) {
  LOG_DBG("Console notifications turned %s",
          value == BT_GATT_CCC_NOTIFY ? "on" : "off");
}

static ssize_t console_on_receive(struct bt_conn *conn,
                                  const struct bt_gatt_attr *attr,
                                  const void *buf, uint16_t len,
                                  uint16_t offset, uint8_t flags) {
  return aux_chan_on_receive(&console_chan, buf, len);
}

static void console_on_sent(struct bt_conn *conn, void *user_data) {
  aux_chan_sent(&console_chan, user_data);
}

static struct bt_gatt_attr console_attrs[] = {
    BT_GATT_PRIMARY_SERVICE(BT_UUID_TRZ_CONSOLE_SERVICE),
    BT_GATT_CHARACTERISTIC(BT_UUID_TRZ_CONSOLE_TX, BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, NULL, NULL, NULL),
    BT_GATT_CCC(console_ccc_cfg_changed,
                BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT),
    BT_GATT_CHARACTERISTIC(
        BT_UUID_TRZ_CONSOLE_RX,
        BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
        BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT, NULL,
        console_on_receive, NULL),
};

static struct bt_gatt_service console_svc = BT_GATT_SERVICE(console_attrs);

// Index of the TX characteristic value attribute: [0] service, [1] TX
// declaration, [2] TX value, [3] CCC, [4] RX declaration, [5] RX value.
static const aux_chan_t console_chan = {
    .name = "console",
    .service_id = NRF_SERVICE_CONSOLE,
    .svc = &console_svc,
    .tx_attr = &console_attrs[2],
    .on_sent = console_on_sent,
    .ready = &console_ready,
};

int console_init(void) { return aux_chan_init(&console_chan); }

static void console_write_thread(void) { aux_chan_write_thread(&console_chan); }

K_THREAD_DEFINE(console_write_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                console_write_thread, NULL, NULL, NULL, 7, 0, 0);
