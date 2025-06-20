/**
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef __NOISE_H__
#define __NOISE_H__

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Noise protocol using KK1 handshake pattern and X25519, AES-GCM and SHA256.
// The handshake messages and the prologue are empty.

#define KEY_SIZE 32
#define NONCE_SIZE 12
#define TAG_SIZE 16

typedef struct {
  uint8_t encryption_nonce[NONCE_SIZE];
  uint8_t decryption_nonce[NONCE_SIZE];
  uint8_t encryption_key[KEY_SIZE];
  uint8_t decryption_key[KEY_SIZE];
  bool initialized;
} noise_context_t;

typedef struct {
  uint8_t initiator_ephemeral_private_key[KEY_SIZE];
} noise_handshake_state_t;

typedef struct {
  uint8_t initiator_ephemeral_public_key[KEY_SIZE];
} noise_request_t;

typedef struct {
  uint8_t responder_ephemeral_public_key[KEY_SIZE];
  uint8_t tag[TAG_SIZE];
} noise_response_t;

// This is called by the initiator to create the handshake request
bool noise_create_handshake_request(noise_handshake_state_t* state,
                                    noise_request_t* request);

// This is called by the responder to handle the handshake request and create
// the handshake response
bool noise_handle_handshake_request(
    noise_context_t* ctx, const uint8_t initiator_public_key[KEY_SIZE],
    const uint8_t responder_private_key[KEY_SIZE], noise_request_t* request,
    noise_response_t* response);

// This is called by the initiator to handle the handshake response
bool noise_handle_handshake_response(
    noise_handshake_state_t* state, noise_context_t* ctx,
    const uint8_t initiator_private_key[KEY_SIZE],
    const uint8_t responder_public_key[KEY_SIZE], noise_response_t* response);

// This is called by both the initiator and responder to send a message
// len(ciphertext) == plaintext_length + TAG_SIZE
// The official Noise specification requires the associated_data to be empty
bool noise_send_message(noise_context_t* ctx, const uint8_t* associated_data,
                        size_t associated_data_length, const uint8_t* plaintext,
                        size_t plaintext_length, uint8_t* ciphertext);

// This is called by both the initiator and responder to receive a message
// len(plaintext) == ciphertext_length - TAG_SIZE
// The official Noise specification requires the associated_data to be empty
bool noise_receive_message(noise_context_t* ctx, const uint8_t* associated_data,
                           size_t associated_data_length,
                           const uint8_t* ciphertext, size_t ciphertext_length,
                           uint8_t* plaintext);

#endif  // __NOISE_H__
