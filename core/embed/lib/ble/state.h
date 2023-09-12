
#ifndef __BLE_STATE__
#define __BLE_STATE__

#include <stdbool.h>
#include <stdint.h>

#include "int_comm_defs.h"

bool ble_initialized(void);

void set_initialized(bool initialized);

bool ble_connected(void);

void set_status(event_status_msg_t *msg);

void start_advertising(bool whitelist);

void stop_advertising(void);

void ble_set_dfu_mode(bool dfu);

bool is_ble_dfu_mode(void);

#endif
