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

#ifndef __NOISE_XX_H__
#define __NOISE_XX_H__

#include "noise_common.h"
#include "sha2.h"

// Noise protocol using XX handshake pattern and X25519, AES-GCM and SHA256.
// Includes responder key masking in addition to the basic protocol.
//
//  -> e               # initiation request, 1 byte payload
//  <- e, ee, s, es    # initiation response, empty payload
//  -> s, se           # completion request, payload <= NOISE_XX_MAX_PAYLOAD_LEN

#define NOISE_XX_MAX_PAYLOAD_LEN 128

typedef struct {
  curve25519_key initiator_ephemeral_public_key;
  uint8_t payload;
} noise_xx_initiation_request_t;

typedef struct {
  curve25519_key responder_ephemeral_public_key;
  uint8_t encrypted_responder_static_public_key[sizeof(curve25519_key) +
                                                NOISE_TAG_SIZE];
  uint8_t tag[NOISE_TAG_SIZE];
} noise_xx_initiation_response_t;

// Please note that this message has variable length and cannot be
// de/serialized by simple cast from/to a byte array.
typedef struct {
  uint8_t encrypted_initiator_static_public_key[sizeof(curve25519_key) +
                                                NOISE_TAG_SIZE];
  uint8_t encrypted_payload[NOISE_XX_MAX_PAYLOAD_LEN + NOISE_TAG_SIZE];
  size_t encrypted_payload_len;
} noise_xx_completion_request_t;

// Valid sequences for initiator:
// * INIT
// * I_SENT_INITIATION_REQUEST
// * I_RECEIVED_INITIATION_RESPONSE
// * FINISHED
// Valid sequences for responder:
// * INIT
// * R_RECEIVED_INITIATION_REQUEST
// * R_SENT_INITIATION_RESPONSE
// * FINISHED
// Any step can also transition to FAILED.
typedef enum {
  NOISE_XX_HANDSHAKE_INIT = 0,
  NOISE_XX_HANDSHAKE_I_SENT_INITIATION_REQUEST,
  NOISE_XX_HANDSHAKE_R_RECEIVED_INITIATION_REQUEST,
  NOISE_XX_HANDSHAKE_R_SENT_INITIATION_RESPONSE,
  NOISE_XX_HANDSHAKE_I_RECEIVED_INITIATION_RESPONSE,
  NOISE_XX_HANDSHAKE_FINISHED,
  NOISE_XX_HANDSHAKE_FAILED,
} noise_xx_handshake_step_t;

typedef struct {
  noise_xx_handshake_step_t step;
  curve25519_key ephemeral_private_key;
  curve25519_key remote_ephemeral_public_key;
  curve25519_key remote_static_public_key;
  uint8_t symmetric_key[NOISE_KEY_SIZE];
  uint8_t handshake_hash[SHA256_DIGEST_LENGTH];
  uint8_t chaining_key[SHA256_DIGEST_LENGTH];
} noise_xx_handshake_context_t;

// This is called by the initiator to initialize the handshake context and
// create the initiation request.
bool noise_xx_create_initiation_request(noise_xx_handshake_context_t* hctx,
                                        const uint8_t* prologue,
                                        size_t prologue_len, uint8_t payload,
                                        noise_xx_initiation_request_t* request);

// This is called by the responder to initialize the handshake context and
// handle the initiation request. After it obtains its static key (possibly
// based on received payload) it needs to call
// `noise_xx_create_initiation_response()`.
bool noise_xx_handle_initiation_request(
    noise_xx_handshake_context_t* hctx, const uint8_t* prologue,
    size_t prologue_len, uint8_t* payload,
    const noise_xx_initiation_request_t* request);

// This is called by the responder to create the initiation response.
bool noise_xx_create_initiation_response(
    noise_xx_handshake_context_t* hctx,
    const curve25519_key responder_static_private_key,
    noise_xx_initiation_response_t* response);

// This is called by the initiator to handle the initiation response. If the
// function successfully returns the initiator should choose its static key
// based on the values of `hctx.remote_static_public_key` and
// `hctx.remote_ephemeral_public_key` and call
// `noise_xx_create_completion_request()`.
bool noise_xx_handle_initiation_response(
    noise_xx_handshake_context_t* hctx,
    const noise_xx_initiation_response_t* response);

// This is called by the initiator to create the completion request. If the
// function successfully returns, `cctx` is initialized and can be used with
// `noise_send_message()` and `noise_receive_message()`. Please note that
// `payload_len` must be less or equal than `NOISE_XX_MAX_PAYLOAD_LEN`.
bool noise_xx_create_completion_request(
    noise_xx_handshake_context_t* hctx,
    const curve25519_key initiator_static_private_key, const uint8_t* payload,
    size_t payload_len, noise_context_t* cctx,
    noise_xx_completion_request_t* request);

// This is called by the responder to handle the completion request. If the
// function successfully returns, `cctx` is initialized and can be used with
// `noise_send_message()` and `noise_receive_message()`.
bool noise_xx_handle_completion_request(
    noise_xx_handshake_context_t* hctx,
    uint8_t payload[NOISE_XX_MAX_PAYLOAD_LEN], size_t* payload_len,
    noise_context_t* cctx, const noise_xx_completion_request_t* request);

#endif  // __NOISE_XX_H__
