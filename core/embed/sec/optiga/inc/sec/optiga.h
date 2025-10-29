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

#ifndef TREZORHAL_OPTIGA_H
#define TREZORHAL_OPTIGA_H

#include <trezor_types.h>

#include <sec/storage.h>

#include "optiga_common.h"

#define OPTIGA_DEVICE_CERT_INDEX 1
#define OPTIGA_DEVICE_ECC_KEY_INDEX 0
#define OPTIGA_FIDO_ECC_KEY_INDEX 2

typedef enum _optiga_pin_result {
  OPTIGA_PIN_SUCCESS = 0,       // The operation completed successfully.
  OPTIGA_PIN_INVALID,           // The PIN is invalid.
  OPTIGA_PIN_COUNTER_EXCEEDED,  // The PIN try counter limit was exceeded.
  OPTIGA_PIN_ERROR,             // Optiga processing or communication error.
} optiga_pin_result;

typedef enum _optiga_sign_result {
  OPTIGA_SIGN_SUCCESS = 0,   // The operation completed successfully.
  OPTIGA_SIGN_INACCESSIBLE,  // The signing key is inaccessible.
  OPTIGA_SIGN_ERROR,         // Invalid parameters or Optiga processing or
                             // communication error.
} optiga_sign_result;

// Size of secrets used in PIN processing, e.g. salted PIN, master secret etc.
#define OPTIGA_PIN_SECRET_SIZE 32

// Security event counter threshold to suspend optiga without postponing
// optiga deinitialization
#define OPTIGA_SEC_SUSPEND_THR 20

/**
 * @brief Initialize optiga driver
 *
 * @return OPTIGA_SUCCESS in case the driver was sucessfully initialized.
 */
optiga_result optiga_init(void);

/**
 * @brief Deinitialize optiga driver
 */
void optiga_deinit(void);

/**
 * @brief Deinitialize optiga driver with conditional power management
 *
 * @warning This function may leave the OPTIGA chip powered on under certain
 * conditions, resulting in increased power consumption. Use with caution in
 * power-sensitive applications.
 *
 * When the Security Event Counter (SEC) exceeds OPTIGA_SEC_SUSPEND_THR, this
 * function will suspend the driver but keep the OPTIGA chip powered to allow
 * the SEC counter to decrement naturally.
 *
 * @note Required follow-up procedure when OPTIGA remains powered:
 * 1. Call optiga_get_sec_clr_time() to get the estimated time (in seconds)
 *    needed for the SEC counter to clear
 * 2. Wait for the returned duration
 * 3. Call optiga_power_down() to safely power off the OPTIGA chip
 */
void optiga_soft_deinit(void);

/**
 * @brief Force immediate power down of the OPTIGA chip
 *
 * @note This function should be called after optiga_soft_deinit() and
 * waiting for the time returned by optiga_get_sec_clr_time().
 */
void optiga_power_down(void);

/**
 * @brief Get estimated time for Security Event Counter (SEC) to clear
 *
 * Retrieves the estimated time required for the OPTIGA chip's Security Event
 * Counter to decrement to a safe level, allowing for proper power down without
 * affecting future operations.
 *
 * @note This function should be called after optiga_soft_deinit() when the
 * OPTIGA chip remains powered due to elevated SEC counter. The returned time
 * represents the minimum wait period before calling optiga_power_down().
 * Returned `sec_clr_time` value is a not a actual counter value, but the
 * snapshot of the SOC counter value done during the `optiga_soft_deinit()`
 * call.
 *
 * @param sec_clr_time Pointer to store the estimated clear time in seconds.
 *
 * @return true when successfully retrieved the SEC clear time estimate
 */
bool optiga_get_sec_clr_time(uint32_t *sec_clr_time);

optiga_sign_result __wur optiga_sign(uint8_t index, const uint8_t *digest,
                                     size_t digest_size, uint8_t *der_signature,
                                     size_t max_der_signature_size,
                                     size_t *der_signature_size);
bool __wur optiga_cert_size(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                            size_t *cert_size);

bool __wur optiga_read_sec(uint8_t *sec);

void optiga_set_sec_max(void);

bool __wur optiga_random_buffer(uint8_t *dest, size_t size);

bool __wur optiga_pin_init(optiga_ui_progress_t ui_progress);

bool optiga_pin_stretch_cmac_ecdh(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

bool __wur optiga_pin_set(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pins[STRETCHED_PIN_COUNT][OPTIGA_PIN_SECRET_SIZE],
    uint8_t hmac_reset_key[OPTIGA_PIN_SECRET_SIZE]);

bool __wur
optiga_pin_reset_hmac_counter(optiga_ui_progress_t ui_progress,
                              const uint8_t reset_key[OPTIGA_PIN_SECRET_SIZE]);

uint32_t optiga_estimate_time_ms(storage_pin_op_t op, uint8_t slot_index);

optiga_pin_result __wur
optiga_pin_verify(optiga_ui_progress_t ui_progress, uint8_t index,
                  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

optiga_pin_result __wur
optiga_pin_verify_v4(optiga_ui_progress_t ui_progress,
                     const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                     uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]);

bool __wur optiga_pin_get_rem_v4(uint32_t *ctr);

bool __wur optiga_pin_get_rem(uint32_t *ctr);

bool __wur optiga_pin_decrease_rem_v4(uint32_t count);

bool __wur optiga_pin_decrease_rem(uint32_t count);

/* *****************************************************************************
 *  KERNEL PART
 * ****************************************************************************/

/**
 * @brief Suspends optiga driver
 *
 * @note This is part of driver is used in KERNEL_MODE since it schedules RTC
 * event to power down the optiga chip when its left powered up due to high
 * SEC counter value.
 */
void optiga_suspend();

/**
 * @brief Resumes optiga driver
 *
 * @note This part of driver is used in KERNEL_MODE since it handles/cancel
 * active RTC power down event when resuming from suspend.
 */
void optiga_resume();

#endif
