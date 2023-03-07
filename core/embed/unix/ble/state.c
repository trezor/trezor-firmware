

#include "ble/state.h"

static bool ble_state_connected = false;
static bool ble_state_initialized = false;

bool ble_connected(void) { return ble_state_connected; }

void set_connected(bool connected) { ble_state_connected = connected; }

void set_initialized(bool initialized) { ble_state_initialized = initialized; }

bool ble_initialized(void) { return ble_state_initialized; }
