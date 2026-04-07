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

#include "secure_channel.h"
#include "hsm_keys.h"

#include "memzero.h"

#include "string.h"

typedef enum {
  SECURE_CHANNEL_STATE_0,  // Handshake has not been initiated yet
  SECURE_CHANNEL_STATE_1,  // Handshake in progress (after calling
                           // `secure_channel_handshake_1()` and before calling
                           // `secure_channel_handshake_2()`)
  SECURE_CHANNEL_STATE_2   // Handshake completed (after calling
                           // `secure_channel_handshake_2()`),
                           // `secure_channel_encrypt()` can be called
} noise_state_t;

static noise_state_t noise_state = SECURE_CHANNEL_STATE_0;
static noise_context_t noise_context = {0};

static curve25519_key prodtest_private_key = {
    0xc8, 0x56, 0x36, 0x89, 0xf5, 0xa6, 0x70, 0x66, 0x43, 0xeb, 0xe3,
    0x7e, 0xff, 0x7a, 0x2c, 0x20, 0x31, 0x27, 0x58, 0xbe, 0x5f, 0x01,
    0xc8, 0x6f, 0x9b, 0xe7, 0xe2, 0xe6, 0x0b, 0xee, 0x7e, 0x55};

static curve25519_key hsm_public_keys[] = {
#if PRODUCTION
#ifdef HSM_PUBLIC_PROD_X25519
    HSM_PUBLIC_PROD_X25519,
#endif
#ifdef HSM_PUBLIC_PROD_BACKUP_X25519
    HSM_PUBLIC_PROD_BACKUP_X25519,
#endif
#else
    HSM_PUBLIC_DEBUG_X25519,
#endif
};

bool secure_channel_handshake_1(uint8_t output[SECURE_CHANNEL_OUTPUT_SIZE]) {
  if (!noise_create_handshake_request(&noise_context,
                                      (noise_request_t*)output)) {
    return false;
  }

  noise_state = SECURE_CHANNEL_STATE_1;

  return true;
}

bool secure_channel_handshake_2(
    const uint8_t input[SECURE_CHANNEL_INPUT_SIZE]) {
  if (noise_state != SECURE_CHANNEL_STATE_1) {
    return false;
  }

  if (!noise_handle_handshake_response_multiple_keys(
          &noise_context, prodtest_private_key, hsm_public_keys,
          sizeof(hsm_public_keys) / sizeof(hsm_public_keys[0]),
          (const noise_response_t*)input)) {
    return false;
  }

  noise_state = SECURE_CHANNEL_STATE_2;
  return true;
}

bool secure_channel_encrypt(const uint8_t* plaintext, size_t plaintext_length,
                            const uint8_t* associated_data,
                            size_t associated_data_length,
                            uint8_t* ciphertext) {
  if (noise_state != SECURE_CHANNEL_STATE_2) {
    return false;
  }

  return noise_send_message(&noise_context, associated_data,
                            associated_data_length, plaintext, plaintext_length,
                            ciphertext);
}
