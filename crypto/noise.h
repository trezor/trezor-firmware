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

#include "ed25519-donna/ed25519.h"

// Noise protocol using KK1 handshake pattern and X25519, AES-GCM and SHA256.
// The handshake messages and the prologue are empty.

#define NOISE_KEY_SIZE 32
#define NOISE_NONCE_SIZE 12
#define NOISE_TAG_SIZE 16

typedef struct {
  curve25519_key initiator_ephemeral_private_key;  // This is used only by the
                                                   // initiator during handshake
  uint8_t encryption_nonce[NOISE_NONCE_SIZE];
  uint8_t decryption_nonce[NOISE_NONCE_SIZE];
  // There is a time-memory trade-off between storing encryption/decryption keys
  // and storing encryption/decryption contexts, we choose to optimize for
  // memory usage by storing the keys
  uint8_t encryption_key[NOISE_KEY_SIZE];
  uint8_t decryption_key[NOISE_KEY_SIZE];
  bool initialized;
} noise_context_t;

typedef struct {
  curve25519_key initiator_ephemeral_public_key;
} noise_request_t;

typedef struct {
  curve25519_key responder_ephemeral_public_key;
  uint8_t tag[NOISE_TAG_SIZE];
} noise_response_t;

// This is called by the initiator to initialize the context and create the
// handshake request
bool noise_create_handshake_request(noise_context_t* ctx,
                                    noise_request_t* request);

// This is called by the responder to initialize the context, handle the
// handshake request and create the handshake response
bool noise_handle_handshake_request(noise_context_t* ctx,
                                    const curve25519_key initiator_public_key,
                                    const curve25519_key responder_private_key,
                                    const noise_request_t* request,
                                    noise_response_t* response);

// This is called by the initiator to handle the handshake response
bool noise_handle_handshake_response(noise_context_t* ctx,
                                     const curve25519_key initiator_private_key,
                                     const curve25519_key responder_public_key,
                                     noise_response_t* response);

// This is called by both the initiator and responder to send a message
// len(ciphertext) == plaintext_length + NOISE_TAG_SIZE
// The official Noise specification requires the associated_data to be empty
bool noise_send_message(noise_context_t* ctx, const uint8_t* associated_data,
                        size_t associated_data_length, const uint8_t* plaintext,
                        size_t plaintext_length, uint8_t* ciphertext);

// This is called by both the initiator and responder to receive a message
// len(plaintext) == ciphertext_length - NOISE_TAG_SIZE
// The official Noise specification requires the associated_data to be empty
bool noise_receive_message(noise_context_t* ctx, const uint8_t* associated_data,
                           size_t associated_data_length,
                           const uint8_t* ciphertext, size_t ciphertext_length,
                           uint8_t* plaintext);

#endif  // __NOISE_H__
