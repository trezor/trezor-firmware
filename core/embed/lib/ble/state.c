

#include "ble/state.h"
#include "ble_hal.h"
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

void set_connected(bool connected) {}

static void configure_ble(bool advertising, bool whitelist) {
  if (ble_advertising != advertising || (ble_advertising_wl != whitelist)) {
    if (advertising) {
      send_advertising_on(whitelist);
    }
    if (!advertising && ble_advertising) {
      send_advertising_off();
    }
  }

  ble_advertising_wanted = advertising;
  ble_advertising_wl_wanted = whitelist;
}

void set_status(event_status_msg_t *msg) {
  ble_state_connected = msg->connected;
  ble_peer_count = msg->peer_count;
  ble_advertising = msg->advertising;
  ble_advertising_wl = msg->advertising_whitelist;

  set_initialized(true);

  configure_ble(ble_advertising_wanted, ble_advertising_wl_wanted);
}

void set_initialized(bool initialized) { ble_state_initialized = initialized; }

bool ble_initialized(void) {
  return ble_state_initialized && ble_firmware_running();
}

void start_advertising(bool whitelist) { configure_ble(true, whitelist); }

void auto_start_advertising(void) {
  if (ble_peer_count > 0) {
    configure_ble(true, true);
  } else {
    configure_ble(false, false);
  }
}

void stop_advertising(void) { configure_ble(false, false); }

void ble_set_dfu_mode(bool dfu) { ble_dfu_mode = dfu; }

bool is_ble_dfu_mode(void) { return ble_dfu_mode; }

void ble_stop_all_comm(void) {
  stop_advertising();
  ble_comm_stop();
}
