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

#ifndef __STORAGE_H__
#define __STORAGE_H__

#include <stddef.h>
#include <stdint.h>
#include "secbool.h"

// The length of the external salt in bytes.
#define EXTERNAL_SALT_SIZE 32

/**
 * Each value in the storage is identified by a 16-bit norcow storage key:
 *
 *  | 15     | 14       | 13 .. 8 | 7 .. 0   |
 *  | PUBLIC | WRITABLE | app_id  | entry id |
 *
 * The high byte consists of two flag bits and a 6-bit app_id designating the
 * application that owns the entry. The low byte distinguishes the individual
 * entries of the application.
 *
 * If the PUBLIC bit (FLAG_PUBLIC) is set, the value is stored unencrypted and
 * can be read even when the storage is locked. If both flag bits (FLAGS_WRITE)
 * are set, the value can also be written and deleted while locked.
 *
 * APP == 0x00 is reserved for the storage's internal entries; the public API
 * rejects keys in that namespace.
 */

// If the top bit of APP is set, then the value is not encrypted.
#define FLAG_PUBLIC 0x80

// If the top two bits of APP are set, then the value is not encrypted and it
// can be written even when the storage is locked.
#define FLAGS_WRITE 0xC0

// The maximum value of app_id which is the six least significant bits of APP.
#define MAX_APPID 0x3F

// The PIN value corresponding to an empty PIN.
extern const uint8_t *PIN_EMPTY;
#define PIN_EMPTY_LEN 0

// Maximum number of failed unlock attempts.
// NOTE: The PIN counter logic relies on this constant being less than or equal
// to 16.
#if USE_TROPIC
// If both Optiga and Tropic are used, every PIN attempt requires a stretched
// PIN slot in Optiga. This restricts the total number of PIN attempts to 10.
// For simplicity we set the number of attempts to 10 when Tropic is used
// without Optiga, even though more attempts could be supported.
#define PIN_MAX_TRIES 10
#else
#define PIN_MAX_TRIES 16
#endif

// The number of slots configured as stretched PINs.
#if USE_TROPIC
#define STRETCHED_PIN_COUNT PIN_MAX_TRIES
#else
#define STRETCHED_PIN_COUNT 1
#endif

// The length of the random salt in bytes.
#if USE_OPTIGA
#define STORAGE_SALT_SIZE 32
#else
#define STORAGE_SALT_SIZE 4
#endif

enum storage_ui_message_t {
  NO_MSG = 0,
  VERIFYING_PIN_MSG,
  PROCESSING_MSG,
  STARTING_MSG,
  WRONG_PIN_MSG,
};

typedef enum {
  STORAGE_PIN_OP_SET = 0,
  STORAGE_PIN_OP_VERIFY,
} storage_pin_op_t;

typedef enum {
  UNLOCK_OK = 0,
  UNLOCK_NOT_INITIALIZED = 1,
  UNLOCK_NO_PIN,
  UNLOCK_PIN_GET_FAILS_FAILED,
  UNLOCK_TOO_MANY_FAILS,
  UNLOCK_UI_CANCELLED,
  UNLOCK_INCREASE_FAILS_FAILED,
  UNLOCK_INCORRECT_PIN,
  UNLOCK_WRONG_STORAGE_VERSION,
  UNLOCK_OPTIGA_GET_HMAC_RESET_KEY_FAILED,
  UNLOCK_OPTIGA_HMAC_COUNTER_RESET_FAILED,
  UNLOCK_GET_TROPIC_MAC_AND_DESTROY_RESET_KEY_FAILED,
  UNLOCK_TROPIC_RESET_SLOTS_FAILED,
  UNLOCK_PIN_RESET_FAILS_FAILED,
  UNLOCK_ACCESS_VIOLATION,
  UNLOCK_UNKNOWN,
} storage_unlock_result_t;

typedef enum {
  PIN_CHANGE_OK = 0,
  PIN_CHANGE_WIPE_CODE = 1,
  PIN_CHANGE_STORAGE_LOCKED,
  PIN_CHANGE_WRONG_ARGUMENT,
  PIN_CHANGE_NOT_INITIALIZED,
  PIN_CHANGE_CANNOT_SET_PIN,
  PIN_CHANGE_ACCESS_VIOLATION,
  PIN_CHANGE_UNKNOWN,
} storage_pin_change_result_t;

/**
 * @brief Callback invoked during long-running PIN operations.
 *
 * Storage calls the callback with progress = 0 to initialize the UI dialog and
 * with progress = 1000 to terminate the UI dialog.
 *
 * @param wait Estimated remaining time in seconds
 * @param progress Progress of the operation, from 0 to 1000
 * @param message Message to be shown to the user
 * @return sectrue to abort the operation, secfalse to continue it
 */
typedef secbool (*PIN_UI_WAIT_CALLBACK)(uint32_t wait, uint32_t progress,
                                        enum storage_ui_message_t message);

/**
 * @brief Initializes the storage, upgrading its format if necessary.
 *
 * If the storage contains no EDEK_PVC_KEY entry, it is initialized to the wiped
 * state.
 *
 * If the format upgrade fails, the storage is wiped.
 *
 * An already initialized storage is left locked. A storage that had to be
 * initialized to the wiped state is left unlocked, since the wiped state has
 * an empty PIN.
 *
 * @param callback Callback invoked during long-running PIN operations, or NULL
 * to report no progress
 * @param salt Hardware-derived salt mixed into the key derivation. Must not be
 * NULL unless salt_len is 0
 * @param salt_len Length of salt in bytes
 */
void storage_init(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                  const uint16_t salt_len);

/**
 * @brief Erases the storage and re-initializes it to the wiped state.
 */
void storage_wipe(void);

/**
 * @brief Tells whether the storage is unlocked.
 *
 * @return sectrue if the storage is initialized and unlocked, secfalse
 * otherwise
 */
secbool storage_is_unlocked(void);

/**
 * @brief Locks the storage, discarding the cached encryption keys.
 */
void storage_lock(void);

/**
 * @brief Unlocks the storage with the given PIN.
 *
 * Every attempt consumes one of the PIN_MAX_TRIES tries; the counter is reset
 * once the PIN is verified. Progress is reported through the callback
 * registered by storage_init(), which may abort the operation.
 *
 * @param pin PIN to verify, PIN_EMPTY for an empty PIN. If NULL, the function
 * fails with UNLOCK_NO_PIN
 * @param pin_len Length of pin in bytes
 * @param ext_salt External salt of EXTERNAL_SALT_SIZE bytes, or NULL to mix in
 * no external salt
 * @return UNLOCK_OK on success, otherwise the reason for the failure
 */
storage_unlock_result_t storage_unlock(const uint8_t *pin, size_t pin_len,
                                       const uint8_t *ext_salt);

/**
 * @brief Tells whether a non-empty PIN is set.
 *
 * @return sectrue if the PIN is set and not empty, secfalse otherwise
 */
secbool storage_has_pin(void);

/**
 * @brief Increments the PIN failure counter.
 *
 * @return sectrue if the counter was incremented, secfalse otherwise
 */
secbool storage_pin_fails_increase(void);

/**
 * @brief Returns the number of remaining PIN attempts.
 *
 * @return Number of attempts left, or 0 if the storage is not initialized or
 * the counter could not be read
 */
uint32_t storage_get_pin_rem(void);

/**
 * @brief Changes the PIN.
 *
 * The storage must be unlocked. The new PIN must differ from the wipe code.
 * Progress is reported through the callback registered by storage_init().
 *
 * @param newpin New PIN, PIN_EMPTY to remove the PIN. If NULL, the function
 * fails with PIN_CHANGE_WRONG_ARGUMENT
 * @param newpin_len Length of newpin in bytes
 * @param new_ext_salt New external salt of EXTERNAL_SALT_SIZE bytes, or NULL
 * to mix in no external salt
 * @return PIN_CHANGE_OK on success, otherwise the reason for the failure
 */
storage_pin_change_result_t storage_change_pin(const uint8_t *newpin,
                                               size_t newpin_len,
                                               const uint8_t *new_ext_salt);

/**
 * @brief Wipes the storage if the given PIN is the wipe code.
 *
 * On a match the storage is wiped and the wipe code screen is shown, and the
 * function does not return.
 *
 * @param pin PIN to check. Must not be NULL
 * @param pin_len Length of pin in bytes
 */
void storage_ensure_not_wipe_code(const uint8_t *pin, size_t pin_len);

/**
 * @brief Tells whether a wipe code is set.
 *
 * @return sectrue if a wipe code is set, secfalse otherwise, in particular if
 * the storage is locked
 */
secbool storage_has_wipe_code(void);

/**
 * @brief Changes the wipe code, verifying the PIN first.
 *
 * Progress is reported through the callback registered by storage_init().
 *
 * @param pin PIN to verify, PIN_EMPTY for an empty PIN. If NULL, the function
 * fails
 * @param pin_len Length of pin in bytes
 * @param ext_salt External salt of EXTERNAL_SALT_SIZE bytes, or NULL to mix in
 * no external salt
 * @param wipe_code New wipe code, which must differ from the PIN. If NULL, the
 * function fails; pass wipe_code_len of 0 to remove the wipe code
 * @param wipe_code_len Length of wipe_code in bytes
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_change_wipe_code(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt,
                                 const uint8_t *wipe_code,
                                 size_t wipe_code_len);

/**
 * @brief Tells whether a value is stored under the given key.
 *
 * @param key Norcow storage key of the value, see above
 * @return sectrue if the value exists and is readable, secfalse otherwise
 */
secbool storage_has(const uint16_t key);

/**
 * @brief Reads the value stored under the given key.
 *
 * @param key Norcow storage key of the value, see above
 * @param val Buffer receiving the value, or NULL together with max_len 0 to
 * query only the length of the value
 * @param max_len Size of val in bytes; the call fails if the value is longer
 * @param len Receives the length of the value in bytes. Must not be NULL
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len);

/**
 * @brief Stores a value under the given key.
 *
 * @param key Norcow storage key of the value, see above
 * @param val Value to store. Must not be NULL unless len is 0
 * @param len Length of val in bytes
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_set(const uint16_t key, const void *val, const uint16_t len);

/**
 * @brief Deletes the value stored under the given key.
 *
 * @param key Norcow storage key of the value, see above
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_delete(const uint16_t key);

/**
 * @brief Sets the counter stored under the given key.
 *
 * Counters are public values, so key must have FLAG_PUBLIC set.
 *
 * @param key Norcow storage key of the counter, see above
 * @param count Value to set the counter to
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_set_counter(const uint16_t key, const uint32_t count);

/**
 * @brief Increments the counter stored under the given key and reads it back.
 *
 * If the counter does not exist yet, it is created and set to 0. Counters are
 * public values, so key must have FLAG_PUBLIC set.
 *
 * @param key Norcow storage key of the counter, see above
 * @param count Receives the new value of the counter. Must not be NULL
 * @return sectrue on success, secfalse otherwise
 */
secbool storage_next_counter(const uint16_t key, uint32_t *count);

#endif
