/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <trezor_types.h>

// maximum data size allowed to be sent
#define NRF_MAX_TX_DATA_SIZE (64)

typedef enum {
  NRF_SERVICE_BLE = 0,
  NRF_SERVICE_BLE_MANAGER = 1,
  NRF_SERVICE_MANAGEMENT = 2,
  NRF_SERVICE_PRODTEST = 3,

  NRF_SERVICE_CNT  // Number of services
} nrf_service_id_t;

typedef enum {
  NRF_STATUS_OK = 0,       // Packet completed successfully
  NRF_STATUS_TIMEOUT = 1,  // Timeout occurred
  NRF_STATUS_ERROR = 2,    // General error
  NRF_STATUS_ABORTED = 3,  // Packet was aborted
} nrf_status_t;

typedef struct {
  uint8_t version_major;
  uint8_t version_minor;
  uint8_t version_patch;
  uint8_t version_tweak;

  bool in_trz_ready;
  bool in_stay_in_bootloader;
  bool out_nrf_ready;
  bool out_reserved;
} nrf_info_t;

typedef void (*nrf_rx_callback_t)(const uint8_t *data, uint32_t len);
typedef void (*nrf_tx_callback_t)(nrf_status_t status, void *context);

// Initialize the NRF driver
void nrf_init(void);

// Deinitialize the NRF driver
void nrf_deinit(void);

// Check that NRF is running
bool nrf_is_running(void);

// Register listener for a service
// The listener will be called when a message is received for the service
// The listener will be called from an interrupt context
// Returns false if a listener for the service is already registered
bool nrf_register_listener(nrf_service_id_t service,
                           nrf_rx_callback_t callback);

// Unregister listener for a service
void nrf_unregister_listener(nrf_service_id_t service);

// Send a message to a service
// The message will be queued and sent as soon as possible
// If the queue is full, the message will be dropped
// returns ID of the message if it was successfully queued, otherwise -1
int32_t nrf_send_msg(nrf_service_id_t service, const uint8_t *data,
                     uint32_t len, nrf_tx_callback_t callback, void *context);

// Abort a message by ID
// If the message is already sent or the id is not found, it does nothing and
// returns false If the message is queued, it will be removed from the queue If
// the message is being sent, it will be sent. The callback will not be called.
bool nrf_abort_msg(int32_t id);

// Reads version and other info from NRF application.
// Blocking function.
bool nrf_get_info(nrf_info_t *info);

// TEST only functions

// Test SPI communication with NRF
bool nrf_test_spi_comm(void);

// Test UART communication with NRF
bool nrf_test_uart_comm(void);

// Test reboot to bootloader
bool nrf_test_reboot_to_bootloader(void);

bool nrf_test_gpio_trz_ready(void);

bool nrf_test_gpio_stay_in_bld(void);

bool nrf_test_gpio_reserved(void);
