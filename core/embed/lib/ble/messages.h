#ifndef __BLE_MESSAGES__
#define __BLE_MESSAGES__

#include <stdbool.h>

bool wait_for_answer(void);

void process_poll(uint8_t *data, uint32_t len);

void send_state_request(void);

void send_advertising_on(bool whitelist);

void send_advertising_off(void);

bool send_erase_bonds(void);

bool send_disconnect(void);

bool wait_for_answer(void);

bool ble_initialize(void);

#endif
