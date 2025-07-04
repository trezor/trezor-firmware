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

#include <sha2.h>

// maximum data size allowed to be sent
#define NRF_MAX_TX_DATA_SIZE (251)

typedef enum {
  NRF_SERVICE_BLE = 0,
  NRF_SERVICE_BLE_MANAGER = 1,
  NRF_SERVICE_MANAGEMENT = 2,
  NRF_SERVICE_PRODTEST = 3,
  NRF_SERVICE_IDLE = 4,

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

  bool reserved;
  bool in_stay_in_bootloader;
  bool reserved2;
  bool out_wakeup;

  uint8_t hash[SHA256_DIGEST_LENGTH];
} nrf_info_t;

/** Callback type invoked when data is received on a registered service */
typedef void (*nrf_rx_callback_t)(const uint8_t *data, uint32_t len);

/** Callback type invoked when a message transmission completes */
typedef void (*nrf_tx_callback_t)(nrf_status_t status, void *context);

/**
 * @brief Initialize the NRF driver.
 */
void nrf_init(void);

/**
 * @brief Deinitialize the NRF driver.
 */
void nrf_deinit(void);

/**
 * @brief Suspend the NRF driver.
 */
void nrf_suspend(void);

/**
 * @brief Resume the NRF driver.
 */
void nrf_resume(void);

/**
 * @brief Check if the NRF communication is currently running.
 *
 * @return true if running, false otherwise
 */
bool nrf_is_running(void);

/**
 * @brief Register a listener for a specific NRF service.
 *
 * The listener callback will be invoked from an interrupt context when a
 * message is received for the specified service.
 *
 * @param service  Service identifier to register for
 * @param callback Function to call when data arrives
 * @return false if a listener for the service is already registered, true
 * otherwise
 */
bool nrf_register_listener(nrf_service_id_t service,
                           nrf_rx_callback_t callback);

/**
 * @brief Unregister the listener for a specific NRF service.
 *
 * @param service  Service identifier to unregister
 */
void nrf_unregister_listener(nrf_service_id_t service);

/**
 * @brief Send a message to a specific NRF service.
 *
 * The message will be queued and sent as soon as possible. If the queue is
 * full, the message will be dropped.
 *
 * @param service   Service identifier to send to
 * @param data      Pointer to the data buffer to send
 * @param len       Length of the data buffer
 * @param callback  Function to call upon transmission completion
 * @param context   Context pointer passed to the callback
 * @return ID of the message if successfully queued; -1 otherwise
 */
int32_t nrf_send_msg(nrf_service_id_t service, const uint8_t *data,
                     uint32_t len, nrf_tx_callback_t callback, void *context);

/**
 * @brief Abort a queued message by its ID.
 *
 * If the message is already sent or the ID is not found, this function does
 * nothing and returns false. If the message is queued, it will be removed from
 * the queue. If the message is in the process of being sent, it will complete,
 * but its callback will not be invoked.
 *
 * @param id  Identifier of the message to abort
 * @return false if the message was already sent or not found, true if aborted
 */
bool nrf_abort_msg(int32_t id);

/**
 * @brief Read version and other information from the NRF application.
 *
 * Blocking function that fills the provided nrf_info_t structure.
 *
 * @param info  Pointer to an nrf_info_t structure to populate
 * @return true on success; false on communication error
 */
bool nrf_get_info(nrf_info_t *info);

/**
 * @brief Place the NRF device into system-off (deep sleep) mode.
 *
 * @return true if the command was acknowledged; false otherwise
 */
bool nrf_system_off(void);

/**
 * @brief Reboot the NRF device immediately.
 */
void nrf_reboot(void);

/**
 * @brief Send raw UART data to the NRF device (for debugging purposes).
 *
 * @param data  Pointer to the data buffer
 * @param len   Length of the data buffer
 * @param timeout_ms  Timeout in milliseconds for the operation
 */
bool nrf_send_uart_data(const uint8_t *data, uint32_t len, uint32_t timeout_ms);

/**
 * @brief Check if an nRF device firmware update is required by comparing SHA256
 * hashes.
 *
 * @param image_ptr  Pointer to the firmware image in memory
 * @param image_len  Length of the firmware image in bytes
 * @return true if an update is required (e.g., corrupted image detected or hash
 * mismatch), false if the device already has the same firmware version
 */
bool nrf_update_required(const uint8_t *image_ptr, size_t image_len);

/**
 * @brief Perform a firmware update on the nRF device via DFU (Device Firmware
 * Update).
 *
 * @param image_ptr  Pointer to the firmware image in memory
 * @param image_len  Length of the firmware image in bytes
 * @return true always (indicates that the update process was initiated)
 */
bool nrf_update(const uint8_t *image_ptr, size_t image_len);

///////////////////////////////////////////////////////////////////////////////
// TEST-only functions

/**
 * @brief Test SPI communication with the NRF device.
 *
 * @return true if SPI communication succeeds; false otherwise
 */
bool nrf_test_spi_comm(void);

/**
 * @brief Test UART communication with the NRF device.
 *
 * @return true if UART communication succeeds; false otherwise
 */
bool nrf_test_uart_comm(void);

/**
 * @brief Test the NRF reset pin functionality.
 *
 * @return true if reset behavior is correct; false otherwise
 */
bool nrf_test_reset(void);

/**
 * @brief Test the GPIO pin that forces the device to stay in bootloader.
 *
 * @return true if the GPIO behaves correctly; false otherwise
 */
bool nrf_test_gpio_stay_in_bld(void);

/**
 * @brief Test a reserved GPIO pin on the NRF device.
 *
 * @return true if the GPIO behavior is correct; false otherwise
 */
bool nrf_test_gpio_reserved(void);
///////////////////////////////////////////////////////////////////////////////
