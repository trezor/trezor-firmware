
#ifndef __BLE_COMM_H__
#define __BLE_COMM_H__

#include <stdbool.h>
#include <stdint.h>
#include "ble/int_comm_defs.h"

void ble_comm_init(void);

void ble_start(void);
void ble_stop(void);

void ble_comm_send(uint8_t *data, uint32_t len);
uint32_t ble_comm_receive(uint8_t *data, uint32_t len);

void ble_int_comm_send(uint8_t *data, uint32_t len, uint8_t message_type);
uint32_t ble_int_event_receive(uint8_t *data, uint32_t len);
uint32_t ble_int_comm_receive(uint8_t *data, uint32_t len);
uint32_t ble_ext_comm_receive(uint8_t *data, uint32_t len);

void ble_event_poll(void);

bool ble_firmware_running(void);

bool ble_reset_to_bootloader(void);

bool ble_reset(void);

#endif
