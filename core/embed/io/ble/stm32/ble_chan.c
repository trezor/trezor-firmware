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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/ble.h>
#include <io/ble_chan.h>
#include <io/nrf.h>
#include <io/tsqueue.h>
#include <sys/irq.h>
#include <sys/logging.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>

LOG_DECLARE(ble_chan)

static const syshandle_vmt_t ble_chan_handle_vmt;

void ble_chan_rx(ble_chan_t *chan, const uint8_t *data, uint32_t len) {
  if (!chan->initialized) {
    return;
  }

  if (len == 0) {
    // TX credit: the packet in flight has left the nRF (sent or dropped).
    chan->tx_pending = false;
    chan->stats.tx_credits++;
    return;
  }

  if (len > BLE_CHAN_PACKET_SIZE) {
    chan->stats.rx_dropped++;
    return;
  }

  if (chan->intr_cb != NULL) {
    for (uint32_t i = 0; i < len; i++) {
      if (data[i] == chan->intr_byte) {
        chan->intr_cb();
        break;
      }
    }
  }

  // Drops the packet when the queue is full; the counters tell.
  if (tsqueue_enqueue(&chan->rx_queue, data, len, NULL)) {
    chan->stats.rx_packets++;
  } else {
    chan->stats.rx_dropped++;
  }
}

// Interrupt context: the packet handed to nrf_send_msg has left the inter-MCU
// queue. It stays in flight until the nRF credits it back; only a failed
// transfer releases it here.
static void ble_chan_tx_done(nrf_status_t status, void *context) {
  ble_chan_t *chan = (ble_chan_t *)context;
  if (status != NRF_STATUS_OK) {
    chan->tx_pending = false;
    chan->stats.tx_failed++;
  }
}

bool ble_chan_init(ble_chan_t *chan, nrf_service_id_t service_id,
                   syshandle_t handle, nrf_rx_callback_t rx) {
  if (chan->initialized) {
    return true;
  }

  memset(chan, 0, sizeof(*chan));
  chan->service_id = service_id;
  chan->handle = handle;

  tsqueue_init(&chan->rx_queue, chan->rx_queue_entries,
               (uint8_t *)chan->rx_queue_buffers, BLE_CHAN_PACKET_SIZE,
               BLE_CHAN_RX_QUEUE_LEN);

  if (!nrf_register_listener(service_id, rx)) {
    goto cleanup;
  }

  if (!syshandle_register(handle, &ble_chan_handle_vmt, chan)) {
    goto cleanup;
  }

  chan->initialized = true;
  return true;

cleanup:
  nrf_unregister_listener(service_id);
  memset(chan, 0, sizeof(*chan));
  return false;
}

void ble_chan_deinit(ble_chan_t *chan) {
  if (!chan->initialized) {
    return;
  }

  syshandle_unregister(chan->handle);
  nrf_unregister_listener(chan->service_id);
  tsqueue_reset(&chan->rx_queue);

  memset(chan, 0, sizeof(*chan));
}

void ble_chan_set_intr(ble_chan_t *chan, uint8_t byte,
                       ble_chan_intr_cb_t callback) {
  irq_key_t key = irq_lock();
  chan->intr_byte = byte;
  chan->intr_cb = callback;
  irq_unlock(key);
}

void ble_chan_get_stats(const ble_chan_t *chan, ble_chan_stats_t *stats) {
  irq_key_t key = irq_lock();
  *stats = chan->stats;
  irq_unlock(key);
}

bool ble_chan_can_read(const ble_chan_t *chan) {
  if (!chan->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();
  bool can_read = !tsqueue_empty((tsqueue_t *)&chan->rx_queue);
  irq_unlock(key);

  return can_read;
}

uint32_t ble_chan_read(ble_chan_t *chan, uint8_t *data, uint16_t max_len) {
  if (!chan->initialized) {
    return 0;
  }

  if (max_len < BLE_CHAN_PACKET_SIZE) {
    // The packet would not fit; leave it in the queue rather than truncate it.
    return 0;
  }

  uint16_t read_len = 0;

  irq_key_t key = irq_lock();
  bool ok = tsqueue_dequeue(&chan->rx_queue, data, max_len, &read_len, NULL);
  irq_unlock(key);

  return ok ? read_len : 0;
}

bool ble_chan_can_write(ble_chan_t *chan) {
  if (!chan->initialized) {
    return false;
  }

  if (chan->tx_pending) {
    if (!ticks_expired(chan->tx_deadline)) {
      return false;
    }
    // No credit came back; assume the packet is lost and move on.
    chan->tx_pending = false;
    chan->stats.tx_timeouts++;
  }

  // Without a connected host the nRF would drop the packet anyway; do not
  // spend inter-MCU bandwidth on it.
  ble_state_t state = {0};
  ble_get_state(&state);

  return state.connected;
}

bool ble_chan_write(ble_chan_t *chan, const uint8_t *data, uint16_t len) {
  if (len == 0 || len > BLE_CHAN_PACKET_SIZE) {
    return false;
  }

  if (!ble_chan_can_write(chan)) {
    return false;
  }

  chan->tx_pending = true;
  chan->tx_deadline = ticks_timeout(BLE_CHAN_TX_CREDIT_TIMEOUT_MS);

  if (!nrf_send_msg(chan->service_id, data, len, ble_chan_tx_done, chan)) {
    chan->tx_pending = false;
    chan->stats.tx_failed++;
    return false;
  }

  chan->stats.tx_packets++;
  return true;
}

// ----------------------------------------------------------------------
// System handle

static void on_chan_poll(void *context, bool read_awaited, bool write_awaited) {
  ble_chan_t *chan = (ble_chan_t *)context;

  // Bring-up diagnostics: who waits on the handle, and when it is readable.
  // Logged on change only; the console handle is never awaited by a task.
  if (read_awaited != chan->read_awaited_seen) {
    chan->read_awaited_seen = read_awaited;
    LOG_DBG("handle %u read %s", (unsigned)chan->handle,
            read_awaited ? "awaited" : "not awaited");
  }

  if (read_awaited && ble_chan_can_read(chan)) {
    if (!chan->read_ready_seen) {
      chan->read_ready_seen = true;
      LOG_DBG("handle %u readable, signalling", (unsigned)chan->handle);
    }
    syshandle_signal_read_ready(chan->handle, NULL);
  } else {
    chan->read_ready_seen = false;
  }

  if (write_awaited && ble_chan_can_write(chan)) {
    syshandle_signal_write_ready(chan->handle, NULL);
  }
}

static bool on_chan_check_read_ready(void *context, systask_id_t task_id,
                                     void *param) {
  UNUSED(task_id);
  UNUSED(param);
  return ble_chan_can_read((ble_chan_t *)context);
}

static bool on_chan_check_write_ready(void *context, systask_id_t task_id,
                                      void *param) {
  UNUSED(task_id);
  UNUSED(param);
  return ble_chan_can_write((ble_chan_t *)context);
}

static ssize_t on_chan_read(void *context, void *buffer, size_t buffer_size) {
  if (buffer_size > UINT16_MAX) {
    buffer_size = UINT16_MAX;
  }
  return (ssize_t)ble_chan_read((ble_chan_t *)context, buffer,
                                (uint16_t)buffer_size);
}

static ssize_t on_chan_write(void *context, const void *data,
                             size_t data_size) {
  if (data_size > BLE_CHAN_PACKET_SIZE) {
    data_size = BLE_CHAN_PACKET_SIZE;
  }
  return ble_chan_write((ble_chan_t *)context, data, (uint16_t)data_size)
             ? (ssize_t)data_size
             : 0;
}

static const syshandle_vmt_t ble_chan_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_chan_check_read_ready,
    .check_write_ready = on_chan_check_write_ready,
    .poll = on_chan_poll,
    .read = on_chan_read,
    .write = on_chan_write,
};

#endif  // KERNEL_MODE
