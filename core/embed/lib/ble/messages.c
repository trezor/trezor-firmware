
#include <stdint.h>
#include <string.h>

#include "ble.h"
#include "common.h"
#include "int_comm_defs.h"
#include "messages.h"
#include "state.h"

void process_poll(uint8_t *data, uint32_t len) {
  uint8_t cmd = data[0];

  switch (cmd) {
    //    case INTERNAL_EVENT_INITIALIZED: {
    //      set_connected(false);
    //      set_initialized(true);
    //      break;
    //    }
    case INTERNAL_EVENT_STATUS: {
      event_status_msg_t *msg = (event_status_msg_t *)data;
      set_status(msg);
      set_initialized(true);
      break;
    }
    default:
      break;
  }
}

bool wait_for_answer(void) {
  uint8_t buf[64] = {0};

  uint32_t ticks_start = hal_ticks_ms();
  int len = 0;

  while (len == 0) {
    if (hal_ticks_ms() - ticks_start > 1000) {
      // timeout
      return false;
    }

    len = ble_int_event_receive(buf, sizeof(buf));

    if (len > 0) {
      process_poll(buf, len);
    }
  }

  return true;
}

void send_state_request(void) {
  uint8_t cmd = INTERNAL_CMD_SEND_STATE;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
}

void send_advertising_on(bool whitelist) {
  uint8_t data[2];
  data[0] = INTERNAL_CMD_ADVERTISING_ON;
  data[1] = whitelist ? 1 : 0;
  ble_int_comm_send(data, sizeof(data), INTERNAL_EVENT);
}

void send_advertising_off(void) {
  uint8_t cmd = INTERNAL_CMD_ADVERTISING_OFF;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
}

bool send_erase_bonds(void) {
  if (!ble_firmware_running()) {
    return false;
  }
  uint8_t cmd = INTERNAL_CMD_ERASE_BONDS;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);

  uint8_t buf[64] = {0};

  uint32_t ticks_start = hal_ticks_ms();
  int len = 0;

  while (len == 0) {
    len = ble_int_event_receive(buf, sizeof(buf));

    if (hal_ticks_ms() - ticks_start > 1000) {
      // timeout
      return false;
    }
  }

  if (buf[0] == INTERNAL_EVENT_SUCCESS) {
    return true;
  }

  return false;
}

bool send_disconnect(void) {
  if (!ble_firmware_running()) {
    return false;
  }
  uint8_t cmd = INTERNAL_CMD_DISCONNECT;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);

  uint8_t buf[64] = {0};

  uint32_t ticks_start = hal_ticks_ms();
  int len = 0;

  while (len == 0) {
    len = ble_int_event_receive(buf, sizeof(buf));

    if (hal_ticks_ms() - ticks_start > 1000) {
      // timeout
      return false;
    }
  }

  if (buf[0] == INTERNAL_EVENT_SUCCESS) {
    return true;
  }

  return false;
}
