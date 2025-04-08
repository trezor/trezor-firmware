#include <io/ble.h>
#include <trezor_rtl.h>

#include <stdlib.h>

bool ble_init(void) { return true; }

void ble_deinit(void) {}

void ble_start(void) {}

void ble_stop(void) {}

bool ble_issue_command(ble_command_t *command) { return true; }

bool ble_get_event(ble_event_t *event) { return false; }

void ble_get_state(ble_state_t *state) {
  memset(state, 0, sizeof(ble_state_t));
}

bool ble_can_write(void) { return true; }

bool ble_write(const uint8_t *data, uint16_t len) { return len; }

bool ble_can_read(void) { return false; }

uint32_t ble_read(uint8_t *data, uint16_t max_len) { return 0; }

bool ble_get_mac(uint8_t *mac, size_t max_len) { return false; }
