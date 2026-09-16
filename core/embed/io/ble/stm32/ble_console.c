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
#include <io/ble_console.h>
#include <io/nrf.h>
#include <io/tsqueue.h>
#include <sys/irq.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>
#include <sys/systimer.h>

// Inbound packets buffered until the consumer reads them. 16 packets is a
// little under 4 KB, the same depth the wire-protocol interface uses.
#define RX_QUEUE_LEN 16

// Retry period for the console-enable request until the nRF link is up.
#define ENABLE_RETRY_MS 100

// A packet in flight is given up when the nRF has not credited it back within
// this time (link down, nRF rebooted); the console is lossy by design.
#define TX_CREDIT_TIMEOUT_MS 1000

typedef struct {
  bool initialized;

  uint8_t rx_queue_buffers[RX_QUEUE_LEN][BLE_CONSOLE_PACKET_SIZE];
  tsqueue_entry_t rx_queue_entries[RX_QUEUE_LEN];
  tsqueue_t rx_queue;

  // One console packet in flight until the nRF credits it back or the
  // deadline passes
  volatile bool tx_pending;
  uint32_t tx_deadline;

  uint8_t intr_byte;
  ble_console_intr_cb_t intr_cb;

  // Sends MGMT_CMD_CONSOLE_ENABLE once the nRF link accepts messages
  systimer_t *enable_timer;
  bool enable_sent;

  ble_console_stats_t stats;
} ble_console_driver_t;

static ble_console_driver_t g_ble_console = {0};

static const syshandle_vmt_t ble_console_handle_vmt;

// Interrupt context: inter-MCU frame on NRF_SERVICE_CONSOLE
static void ble_console_rx(const uint8_t *data, uint32_t len) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->initialized) {
    return;
  }

  if (len == 0) {
    // TX credit: the packet in flight has left the nRF (sent or dropped).
    drv->tx_pending = false;
    drv->stats.tx_credits++;
    return;
  }

  if (len > BLE_CONSOLE_PACKET_SIZE) {
    drv->stats.rx_dropped++;
    return;
  }

  if (drv->intr_cb != NULL) {
    for (uint32_t i = 0; i < len; i++) {
      if (data[i] == drv->intr_byte) {
        drv->intr_cb();
        break;
      }
    }
  }

  // Drops the packet when the queue is full; the console is lossy.
  if (tsqueue_enqueue(&drv->rx_queue, data, len, NULL)) {
    drv->stats.rx_packets++;
  } else {
    drv->stats.rx_dropped++;
  }
}

// Interrupt context: the packet handed to nrf_send_msg has left the inter-MCU
// queue. It stays in flight until the nRF credits it back; only a failed
// transfer releases it here.
static void ble_console_tx_done(nrf_status_t status, void *context) {
  ble_console_driver_t *drv = (ble_console_driver_t *)context;
  if (status != NRF_STATUS_OK) {
    drv->tx_pending = false;
    drv->stats.tx_failed++;
  }
}

// Interrupt context: one-shot, re-armed until the request goes out. The nRF
// currently registers the console service unconditionally and treats the
// request as a no-op; it is sent so that a later nRF version can register the
// service only on request without an STM32 change.
static void ble_console_enable_timer(void *context) {
  ble_console_driver_t *drv = (ble_console_driver_t *)context;

  if (drv->enable_sent) {
    return;
  }

  if (nrf_enable_console()) {
    drv->enable_sent = true;
  } else {
    systimer_set(drv->enable_timer, ENABLE_RETRY_MS);
  }
}

bool ble_console_init(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(*drv));

  tsqueue_init(&drv->rx_queue, drv->rx_queue_entries,
               (uint8_t *)drv->rx_queue_buffers, BLE_CONSOLE_PACKET_SIZE,
               RX_QUEUE_LEN);

  drv->enable_timer = systimer_create(ble_console_enable_timer, drv);
  if (drv->enable_timer == NULL) {
    goto cleanup;
  }

  if (!nrf_register_listener(NRF_SERVICE_CONSOLE, ble_console_rx)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_BLE_CONSOLE, &ble_console_handle_vmt,
                          drv)) {
    goto cleanup;
  }

  drv->initialized = true;

  systimer_set(drv->enable_timer, ENABLE_RETRY_MS);

  return true;

cleanup:
  nrf_unregister_listener(NRF_SERVICE_CONSOLE);
  if (drv->enable_timer != NULL) {
    systimer_delete(drv->enable_timer);
  }
  memset(drv, 0, sizeof(*drv));
  return false;
}

void ble_console_deinit(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->initialized) {
    return;
  }

  syshandle_unregister(SYSHANDLE_BLE_CONSOLE);
  nrf_unregister_listener(NRF_SERVICE_CONSOLE);
  systimer_delete(drv->enable_timer);
  tsqueue_reset(&drv->rx_queue);

  memset(drv, 0, sizeof(*drv));
}

void ble_console_set_intr(uint8_t byte, ble_console_intr_cb_t callback) {
  ble_console_driver_t *drv = &g_ble_console;

  irq_key_t key = irq_lock();
  drv->intr_byte = byte;
  drv->intr_cb = callback;
  irq_unlock(key);
}

bool ble_console_can_read(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();
  bool can_read = !tsqueue_empty(&drv->rx_queue);
  irq_unlock(key);

  return can_read;
}

uint32_t ble_console_read(uint8_t *data, uint16_t max_len) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->initialized) {
    return 0;
  }

  if (max_len < BLE_CONSOLE_PACKET_SIZE) {
    // The packet would not fit; leave it in the queue rather than truncate it.
    return 0;
  }

  uint16_t read_len = 0;

  irq_key_t key = irq_lock();
  bool ok = tsqueue_dequeue(&drv->rx_queue, data, max_len, &read_len, NULL);
  irq_unlock(key);

  return ok ? read_len : 0;
}

bool ble_console_can_write(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->initialized) {
    return false;
  }

  if (drv->tx_pending) {
    if (!ticks_expired(drv->tx_deadline)) {
      return false;
    }
    // No credit came back; assume the packet is lost and move on.
    drv->tx_pending = false;
    drv->stats.tx_timeouts++;
  }

  // Without a connected host the nRF would drop the packet anyway; do not
  // spend inter-MCU bandwidth on it.
  ble_state_t state = {0};
  ble_get_state(&state);

  return state.connected;
}

bool ble_console_write(const uint8_t *data, uint16_t len) {
  ble_console_driver_t *drv = &g_ble_console;

  if (len == 0 || len > BLE_CONSOLE_PACKET_SIZE) {
    return false;
  }

  if (!ble_console_can_write()) {
    return false;
  }

  drv->tx_pending = true;
  drv->tx_deadline = ticks_timeout(TX_CREDIT_TIMEOUT_MS);

  if (!nrf_send_msg(NRF_SERVICE_CONSOLE, data, len, ble_console_tx_done, drv)) {
    drv->tx_pending = false;
    drv->stats.tx_failed++;
    return false;
  }

  drv->stats.tx_packets++;
  return true;
}

void ble_console_get_stats(ble_console_stats_t *stats) {
  ble_console_driver_t *drv = &g_ble_console;

  irq_key_t key = irq_lock();
  *stats = drv->stats;
  irq_unlock(key);
}

// ----------------------------------------------------------------------
// System handle

static void on_console_poll(void *context, bool read_awaited,
                            bool write_awaited) {
  UNUSED(context);

  if (read_awaited && ble_console_can_read()) {
    syshandle_signal_read_ready(SYSHANDLE_BLE_CONSOLE, NULL);
  }

  if (write_awaited && ble_console_can_write()) {
    syshandle_signal_write_ready(SYSHANDLE_BLE_CONSOLE, NULL);
  }
}

static bool on_console_check_read_ready(void *context, systask_id_t task_id,
                                        void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);
  return ble_console_can_read();
}

static bool on_console_check_write_ready(void *context, systask_id_t task_id,
                                         void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);
  return ble_console_can_write();
}

static ssize_t on_console_read(void *context, void *buffer,
                               size_t buffer_size) {
  UNUSED(context);
  if (buffer_size > UINT16_MAX) {
    buffer_size = UINT16_MAX;
  }
  return (ssize_t)ble_console_read(buffer, (uint16_t)buffer_size);
}

static ssize_t on_console_write(void *context, const void *data,
                                size_t data_size) {
  UNUSED(context);
  if (data_size > BLE_CONSOLE_PACKET_SIZE) {
    data_size = BLE_CONSOLE_PACKET_SIZE;
  }
  return ble_console_write(data, (uint16_t)data_size) ? (ssize_t)data_size : 0;
}

static const syshandle_vmt_t ble_console_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_console_check_read_ready,
    .check_write_ready = on_console_check_write_ready,
    .poll = on_console_poll,
    .read = on_console_read,
    .write = on_console_write,
};

#endif  // KERNEL_MODE
