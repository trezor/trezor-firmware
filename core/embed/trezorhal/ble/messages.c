
#include <stdint.h>

#include "comm.h"
#include "messages.h"

void send_state_request(void) {
  uint8_t cmd = INTERNAL_CMD_SEND_STATE;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
}

void send_advertising_on(void) {
  uint8_t cmd = INTERNAL_CMD_ADVERTISING_ON;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
}

void send_advertising_off(void) {
  uint8_t cmd = INTERNAL_CMD_ADVERTISING_OFF;
  ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
}
