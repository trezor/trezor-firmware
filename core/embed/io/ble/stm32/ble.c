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

#include <trezor_rtl.h>

#include <io/ble.h>
#include <io/nrf.h>
#include <sys/irq.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <util/tsqueue.h>
#include <util/unit_properties.h>

#include "ble_comm_defs.h"

typedef enum {
  BLE_MODE_OFF,
  BLE_MODE_CONNECTABLE,
  BLE_MODE_PAIRING,
  BLE_MODE_DFU,
} ble_mode_t;

// changing value of TX_QUEUE_LEN is not allowed
// as it might result in order of messages being changed
#define TX_QUEUE_LEN 1
#define EVENT_QUEUE_LEN 4
#define RX_QUEUE_LEN 16
#define LOOP_PERIOD_MS 20
#define PING_PERIOD 100

typedef struct {
  ble_mode_t mode_requested;
  ble_mode_t mode_current;
  bool connected;
  uint8_t peer_count;
  bool initialized;
  bool status_valid;
  bool accept_msgs;
  bool pairing_requested;
  ble_event_t event_queue_buffers[EVENT_QUEUE_LEN];
  tsqueue_entry_t event_queue_entries[EVENT_QUEUE_LEN];
  tsqueue_t event_queue;

  uint8_t rx_queue_buffers[RX_QUEUE_LEN][BLE_RX_PACKET_SIZE];
  tsqueue_entry_t rx_queue_entries[RX_QUEUE_LEN];
  tsqueue_t rx_queue;

  uint8_t tx_queue_buffers[TX_QUEUE_LEN][NRF_MAX_TX_DATA_SIZE];
  tsqueue_entry_t ts_queue_entries[TX_QUEUE_LEN];
  tsqueue_t tx_queue;

  ble_adv_start_cmd_data_t adv_cmd;
  uint8_t mac[6];
  bool mac_ready;
  systimer_t *timer;
  uint16_t ping_cntr;
} ble_driver_t;

static ble_driver_t g_ble_driver = {0};

static const syshandle_vmt_t ble_handle_vmt;
static const syshandle_vmt_t ble_iface_handle_vmt;

static bool ble_send_state_request(ble_driver_t *drv) {
  (void)drv;
  uint8_t cmd = INTERNAL_CMD_SEND_STATE;
  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL) >=
         0;
}

static bool ble_send_advertising_on(ble_driver_t *drv, bool whitelist) {
  (void)drv;

  unit_properties_t props;
  unit_properties_get(&props);

  cmd_advertising_on_t data = {
      .cmd_id = INTERNAL_CMD_ADVERTISING_ON,
      .whitelist = whitelist ? 1 : 0,
      .color = props.color,
      .static_addr = drv->adv_cmd.static_mac,
      .device_code = HW_MODEL,
  };

  memcpy(data.name, drv->adv_cmd.name, BLE_ADV_NAME_LEN);

  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, (uint8_t *)&data, sizeof(data),
                      NULL, NULL) >= 0;
}

static bool ble_send_advertising_off(ble_driver_t *drv) {
  (void)drv;
  uint8_t cmd = INTERNAL_CMD_ADVERTISING_OFF;
  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL) >=
         0;
}

static bool ble_send_erase_bonds(ble_driver_t *drv) {
  (void)drv;
  uint8_t cmd = INTERNAL_CMD_ERASE_BONDS;
  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL) >=
         0;
}

static bool ble_send_unpair(ble_driver_t *drv) {
  (void)drv;
  uint8_t cmd = INTERNAL_CMD_UNPAIR;
  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL) >=
         0;
}

static bool ble_send_disconnect(ble_driver_t *drv) {
  (void)drv;
  uint8_t cmd = INTERNAL_CMD_DISCONNECT;
  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL) >=
         0;
}

static bool ble_send_pairing_reject(ble_driver_t *drv) {
  uint8_t cmd = INTERNAL_CMD_REJECT_PAIRING;
  bool result =
      nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);

  if (result) {
    drv->pairing_requested = false;
  }

  return result;
}

static bool ble_send_pairing_accept(ble_driver_t *drv, uint8_t *code) {
  cmd_allow_pairing_t data = {
      .cmd_id = INTERNAL_CMD_ALLOW_PAIRING,
  };

  memcpy(data.code, code, sizeof(data.code));

  bool result = nrf_send_msg(NRF_SERVICE_BLE_MANAGER, (uint8_t *)&data,
                             sizeof(data), NULL, NULL);

  if (result) {
    drv->pairing_requested = false;
  }

  return result;
}

static bool ble_send_mac_request(ble_driver_t *drv) {
  UNUSED(drv);
  uint8_t cmd = INTERNAL_CMD_GET_MAC;

  return nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);
}

static void ble_process_rx_msg_status(const uint8_t *data, uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }
  if (len < sizeof(event_status_msg_t)) {
    // insufficient data length
    return;
  }

  event_status_msg_t msg;
  memcpy(&msg, data, sizeof(event_status_msg_t));

  if (drv->connected != msg.connected) {
    if (msg.connected) {
      // new connection

      ble_event_t event = {.type = BLE_CONNECTED};
      tsqueue_enqueue(&drv->event_queue, (uint8_t *)&event, sizeof(event),
                      NULL);

    } else {
      // connection lost
      ble_event_t event = {.type = BLE_DISCONNECTED};
      tsqueue_enqueue(&drv->event_queue, (uint8_t *)&event, sizeof(event),
                      NULL);

      if (drv->mode_current == BLE_MODE_PAIRING) {
        drv->mode_requested = BLE_MODE_CONNECTABLE;
      }

      drv->pairing_requested = false;
    }

    drv->connected = msg.connected;
  }

  if (msg.advertising && !msg.advertising_whitelist) {
    drv->mode_current = BLE_MODE_PAIRING;
  } else if (msg.advertising) {
    drv->mode_current = BLE_MODE_CONNECTABLE;
  } else {
    drv->mode_current = BLE_MODE_OFF;
  }

  drv->peer_count = msg.peer_count;

  drv->status_valid = true;
}

static void ble_process_rx_msg_pairing_request(const uint8_t *data,
                                               uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  if (len < 7) {
    // insufficient data length
    return;
  }

  if (drv->mode_requested != BLE_MODE_PAIRING ||
      drv->mode_current != BLE_MODE_PAIRING) {
    ble_send_pairing_reject(drv);
    return;
  }

  ble_event_t event = {.type = BLE_PAIRING_REQUEST,
                       .data_len = BLE_PAIRING_CODE_LEN};
  memcpy(event.data, &data[1], BLE_PAIRING_CODE_LEN);
  if (!tsqueue_enqueue(&drv->event_queue, (uint8_t *)&event, sizeof(event),
                       NULL)) {
    ble_send_pairing_reject(drv);
  } else {
    drv->pairing_requested = true;
  }
}

static void ble_process_rx_msg_pairing_cancelled(const uint8_t *data,
                                                 uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  ble_event_t event = {.type = BLE_PAIRING_CANCELLED, .data_len = 0};
  tsqueue_enqueue(&drv->event_queue, (uint8_t *)&event, sizeof(event), NULL);
  drv->pairing_requested = false;
}

static void ble_process_rx_msg_mac(const uint8_t *data, uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  drv->mac_ready = true;
  memcpy(drv->mac, &data[1], sizeof(drv->mac));
}

static void ble_process_rx_msg(const uint8_t *data, uint32_t len) {
  if (len < 1) {
    return;
  }

  switch (data[0]) {
    case INTERNAL_EVENT_STATUS:
      ble_process_rx_msg_status(data, len);
      break;
    case INTERNAL_EVENT_PAIRING_REQUEST:
      ble_process_rx_msg_pairing_request(data, len);
      break;
    case INTERNAL_EVENT_PAIRING_CANCELLED:
      ble_process_rx_msg_pairing_cancelled(data, len);
      break;
    case INTERNAL_EVENT_MAC:
      ble_process_rx_msg_mac(data, len);
    default:
      break;
  }
}

static void ble_process_data(const uint8_t *data, uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  if (len != BLE_RX_PACKET_SIZE) {
    return;
  }

  tsqueue_enqueue(&drv->rx_queue, data, len, NULL);
}

// background loop, called from systimer every 10ms
static void ble_loop(void *context) {
  ble_driver_t *drv = (ble_driver_t *)context;

  if (!drv->initialized) {
    return;
  }

  if (nrf_is_running()) {
    if (drv->ping_cntr == 0) {
      ble_send_state_request(drv);
    }

    drv->ping_cntr++;
    if (drv->ping_cntr >= PING_PERIOD / LOOP_PERIOD_MS) {
      drv->ping_cntr = 0;
    }

    uint8_t data[NRF_MAX_TX_DATA_SIZE] = {0};
    if (tsqueue_dequeue(&drv->tx_queue, data, NRF_MAX_TX_DATA_SIZE, NULL,
                        NULL)) {
      if (!nrf_send_msg(NRF_SERVICE_BLE, data, NRF_MAX_TX_DATA_SIZE, NULL,
                        NULL)) {
        tsqueue_enqueue(&drv->tx_queue, data, NRF_MAX_TX_DATA_SIZE, NULL);
      }
    }

    if (drv->mode_current != drv->mode_requested) {
      if (drv->mode_requested == BLE_MODE_OFF) {
        ble_send_advertising_off(drv);
        // if (drv->connected) {
        //   nrf_send_disconnect();
        // }
      } else if (drv->mode_requested == BLE_MODE_CONNECTABLE) {
        ble_send_advertising_on(drv, true);
      } else if (drv->mode_requested == BLE_MODE_PAIRING) {
        ble_send_advertising_on(drv, false);
      }
    }
  } else {
    drv->status_valid = false;
  }
}

bool ble_init(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(ble_driver_t));

  tsqueue_init(&drv->event_queue, drv->event_queue_entries,
               (uint8_t *)drv->event_queue_buffers, sizeof(ble_event_t),
               EVENT_QUEUE_LEN);

  tsqueue_init(&drv->rx_queue, drv->rx_queue_entries,
               (uint8_t *)drv->rx_queue_buffers, BLE_RX_PACKET_SIZE,
               RX_QUEUE_LEN);

  tsqueue_init(&drv->tx_queue, drv->ts_queue_entries,
               (uint8_t *)drv->tx_queue_buffers, NRF_MAX_TX_DATA_SIZE,
               TX_QUEUE_LEN);

  drv->timer = systimer_create(ble_loop, drv);

  if (drv->timer == NULL) {
    goto cleanup;
  }

  systimer_set_periodic(drv->timer, LOOP_PERIOD_MS);

  nrf_init();
  if (!nrf_register_listener(NRF_SERVICE_BLE_MANAGER, ble_process_rx_msg)) {
    goto cleanup;
  }
  if (!nrf_register_listener(NRF_SERVICE_BLE, ble_process_data)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_BLE, &ble_handle_vmt, drv)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_BLE_IFACE_0, &ble_iface_handle_vmt, drv)) {
    goto cleanup;
  }

  drv->initialized = true;
  return true;

cleanup:
  if (drv->timer != NULL) {
    systimer_delete(drv->timer);
  }
  nrf_deinit();
  memset(drv, 0, sizeof(ble_driver_t));
  return false;
}

void ble_deinit(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  syshandle_unregister(SYSHANDLE_BLE_IFACE_0);
  syshandle_unregister(SYSHANDLE_BLE);

  nrf_unregister_listener(NRF_SERVICE_BLE);
  nrf_unregister_listener(NRF_SERVICE_BLE_MANAGER);

  systimer_delete(drv->timer);

  tsqueue_reset(&drv->event_queue);
  tsqueue_reset(&drv->rx_queue);
  tsqueue_reset(&drv->tx_queue);

  nrf_deinit();

  drv->initialized = false;
}

bool ble_connected(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  bool connected = drv->connected && nrf_is_running();

  irq_unlock(key);

  return connected;
}

void ble_start(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  irq_key_t key = irq_lock();

  drv->accept_msgs = true;

  irq_unlock(key);
}

void ble_stop(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  irq_key_t key = irq_lock();

  drv->accept_msgs = false;
  tsqueue_reset(&drv->rx_queue);

  irq_unlock(key);
}

bool ble_can_write(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  if (!drv->connected || !drv->accept_msgs) {
    irq_unlock(key);
    return false;
  }

  bool full = !tsqueue_full(&drv->tx_queue);

  irq_unlock(key);

  return full;
}

bool ble_write(const uint8_t *data, uint16_t len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  if (!drv->connected || !drv->accept_msgs) {
    irq_unlock(key);
    return false;
  }

  bool sent = nrf_send_msg(NRF_SERVICE_BLE, data, len, NULL, NULL);

  if (!sent) {
    bool queued = tsqueue_enqueue(&drv->tx_queue, data, len, NULL);
    irq_unlock(key);
    return queued;
  }

  irq_unlock(key);
  return true;
}

bool ble_can_read(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  bool result = !tsqueue_empty(&drv->rx_queue);

  irq_unlock(key);

  return result;
}

uint32_t ble_read(uint8_t *data, uint16_t max_len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return 0;
  }

  irq_key_t key = irq_lock();

  tsqueue_t *queue = &drv->rx_queue;

  uint16_t read_len = 0;

  tsqueue_dequeue(queue, data, max_len, &read_len, NULL);

  irq_unlock(key);

  return read_len;
}

bool ble_issue_command(ble_command_t *command) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  bool result = false;

  switch (command->cmd_type) {
    case BLE_SWITCH_OFF:
      drv->mode_requested = BLE_MODE_OFF;
      result = true;
      break;
    case BLE_SWITCH_ON:
      memcpy(&drv->adv_cmd, &command->data.adv_start, sizeof(drv->adv_cmd));
      drv->mode_requested = BLE_MODE_CONNECTABLE;
      result = true;
      break;
    case BLE_PAIRING_MODE:
      memcpy(&drv->adv_cmd, &command->data.adv_start, sizeof(drv->adv_cmd));
      drv->mode_requested = BLE_MODE_PAIRING;
      result = true;
      break;
    case BLE_DISCONNECT:
      result = ble_send_disconnect(drv);
      break;
    case BLE_ERASE_BONDS:
      result = ble_send_erase_bonds(drv);
      break;
    case BLE_ALLOW_PAIRING:
      result = ble_send_pairing_accept(drv, command->data.pairing_code);
      break;
    case BLE_REJECT_PAIRING:
      result = ble_send_pairing_reject(drv);
      break;
    case BLE_UNPAIR:
      result = ble_send_unpair(drv);
      break;
    default:
      break;
  }

  irq_unlock(key);

  return result;
}

bool ble_get_event(ble_event_t *event) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t key = irq_lock();

  bool result = tsqueue_dequeue(&drv->event_queue, (uint8_t *)event,
                                sizeof(*event), NULL, NULL);

  irq_unlock(key);

  return result;
}

void ble_get_state(ble_state_t *state) {
  const ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    memset(state, 0, sizeof(ble_state_t));
    return;
  }

  irq_key_t key = irq_lock();

  state->connected = drv->connected;
  state->peer_count = drv->peer_count;
  state->pairing = drv->mode_current == BLE_MODE_PAIRING;
  state->connectable = drv->mode_current == BLE_MODE_CONNECTABLE;
  state->pairing_requested = drv->pairing_requested;
  state->state_known = drv->status_valid;

  irq_unlock(key);
}

bool ble_get_mac(uint8_t *mac, size_t max_len) {
  ble_driver_t *drv = &g_ble_driver;

  if (max_len < sizeof(drv->mac)) {
    return false;
  }

  if (!drv->initialized) {
    memset(mac, 0, max_len);
    return false;
  }

  drv->mac_ready = false;

  if (!ble_send_mac_request(drv)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (drv->mac_ready) {
      memcpy(mac, drv->mac, sizeof(drv->mac));
      return true;
    }
  }

  memset(mac, 0, max_len);
  return false;
}

static void on_ble_iface_event_poll(void *context, bool read_awaited,
                                    bool write_awaited) {
  UNUSED(context);

  syshandle_t handle = SYSHANDLE_BLE_IFACE_0;

  // Only one task can read or write at a time. Therefore, we can
  // assume that only one task is waiting for events and keep the
  // logic simple.

  if (read_awaited && ble_can_read()) {
    syshandle_signal_read_ready(handle, NULL);
  }

  if (write_awaited && ble_can_write()) {
    syshandle_signal_write_ready(handle, NULL);
  }
}

static bool on_ble_iface_read_ready(void *context, systask_id_t task_id,
                                    void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);

  return ble_can_read();
}

static bool on_ble_iface_check_write_ready(void *context, systask_id_t task_id,
                                           void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);

  return ble_can_write();
}

static const syshandle_vmt_t ble_iface_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_ble_iface_read_ready,
    .check_write_ready = on_ble_iface_check_write_ready,
    .poll = on_ble_iface_event_poll,
};

static void on_ble_poll(void *context, bool read_awaited, bool write_awaited) {
  ble_driver_t *drv = (ble_driver_t *)context;

  UNUSED(write_awaited);

  // Until we need to poll BLE events from multiple tasks,
  // the logic here can remain very simple. If this assumption
  // changes, the logic will need to be updated (e.g., task-local storage
  // with an independent queue for each task).

  if (read_awaited) {
    irq_key_t key = irq_lock();
    bool queue_is_empty = tsqueue_empty(&drv->event_queue);
    irq_unlock(key);

    syshandle_signal_read_ready(SYSHANDLE_BLE, &queue_is_empty);
  }
}

static bool on_ble_check_read_ready(void *context, systask_id_t task_id,
                                    void *param) {
  UNUSED(context);
  UNUSED(task_id);

  bool queue_is_empty = *(bool *)param;

  return !queue_is_empty;
}

static const syshandle_vmt_t ble_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_ble_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_ble_poll,
};

#endif
