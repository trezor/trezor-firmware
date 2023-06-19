

#include "ble/state.h"
#include "ble/comm.h"
#include "messages.h"

static bool ble_state_connected = false;
static bool ble_state_initialized = false;
static bool ble_advertising_wanted = false;
static bool ble_advertising_wh_wanted = false;
static bool ble_advertising = false;

bool ble_connected(void) {
  return ble_state_connected && ble_firmware_running();
}

void set_connected(bool connected) { ble_state_connected = connected; }

void set_advertising(bool advertising) {
  if (ble_advertising_wanted != advertising) {
    if (ble_advertising_wanted) {
      send_advertising_on(ble_advertising_wh_wanted);
    } else {
      send_advertising_off();
    }
  }
  ble_advertising = advertising;
}

void set_initialized(bool initialized) { ble_state_initialized = initialized; }

bool ble_initialized(void) {
  return ble_state_initialized && ble_firmware_running();
}

void start_advertising(bool whitelist) {
  ble_advertising_wh_wanted = whitelist;
  ble_advertising_wanted = true;
  //if (!ble_advertising) {
    send_advertising_on(whitelist);
  //}
}

void stop_advertising(void) {
  ble_advertising_wanted = false;
  if (ble_advertising) {
    send_advertising_off();
  }
}
