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
// debug firmware. The nRF does not interpret the bytes.
//
// Both characteristics are variable-length up to CONSOLE_PACKET_SIZE. On the
// inter-MCU link the console has its own service id (NRF_SERVICE_CONSOLE);
// the SPI frame stays fixed-size and carries the real length in its header,
// so nothing here pads or strips anything. Unlike the wire-protocol service
// there is no peer-address prefix: there is a single connection and the
// console has no per-peer semantics.
//
// Flow control: the STM32 keeps one console packet in flight and waits for a
// credit before sending the next. The credit is an empty frame on the console
// service id, sent here once the notification has left (or once the packet
// had to be dropped), so the STM32 can never outrun the air interface and
// fill the heap-backed FIFO. Empty frames therefore never carry data in
// either direction; an empty GATT write is discarded.
//
// The service is registered at runtime (bt_gatt_service_register) rather
// than with BT_GATT_SERVICE_DEFINE so that a later version can register it
// only when the STM32 asks for it (MGMT_CMD_CONSOLE_ENABLE). Today it is
// registered unconditionally whenever CONFIG_TRZ_CONSOLE is set; production
// STM32 firmware simply never routes it.

#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "ble_internal.h"

LOG_MODULE_REGISTER(ble_console);

// Largest payload in either direction. Bounded by the ATT MTU on the air side
// (CONFIG_BT_L2CAP_TX_MTU - 3) and by the inter-MCU frame on the other.
#define CONSOLE_PACKET_SIZE BLE_TX_PACKET_SIZE

BUILD_ASSERT(CONSOLE_PACKET_SIZE <= PACKET_DATA_SIZE,
             "console packet must fit an inter-MCU frame");

static K_SEM_DEFINE(console_ready, 0, 1);

// How long to keep retrying a notification when the BLE stack is out of TX
// buffers before giving the packet up.
#define CONSOLE_NOTIFY_RETRY_MS 10
#define CONSOLE_NOTIFY_MAX_WAIT_MS 2000

// Tells the STM32 the packet in flight is done with (sent or dropped).
static void console_send_credit(void) {
  static const uint8_t none[1] = {0};
  if (!trz_comm_send_msg(NRF_SERVICE_CONSOLE, none, 0)) {
    LOG_WRN("Console credit not sent");
  }
}

static void console_ccc_cfg_changed(const struct bt_gatt_attr *attr,
                                    uint16_t value) {
  LOG_DBG("Console notifications turned %s",
          value == BT_GATT_CCC_NOTIFY ? "on" : "off");
}

// Host -> STM32. Forwards exactly `len` bytes; the frame header carries the
// length, so short writes arrive on the STM32 as short messages.
static ssize_t console_on_receive(struct bt_conn *conn,
                                  const struct bt_gatt_attr *attr,
                                  const void *buf, uint16_t len,
                                  uint16_t offset, uint8_t flags) {
  if (len == 0) {
    // An empty frame is the TX credit on the inter-MCU link; never forward one.
    return len;
  }

  if (len > CONSOLE_PACKET_SIZE) {
    LOG_WRN("Console write too long (%u bytes), dropping", len);
    return len;
  }

  if (!trz_comm_send_msg(NRF_SERVICE_CONSOLE, buf, len)) {
    LOG_WRN("Console write not forwarded (%u bytes)", len);
  }

  return len;
}

static void console_on_sent(struct bt_conn *conn, void *user_data) {
  k_free(user_data);
  console_send_credit();
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

// Index of the TX characteristic value attribute: [0] service, [1] TX
// declaration, [2] TX value, [3] CCC, [4] RX declaration, [5] RX value.
#define CONSOLE_TX_VALUE_ATTR (&console_attrs[2])

static struct bt_gatt_service console_svc = BT_GATT_SERVICE(console_attrs);

int console_init(void) {
  int err = bt_gatt_service_register(&console_svc);

  if (err) {
    LOG_ERR("Failed to register console service (err: %d)", err);
    return err;
  }

  k_sem_give(&console_ready);
  LOG_INF("Console service registered");

  return 0;
}

// STM32 -> host. Takes ownership of `data` on success (freed in
// console_on_sent); the caller keeps ownership on failure.
static int console_send(struct bt_conn *conn, trz_packet_t *data) {
  const struct bt_gatt_attr *attr = CONSOLE_TX_VALUE_ATTR;

  if (!bt_gatt_is_subscribed(conn, attr, BT_GATT_CCC_NOTIFY)) {
    return -EINVAL;
  }

  struct bt_gatt_notify_params params = {
      .attr = attr,
      .data = data->data,
      .len = data->len,
      .func = console_on_sent,
      .user_data = data,
  };

  return bt_gatt_notify_cb(conn, &params);
}

static void console_write_thread(void) {
  k_sem_take(&console_ready, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_CONSOLE);

    if (buf->len == 0 || buf->len > CONSOLE_PACKET_SIZE) {
      LOG_WRN("Console message of %u bytes, dropping", buf->len);
      k_free(buf);
      console_send_credit();
      continue;
    }

    struct bt_conn *conn = connection_get_current();

    if (conn == NULL) {
      // The console is lossy by design: nobody is listening, drop it.
      k_free(buf);
      console_send_credit();
      continue;
    }

    // Out of TX buffers means the host is slower than we are; wait for the
    // stack to drain rather than dropping, but not forever.
    int err;
    int waited_ms = 0;
    do {
      err = console_send(conn, buf);
      if (err != -ENOMEM) {
        break;
      }
      k_sleep(K_MSEC(CONSOLE_NOTIFY_RETRY_MS));
      waited_ms += CONSOLE_NOTIFY_RETRY_MS;
    } while (waited_ms < CONSOLE_NOTIFY_MAX_WAIT_MS);

    if (err) {
      LOG_DBG("Console message not sent (err: %d)", err);
      k_free(buf);
      console_send_credit();
    }
    // On success the credit follows from console_on_sent().
  }
}

K_THREAD_DEFINE(console_write_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                console_write_thread, NULL, NULL, NULL, 7, 0, 0);
