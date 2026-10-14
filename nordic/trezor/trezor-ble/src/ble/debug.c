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

// BLE debuglink service.
//
// The debuglink's own GATT service for debug firmware on boards without USB:
// the counterpart of the USB debug interface. It carries the debuglink's
// codec v1 reports, 244 bytes each, between the STM32 and a bonded host,
// separate from the wire-protocol service (THP) and from the console. The
// nRF does not interpret the bytes. Framing and flow control are the
// auxiliary channel's (aux_chan.h); this file is the instance: its UUIDs,
// attribute table, thread and inter-MCU service id (NRF_SERVICE_DEBUG).
//
// Only debug images set CONFIG_TRZ_DEBUG_LINK. A production nRF must never
// expose this service: debug STM32 firmware answers debuglink requests from
// any bonded host.

#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "aux_chan.h"
#include "ble_internal.h"

LOG_MODULE_REGISTER(ble_debug);

static K_SEM_DEFINE(debug_ready, 0, 1);

static const aux_chan_t debug_chan;

static void debug_ccc_cfg_changed(const struct bt_gatt_attr *attr,
                                  uint16_t value) {
  LOG_DBG("Debuglink notifications turned %s",
          value == BT_GATT_CCC_NOTIFY ? "on" : "off");
}

static ssize_t debug_on_receive(struct bt_conn *conn,
                                const struct bt_gatt_attr *attr,
                                const void *buf, uint16_t len, uint16_t offset,
                                uint8_t flags) {
  return aux_chan_on_receive(&debug_chan, buf, len);
}

static void debug_on_sent(struct bt_conn *conn, void *user_data) {
  aux_chan_sent(&debug_chan, user_data);
}

static struct bt_gatt_attr debug_attrs[] = {
    BT_GATT_PRIMARY_SERVICE(BT_UUID_TRZ_DEBUG_SERVICE),
    BT_GATT_CHARACTERISTIC(BT_UUID_TRZ_DEBUG_TX, BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, NULL, NULL, NULL),
    BT_GATT_CCC(debug_ccc_cfg_changed,
                BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT),
    BT_GATT_CHARACTERISTIC(
        BT_UUID_TRZ_DEBUG_RX,
        BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
        BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT, NULL,
        debug_on_receive, NULL),
};

static struct bt_gatt_service debug_svc = BT_GATT_SERVICE(debug_attrs);

// Index of the TX characteristic value attribute: [0] service, [1] TX
// declaration, [2] TX value, [3] CCC, [4] RX declaration, [5] RX value.
static const aux_chan_t debug_chan = {
    .name = "debuglink",
    .service_id = NRF_SERVICE_DEBUG,
    .svc = &debug_svc,
    .tx_attr = &debug_attrs[2],
    .on_sent = debug_on_sent,
    .ready = &debug_ready,
};

int debug_init(void) { return aux_chan_init(&debug_chan); }

static void debug_write_thread(void) { aux_chan_write_thread(&debug_chan); }

K_THREAD_DEFINE(debug_write_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                debug_write_thread, NULL, NULL, NULL, 7, 0, 0);
