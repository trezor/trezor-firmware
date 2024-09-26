
#ifndef __BLE_COMM_H__
#define __BLE_COMM_H__

#include <stdbool.h>
#include <stdint.h>

void ble_hal_init(void);
void ble_hal_deinit(void);

void ble_hal_start(void);
void ble_hal_stop(void);
bool ble_hal_running(void);

void ble_hal_dfu_comm_send(const uint8_t *data, uint32_t len);
uint32_t ble_hal_dfu_comm_receive(uint8_t *data, uint32_t len);

void ble_hal_int_send(const uint8_t *data, uint32_t len);
uint32_t ble_hal_int_receive(uint8_t *data, uint32_t len);

void ble_hal_ext_send(const uint8_t *data, uint32_t len);
uint32_t ble_hal_ext_receive(uint8_t *data, uint32_t len);

bool ble_hal_firmware_running(void);

bool ble_hal_reboot(void);
bool ble_hal_reboot_to_bootloader(void);

void ble_hal_signal_running(void);
void ble_hal_signal_off(void);

#endif
