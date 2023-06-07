
#ifndef __BLE_STATE__
#define __BLE_STATE__

#include <stdbool.h>
#include <stdint.h>

bool ble_initialized(void);

void set_initialized(bool initialized);

bool ble_connected(void);

void set_advertising(bool advertising);

void set_connected(bool connected);

void start_advertising(void);

void stop_advertising(void);

#endif
