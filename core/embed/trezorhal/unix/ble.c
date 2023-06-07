#include "ble.h"
#include <stdint.h>

static bool firmware_running = true;

void ble_comm_init(void) {}

void ble_comm_send(uint8_t *data, uint32_t len) {}

uint32_t ble_comm_receive(uint8_t *data, uint32_t len) { return 0; }

void ble_int_comm_send(uint8_t *data, uint32_t len, uint8_t message_type) {}
uint32_t ble_int_event_receive(uint8_t *data, uint32_t len) { return 0; }
uint32_t ble_int_comm_receive(uint8_t *data, uint32_t len) { return 0; }
uint32_t ble_ext_comm_receive(uint8_t *data, uint32_t len) { return 0; }

void ble_event_poll(void) {}

bool ble_firmware_running(void) { return firmware_running; }

bool ble_reset_to_bootloader(void) {
  firmware_running = false;
  return true;
}

bool ble_reset(void) {
  firmware_running = true;
  return true;
}
