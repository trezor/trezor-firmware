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
  UNLOCK_OK = -1431655766,  // sectrue
  UNLOCK_NOT_INITIALIZED = 1,
  UNLOCK_NO_PIN,
  UNLOCK_PIN_GET_FAILS_FAILED,
  UNLOCK_TOO_MANY_FAILS,
  UNLOCK_UI_ISSUE,
  UNLOCK_INCREASE_FAILS_FAILED,
  UNLOCK_INCORRECT_PIN,
  UNLOCK_WRONG_STORAGE_VERSION,
  UNLOCK_OPTIGA_HMAC_RESET_FAILED,
  UNLOCK_OPTIGA_COUNTER_RESET_FAILED,
  UNLOCK_TROPIC_RESET_MAC_AND_DESTROY_FAILED,
  UNLOCK_TROPIC_RESET_SLOTS_FAILED,
  UNLOCK_PIN_RESET_FAILS_FAILED,
  UNLOCK_UNKNOWN,
} storage_unlock_result_t;

typedef enum {
  PIN_CHANGE_OK = -1431655766,  // sectrue
  PIN_CHANGE_WIPE_CODE = 1,
  PIN_CHANGE_STORAGE_LOCKED,
  PIN_CHANGE_WRONG_ARGUMENT,
  PIN_CHANGE_NOT_INITIALIZED,
  PIN_CHANGE_CANNOT_SET_PIN,
  PIN_CHANGE_UNKNOWN,
} storage_pin_change_result_t;

typedef secbool (*PIN_UI_WAIT_CALLBACK)(uint32_t wait, uint32_t progress,
                                        enum storage_ui_message_t message);

void storage_init(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                  const uint16_t salt_len);
void storage_wipe(void);
secbool storage_is_unlocked(void);
void storage_lock(void);
storage_unlock_result_t storage_unlock(const uint8_t *pin, size_t pin_len,
                                       const uint8_t *ext_salt);
secbool storage_has_pin(void);
secbool storage_pin_fails_increase(void);
uint32_t storage_get_pin_rem(void);
storage_pin_change_result_t storage_change_pin(const uint8_t *newpin,
                                               size_t newpin_len,
                                               const uint8_t *new_ext_salt);
void storage_ensure_not_wipe_code(const uint8_t *pin, size_t pin_len);
secbool storage_has_wipe_code(void);
secbool storage_change_wipe_code(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt,
                                 const uint8_t *wipe_code,
                                 size_t wipe_code_len);
secbool storage_has(const uint16_t key);
secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len);
secbool storage_set(const uint16_t key, const void *val, const uint16_t len);
secbool storage_delete(const uint16_t key);
secbool storage_set_counter(const uint16_t key, const uint32_t count);
secbool storage_next_counter(const uint16_t key, uint32_t *count);

#endif
