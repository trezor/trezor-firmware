
#ifdef KERNEL_MODE

#include <string.h>

#include "systimer.h"

#include "ble.h"
#include "ble_hal.h"
#include "int_comm_defs.h"
#include "messages.h"
#include "static_queue.h"

CREATE_QUEUE_TYPE(event, sizeof(ble_event_t), 4)

typedef enum {
  BLE_MODE_OFF,
  BLE_MODE_CONNECTABLE,
  BLE_MODE_PAIRING,
  BLE_MODE_DFU,
} ble_mode_t;

typedef struct {
  ble_mode_t mode_requested;
  ble_mode_t mode_current;
  bool connected;
  uint8_t peer_count;
  bool initialized;
  bool status_valid;
  event_queue_t event_queue;
} ble_driver_t;

static ble_driver_t g_ble_driver = {0};

static void ble_process_rx_msg_status(const uint8_t *data, uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  const event_status_msg_t *msg = (event_status_msg_t *)data;

  if (drv->connected != msg->connected) {
    if (msg->connected) {
      // new connection

      ble_event_t event = {.type = BLE_CONNECTED};
      event_queue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event));

    } else {
      // connection lost
      ble_event_t event = {.type = BLE_DISCONNECTED};
      event_queue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event));

      if (drv->mode_current == BLE_MODE_PAIRING) {
        drv->mode_requested = BLE_MODE_CONNECTABLE;
      }
    }

    drv->connected = msg->connected;
  }

  if (msg->advertising && !msg->advertising_whitelist) {
    drv->mode_current = BLE_MODE_PAIRING;
  } else if (msg->advertising) {
    drv->mode_current = BLE_MODE_CONNECTABLE;
  } else {
    drv->mode_current = BLE_MODE_OFF;
  }

  drv->peer_count = msg->peer_count;

  drv->status_valid = true;
}

static void ble_process_rx_msg_pairing_request(const uint8_t *data,
                                               uint32_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  if (drv->mode_requested != BLE_MODE_PAIRING ||
      drv->mode_current != BLE_MODE_PAIRING) {
    send_pairing_reject();
  }

  ble_event_t event = {.type = BLE_PAIRING_REQUEST, .data_len = 6};
  memcpy(event.data, &data[1], 6);
  event_queue_insert(&drv->event_queue, (uint8_t *)&event, sizeof(event));
}

static void ble_process_rx_msg(const uint8_t *data, uint32_t len) {
  switch (data[0]) {
    case INTERNAL_EVENT_STATUS:
      ble_process_rx_msg_status(data, len);
      break;
    case INTERNAL_EVENT_PAIRING_REQUEST:
      ble_process_rx_msg_pairing_request(data, len);
      break;
    default:
      break;
  }
}

// background loop, called from systimer every 10ms
static void ble_loop(void *context) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  if (ble_hal_firmware_running()) {
    // receive internal messages
    uint8_t buf[64] = {0};
    uint32_t len = ble_hal_int_receive(buf, 64);

    if (len > 0) {
      ble_process_rx_msg(buf, len);
    }

    if (!drv->status_valid) {
      send_state_request();
    }

    if (drv->mode_current != drv->mode_requested) {
      if (drv->mode_requested == BLE_MODE_OFF) {
        send_advertising_off();
        if (drv->connected) {
          send_disconnect();
        }
      } else if (drv->mode_requested == BLE_MODE_CONNECTABLE) {
        send_advertising_on(true);
      } else if (drv->mode_requested == BLE_MODE_PAIRING) {
        send_advertising_on(false);
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

  event_queue_init(&drv->event_queue);

  systimer_t *timer = systimer_create(ble_loop, NULL);

  systimer_set_periodic(timer, 10);

  ble_hal_init();
  drv->initialized = true;
}

void ble_deinit(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  ble_hal_deinit();

  drv->initialized = false;
}

bool ble_connected(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->connected && ble_hal_firmware_running();
}

void ble_set_dfu_mode(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  if (ble_hal_reboot_to_bootloader()) {
    drv->mode_current = BLE_MODE_DFU;
  } else {
    drv->status_valid = false;
  }
}

bool is_ble_dfu_mode(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->mode_current == BLE_MODE_DFU;
}

void ble_start(void) { ble_hal_start(); }

void ble_stop(void) {
  ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    return;
  }

  send_advertising_off();
  drv->mode_requested = BLE_MODE_OFF;
  ble_hal_stop();
}

void ble_disconnect(void) { send_disconnect(); }

void ble_erase_bonds(void) { send_erase_bonds(); }

void ble_write(const uint8_t *data, uint16_t len) {
  ble_hal_ext_send(data, len);
}

uint32_t ble_read(uint8_t *data, uint16_t len) {
  return ble_hal_ext_receive(data, len);
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
      send_disconnect();
      break;
    case BLE_ERASE_BONDS:
      send_erase_bonds();
      break;
    case BLE_ENTER_DFU_MODE:
      ble_set_dfu_mode();
      break;
    case BLE_ALLOW_PAIRING:
      send_pairing_accept();
      break;
    case BLE_REJECT_PAIRING:
      send_pairing_reject();
      break;
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
  bool read = event_queue_read(&drv->event_queue, (uint8_t *)&tmp_event,
                               sizeof(tmp_event), &len);

  if (!read) {
    return false;
  }

  memcpy(event, &tmp_event, sizeof(ble_event_t));

  return true;
}

void ble_get_state(ble_state_t *state) {
  const ble_driver_t *drv = &g_ble_driver;

  if (!drv->initialized) {
    memset(state, 0, sizeof(ble_state_t));
    return;
  }

  state->connected = drv->connected;
  state->peer_count = drv->peer_count;
}

#endif
