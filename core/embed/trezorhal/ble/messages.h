#ifndef __BLE_MESSAGES__
#define __BLE_MESSAGES__

void send_state_request(void);

void send_advertising_on(void);

void send_advertising_off(void);

bool send_erase_bonds(void);

bool send_disconnect(void);

#endif
