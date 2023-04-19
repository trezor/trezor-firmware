

#include "ble/state.h"
#include "messages.h"

static bool ble_state_connected = false;
static bool ble_state_initialized = false;
static bool ble_advertising_wanted = false;
static bool ble_advertising = false;

bool ble_connected(void) { return ble_state_connected; }

void set_connected(bool connected) { ble_state_connected = connected; }

void set_advertising(bool advertising) {
  if (ble_advertising_wanted != advertising) {
    if (ble_advertising_wanted) {
      send_advertising_on();
    } else {
      send_advertising_off();
    }
  }
  ble_advertising = advertising;
}

void set_initialized(bool initialized) { ble_state_initialized = initialized; }

bool ble_initialized(void) { return ble_state_initialized; }

void start_advertising(void) {
  ble_advertising_wanted = true;
  if (!ble_advertising) {
    send_advertising_on();
  }
}

void stop_advertising(void) {
  ble_advertising_wanted = false;
  if (ble_advertising) {
    send_advertising_off();
  }
}
