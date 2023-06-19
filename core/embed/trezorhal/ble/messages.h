#ifndef __BLE_MESSAGES__
#define __BLE_MESSAGES__

#include <stdbool.h>

void send_state_request(void);

void send_advertising_on(bool whitelist);

void send_advertising_off(void);

bool send_erase_bonds(void);

bool send_disconnect(void);

#endif
