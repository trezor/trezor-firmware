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

#include "systimer.h"

#include "ble.h"
#include "ble_comm_defs.h"
#include "nrf/nrf.h"
#include "tsqueue/tsqueue.h"

typedef enum {
  BLE_MODE_OFF,
  BLE_MODE_CONNECTABLE,
  BLE_MODE_PAIRING,
  BLE_MODE_DFU,
} ble_mode_t;

#define EVENT_QUEUE_LEN 4
#define DATA_QUEUE_LEN 16
#define SEND_QUEUE_LEN 1
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
  ble_event_t event_buffers[EVENT_QUEUE_LEN];
  tsqueue_entry_t event_queue_entries[EVENT_QUEUE_LEN];
  tsqueue_t event_queue;

  uint8_t data_buffers[DATA_QUEUE_LEN][BLE_RX_PACKET_SIZE];
  tsqueue_entry_t data_queue_entries[DATA_QUEUE_LEN];
  tsqueue_t data_queue;

  uint8_t send_buffer[NRF_MAX_TX_DATA_SIZE];
  tsqueue_entry_t send_queue_entries[DATA_QUEUE_LEN];
  tsqueue_t send_queue;

  uint16_t ping_cntr;
} ble_driver_t;

static ble_driver_t g_ble_driver = {0};

static void ble_send_state_request(void) {
  uint8_t cmd = INTERNAL_CMD_PING;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);
}

static void ble_send_advertising_on(bool whitelist) {
  uint8_t data[2];
  data[0] = INTERNAL_CMD_ADVERTISING_ON;
  data[1] = whitelist ? 1 : 0;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, data, sizeof(data), NULL, NULL);
}

static void ble_send_advertising_off(void) {
  uint8_t cmd = INTERNAL_CMD_ADVERTISING_OFF;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);
}

static bool ble_send_erase_bonds(void) {
  if (!nrf_is_running()) {
    return false;
  }
  uint8_t cmd = INTERNAL_CMD_ERASE_BONDS;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);

  return true;
}

static bool ble_send_disconnect(void) {
  if (!nrf_is_running()) {
    return false;
  }
  uint8_t cmd = INTERNAL_CMD_DISCONNECT;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);

  return true;
}

static void ble_send_pairing_reject(void) {
  uint8_t cmd = INTERNAL_CMD_REJECT_PAIRING;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);
}

static void ble_send_pairing_accept(void) {
  uint8_t cmd = INTERNAL_CMD_ALLOW_PAIRING;
  nrf_send_msg(NRF_SERVICE_BLE_MANAGER, &cmd, sizeof(cmd), NULL, NULL);
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

  if (!drv->status_valid) {
    if (msg.peer_count > 0) {
      drv->mode_requested = BLE_MODE_CONNECTABLE;
    } else {
      drv->mode_requested = BLE_MODE_OFF;
    }
  }

  if (drv->connected != msg.connected) {
    if (msg.connected) {
      // new connection

      ble_event_t event = {.type = BLE_CONNECTED};
      tsqueue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event), NULL);

    } else {
      // connection lost
      ble_event_t event = {.type = BLE_DISCONNECTED};
      tsqueue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event), NULL);

      if (drv->mode_current == BLE_MODE_PAIRING) {
        drv->mode_requested = BLE_MODE_CONNECTABLE;
      }
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
    ble_send_pairing_reject();
    return;
  }

  ble_event_t event = {.type = BLE_PAIRING_REQUEST, .data_len = 6};
  memcpy(event.data, &data[1], 6);
  tsqueue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event), NULL);
}

static void ble_process_rx_msg_pairing_cancelled(const uint8_t *data,
                                                 uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  ble_event_t event = {.type = BLE_PAIRING_CANCELLED, .data_len = 0};
  tsqueue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event), NULL);
}

static void ble_process_rx_msg(const uint8_t *data, uint32_t len) {
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

  uint8_t *buffer = tsqueue_allocate(&drv->data_queue, NULL);

  if (buffer == NULL) {
    return;
  }

  memcpy(buffer, data, len);

  tsqueue_finalize(&drv->data_queue, buffer, len);
}

// background loop, called from systimer every 10ms
static void ble_loop(void *context) {
  (void)context;
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  if (nrf_is_running()) {
    if (!drv->status_valid) {
      ble_send_state_request();
    }

    if (drv->ping_cntr++ > (PING_PERIOD / LOOP_PERIOD_MS)) {
      ble_send_state_request();
      drv->ping_cntr = 0;
    }

    uint8_t data[NRF_MAX_TX_DATA_SIZE] = {0};
    if (tsqueue_read(&drv->send_queue, data, NRF_MAX_TX_DATA_SIZE, NULL)) {
      if (!nrf_send_msg(NRF_SERVICE_BLE, data, NRF_MAX_TX_DATA_SIZE, NULL,
                        NULL)) {
        tsqueue_insert(&drv->send_queue, data, NRF_MAX_TX_DATA_SIZE, NULL);
      }
    }

    if (drv->mode_current != drv->mode_requested) {
      if (drv->mode_requested == BLE_MODE_OFF) {
        ble_send_advertising_off();
        // if (drv->connected) {
        //   nrf_send_disconnect();
        // }
      } else if (drv->mode_requested == BLE_MODE_CONNECTABLE) {
        ble_send_advertising_on(true);
      } else if (drv->mode_requested == BLE_MODE_PAIRING) {
        ble_send_advertising_on(false);
      }
    }
  } else {
    drv->status_valid = false;
  }
}

void ble_init(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(ble_driver_t));

  tsqueue_init(&drv->event_queue, drv->event_queue_entries,
               (uint8_t *)drv->event_buffers, sizeof(ble_event_t),
               EVENT_QUEUE_LEN);

  tsqueue_init(&drv->data_queue, drv->data_queue_entries,
               (uint8_t *)drv->data_buffers, BLE_RX_PACKET_SIZE,
               DATA_QUEUE_LEN);

  tsqueue_init(&drv->send_queue, drv->send_queue_entries,
               (uint8_t *)drv->send_buffer, NRF_MAX_TX_DATA_SIZE,
               SEND_QUEUE_LEN);

  systimer_t *timer = systimer_create(ble_loop, NULL);

  systimer_set_periodic(timer, LOOP_PERIOD_MS);

  nrf_init();
  nrf_register_listener(NRF_SERVICE_BLE_MANAGER, ble_process_rx_msg);
  nrf_register_listener(NRF_SERVICE_BLE, ble_process_data);

  drv->initialized = true;
}

void ble_deinit(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  tsqueue_reset(&drv->event_queue);
  tsqueue_reset(&drv->data_queue);
  tsqueue_reset(&drv->send_queue);

  nrf_unregister_listener(NRF_SERVICE_BLE);
  nrf_unregister_listener(NRF_SERVICE_BLE_MANAGER);

  drv->initialized = false;
}

bool ble_connected(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->connected && nrf_is_running();
}

void ble_start(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  drv->accept_msgs = true;
}

void ble_stop(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  drv->accept_msgs = false;
  tsqueue_reset(&drv->data_queue);
}

bool ble_can_write(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!drv->connected || !drv->accept_msgs) {
    return false;
  }

  return !tsqueue_full(&drv->send_queue);
}

bool ble_write(const uint8_t *data, uint16_t len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!drv->connected || !drv->accept_msgs) {
    return false;
  }

  bool sent = nrf_send_msg(NRF_SERVICE_BLE, data, len, NULL, NULL);

  if (!sent) {
    bool queued = tsqueue_insert(&drv->send_queue, data, len, NULL);
    return queued;
  }

  return true;
}

uint32_t ble_read(uint8_t *data, uint16_t max_len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return 0;
  }

  tsqueue_t *queue = &drv->data_queue;

  uint16_t read_len = 0;

  bool received = tsqueue_read(queue, data, max_len, &read_len);

  if (!received) {
    return 0;
  }

  return max_len;
}

bool ble_issue_command(ble_command_t command) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  switch (command) {
    case BLE_SWITCH_OFF:
      drv->mode_requested = BLE_MODE_OFF;
      break;
    case BLE_SWITCH_ON:
      drv->mode_requested = BLE_MODE_CONNECTABLE;
      break;
    case BLE_PAIRING_MODE:
      drv->mode_requested = BLE_MODE_PAIRING;
      break;
    case BLE_DISCONNECT:
      ble_send_disconnect();
      break;
    case BLE_ERASE_BONDS:
      ble_send_erase_bonds();
      break;
    case BLE_ALLOW_PAIRING:
      ble_send_pairing_accept();
      break;
    case BLE_REJECT_PAIRING:
      ble_send_pairing_reject();
      break;
    default:
      // unknown command
      return false;
  }

  return true;
}

bool ble_read_event(ble_event_t *event) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  ble_event_t tmp_event = {0};
  uint16_t len = 0;
  bool read = tsqueue_read(&drv->event_queue, (uint8_t *)&tmp_event,
                           sizeof(tmp_event), &len);

  if (!read) {
    return false;
  }

  if (len != sizeof(ble_event_t)) {
    return false;
  }

  memcpy(event, &tmp_event, sizeof(ble_event_t));

  return true;
}

void ble_get_state(ble_state_t *state) {
  const ble_driver_t *drv = &g_ble_driver;

  if (state == NULL) {
    return;
  }

  if (!drv->initialized) {
    memset(state, 0, sizeof(ble_state_t));
    return;
  }

  state->connected = drv->connected;
  state->peer_count = drv->peer_count;
}

#endif
