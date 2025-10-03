#include <io/ble.h>
#include <trezor_rtl.h>

bool ble_init(void) { return true; }

void ble_deinit(void) {}

void ble_start(void) {}

void ble_stop(void) {}

bool ble_switch_off(void) { return true; }

bool ble_switch_on(void) { return true; }

bool ble_enter_pairing_mode(const uint8_t *name, size_t name_len) {
  return true;
}

bool ble_disconnect(void) { return true; }

bool ble_erase_bonds(void) { return true; }

bool ble_allow_pairing(const uint8_t *pairing_code) { return true; }

bool ble_reject_pairing(void) { return true; }

bool ble_keep_connection(void) { return true; }

void ble_set_name(const uint8_t *name, size_t len) {}

bool ble_get_event(ble_event_t *event) { return false; }

void ble_get_state(ble_state_t *state) {
  memset(state, 0, sizeof(ble_state_t));
}

bool ble_can_write(void) { return true; }

bool ble_write(const uint8_t *data, uint16_t len) { return len; }

bool ble_can_read(void) { return false; }

uint32_t ble_read(uint8_t *data, uint16_t max_len) { return 0; }

bool ble_get_mac(bt_le_addr_t *addr) { return false; }

void ble_event_flush(void) {}

void ble_get_advertising_name(char *name, size_t max_len) {
  memset(name, 0, max_len);
}

bool ble_unpair(const bt_le_addr_t *addr) { return false; }

uint8_t ble_get_bond_list(bt_le_addr_t *bonds, size_t count) { return 0; }

void ble_set_high_speed(bool enable){};

void ble_notify(const uint8_t *data, size_t len){};

void ble_set_enabled(bool enabled) {}

bool ble_get_enabled(void) { return false; }

bool ble_wait_until_ready(void) { return true; }
