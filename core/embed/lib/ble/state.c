

#include "ble/state.h"
#include "ble.h"
#include "messages.h"

static bool ble_state_connected = false;
static bool ble_state_initialized = false;
static bool ble_advertising_wanted = false;
static bool ble_advertising_wl_wanted = false;
static bool ble_advertising = false;
static bool ble_advertising_wl = false;
static bool ble_dfu_mode = false;
static uint8_t ble_peer_count = 0;

bool ble_connected(void) {
  return ble_state_connected && ble_firmware_running();
}

void set_status(event_status_msg_t *msg) {
  if (ble_state_connected != msg->connected) {
    ble_advertising_wanted = msg->peer_count > 0;
    ble_advertising_wl_wanted = true;
  }
  ble_state_connected = msg->connected;

  ble_peer_count = msg->peer_count;
  if (msg->peer_count > 0 && !ble_initialized()) {
    ble_advertising_wanted = true;
    ble_advertising_wl_wanted = true;
  }

  if (ble_advertising_wanted != msg->advertising ||
      (ble_advertising_wl_wanted != msg->advertising_whitelist)) {
    if (ble_advertising_wanted && !ble_state_connected) {
      send_advertising_on(ble_advertising_wl_wanted);
    }
    if (!ble_advertising_wanted && ble_advertising) {
      send_advertising_off();
    }
  }
  ble_advertising = msg->advertising;
  ble_advertising_wl = msg->advertising_whitelist;
}

void set_initialized(bool initialized) { ble_state_initialized = initialized; }

bool ble_initialized(void) {
  return ble_state_initialized && ble_firmware_running();
}

void start_advertising(bool whitelist) {
  ble_advertising_wl_wanted = whitelist;
  ble_advertising_wanted = true;
  if (!ble_advertising || ble_advertising_wl != whitelist) {
    send_advertising_on(whitelist);
  } else {
    send_state_request();
  }
}

void stop_advertising(void) {
  ble_advertising_wanted = false;
  if (ble_advertising) {
    send_advertising_off();
  } else {
    send_state_request();
  }
}

void ble_set_dfu_mode(bool dfu) { ble_dfu_mode = dfu; }

bool is_ble_dfu_mode(void) { return ble_dfu_mode; }
