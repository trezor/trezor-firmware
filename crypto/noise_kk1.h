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

#ifndef __NOISE_KK1_H__
#define __NOISE_KK1_H__

#include "noise_common.h"

// Noise protocol using KK1 handshake pattern and X25519, AES-GCM and SHA256.
// The handshake messages and the prologue are empty.

typedef struct {
  curve25519_key initiator_ephemeral_public_key;
} noise_kk1_request_t;

typedef struct {
  curve25519_key responder_ephemeral_public_key;
  uint8_t tag[NOISE_TAG_SIZE];
} noise_kk1_response_t;

// This is called by the initiator to initialize the context and create the
// handshake request
bool noise_create_handshake_request(noise_context_t* ctx,
                                    noise_kk1_request_t* request);

// This is called by the responder to initialize the context, handle the
// handshake request and create the handshake response
bool noise_handle_handshake_request(noise_context_t* ctx,
                                    const curve25519_key initiator_public_key,
                                    const curve25519_key responder_private_key,
                                    const noise_kk1_request_t* request,
                                    noise_kk1_response_t* response);

// This is called by the initiator to handle the handshake response
bool noise_handle_handshake_response(noise_context_t* ctx,
                                     const curve25519_key initiator_private_key,
                                     const curve25519_key responder_public_key,
                                     const noise_kk1_response_t* response);

// This is called by the initiator to handle the handshake response
// This is a wrapper above noise_handle_handshake_response that allows to pass
// multiple responder public keys, the first key that succeeds in paring is
// used
bool noise_handle_handshake_response_multiple_keys(
    noise_context_t* ctx, const curve25519_key initiator_private_key,
    const curve25519_key* responder_public_keys,
    size_t responder_public_keys_count, const noise_kk1_response_t* response);

#endif  // __NOISE_KK1_H__
