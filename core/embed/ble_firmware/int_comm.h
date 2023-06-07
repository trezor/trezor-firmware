#ifndef __INT_COMM__
#define __INT_COMM__

#include "app_uart.h"
#include "ble_nus.h"
#include "stdint.h"

void spi_init(void);

void nus_init(void);

void nus_data_handler(ble_nus_evt_t *p_evt);

void uart_event_handle(app_uart_evt_t *p_event);

void send_status_event(void);
void send_success_event(void);

bool send_comparison_request(uint8_t *p_key, int8_t p_key_len);

bool send_auth_key_request(uint8_t *p_key, uint8_t p_key_len);

bool send_repair_request(void);

void send_initialized(void);

#endif
