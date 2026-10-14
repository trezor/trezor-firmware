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
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "aux_chan.h"
#include "ble_internal.h"

LOG_MODULE_REGISTER(ble_aux_chan);

BUILD_ASSERT(AUX_CHAN_PACKET_SIZE <= PACKET_DATA_SIZE,
             "channel packet must fit an inter-MCU frame");

// How long to keep retrying a notification when the BLE stack is out of TX
// buffers before giving the packet up.
#define AUX_CHAN_NOTIFY_RETRY_MS 10
#define AUX_CHAN_NOTIFY_MAX_WAIT_MS 2000

// Tells the STM32 the packet in flight is done with (sent or dropped).
static void aux_chan_send_credit(const aux_chan_t *chan) {
  static const uint8_t none[1] = {0};
  if (!trz_comm_send_msg(chan->service_id, none, 0)) {
    LOG_WRN("%s: credit not sent", chan->name);
  }
}

int aux_chan_init(const aux_chan_t *chan) {
  int err = bt_gatt_service_register(chan->svc);

  if (err) {
    LOG_ERR("%s: failed to register service (err: %d)", chan->name, err);
    return err;
  }

  k_sem_give(chan->ready);
  LOG_INF("%s: service registered", chan->name);

  return 0;
}

ssize_t aux_chan_on_receive(const aux_chan_t *chan, const void *buf,
                            uint16_t len) {
  if (len == 0) {
    // An empty frame is the TX credit on the inter-MCU link; never forward one.
    return len;
  }

  if (len > AUX_CHAN_PACKET_SIZE) {
    LOG_WRN("%s: write too long (%u bytes), dropping", chan->name, len);
    return len;
  }

  if (!trz_comm_send_msg(chan->service_id, buf, len)) {
    LOG_WRN("%s: write not forwarded (%u bytes)", chan->name, len);
  }

  return len;
}

void aux_chan_sent(const aux_chan_t *chan, void *user_data) {
  k_free(user_data);
  aux_chan_send_credit(chan);
}

// STM32 -> host. Takes ownership of `data` on success (freed in the sent
// callback); the caller keeps ownership on failure.
static int aux_chan_send(const aux_chan_t *chan, struct bt_conn *conn,
                         trz_packet_t *data) {
  if (!bt_gatt_is_subscribed(conn, chan->tx_attr, BT_GATT_CCC_NOTIFY)) {
    return -EINVAL;
  }

  struct bt_gatt_notify_params params = {
      .attr = chan->tx_attr,
      .data = data->data,
      .len = data->len,
      .func = chan->on_sent,
      .user_data = data,
  };

  return bt_gatt_notify_cb(conn, &params);
}

void aux_chan_write_thread(const aux_chan_t *chan) {
  k_sem_take(chan->ready, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(chan->service_id);

    if (buf->len == 0 || buf->len > AUX_CHAN_PACKET_SIZE) {
      LOG_WRN("%s: message of %u bytes, dropping", chan->name, buf->len);
      k_free(buf);
      aux_chan_send_credit(chan);
      continue;
    }

    struct bt_conn *conn = connection_get_current();

    if (conn == NULL) {
      // Nobody is listening: drop it and let the STM32 move on.
      k_free(buf);
      aux_chan_send_credit(chan);
      continue;
    }

    // Out of TX buffers means the host is slower than we are; wait for the
    // stack to drain rather than dropping, but not forever.
    int err;
    int waited_ms = 0;
    do {
      err = aux_chan_send(chan, conn, buf);
      if (err != -ENOMEM) {
        break;
      }
      k_sleep(K_MSEC(AUX_CHAN_NOTIFY_RETRY_MS));
      waited_ms += AUX_CHAN_NOTIFY_RETRY_MS;
    } while (waited_ms < AUX_CHAN_NOTIFY_MAX_WAIT_MS);

    if (err) {
      LOG_DBG("%s: message not sent (err: %d)", chan->name, err);
      k_free(buf);
      aux_chan_send_credit(chan);
    }
    // On success the credit follows from the sent callback.
  }
}
