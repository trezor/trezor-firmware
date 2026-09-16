/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
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

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "xwing.h"

/**
 * Noise_pqIKpsk1_XWing_AESGCM_SHA256 — PQNoise pqIK handshake with a
 * pre-shared key (eprint 2022/539) instantiated with the X-Wing KEM.
 *
 *   <- s
 *   ...
 *   -> skem, e, s, psk   (request)
 *   <- ekem, skem        (response)
 *
 * The initiator must know the responder's static public key upfront.  Both
 * parties must know the 32-byte pre-shared key before the handshake.
 *
 * We follow the de-facto PQNoise semantics of the reference implementations
 * (yawning/nyquist experimental/pqnoise, clatter), i.e. the classical Noise
 * rev. 34 state machine with two new tokens:
 *   ekem: append ct in cleartext, MixHash(ct), MixKey(kk)
 *   skem: EncryptAndHash(ct), MixKeyAndHash(kk)
 * This deviates from the pseudocode in appendix G of the paper:
 *   1. Ephemeral public keys are never encrypted (MixHash only), matching
 *      sec. 2.1 of the paper and the Noise spec.
 *   2. Each token is encrypted separately with its own AEAD tag; tokens are
 *      not bundled into one ciphertext per key window.
 *   3. skem shared secrets use MixKeyAndHash (3-output HKDF), not a
 *      2-output KDF.
 *   4. Transport keys come from Split() (HKDF(ck, empty, 2)) after the last
 *      message, matching Fig. 1 of the paper; there is no finalize() special
 *      case for the last shared secret.
 * Wire format and test vectors are therefore cross-checkable against
 * nyquist/clatter, but NOT against appendix G of the paper.
 *
 * The psk1 modifier follows the classical Noise psk rules: the psk token
 * performs MixKeyAndHash(psk) and every `e` token additionally performs
 * MixKey(pk_e).  The paper does not analyze psk variants; pqIKpsk1 is our
 * construction by direct analogy with the named IKpsk1 pattern.
 *
 * Wire format (payload of n bytes):
 *
 *   request (3584 + n bytes):
 *     [0,    1120)  ct_r        encapsulation to the responder's static key,
 *                               cleartext
 *     [1120, 2336)  pk_e        initiator's ephemeral public key, cleartext
 *     [2336, 3568)  enc(pk_i)   initiator's static public key, encrypted
 *     [3568, ...)   enc(payload)  encrypted under a psk-mixed key
 *
 *   response (2272 + n bytes):
 *     [0,    1120)  ct_e        encapsulation to pk_e, cleartext
 *     [1120, 2256)  enc(ct_i)   encapsulation to pk_i, encrypted
 *     [2256, ...)   enc(payload)
 *
 * Security notes:
 *   - The request payload is 0-RTT data: it has no forward secrecy (it is
 *     protected only by the responder's static key and the psk) and the whole
 *     request can be replayed.  The responder must process it idempotently,
 *     or the payload should be left empty.
 *   - noise_pqikpsk1_responder_handle_request outputs the initiator's static
 *     public key; the caller must verify it against the expected key or an
 *     allowlist before using the channel.
 *   - The initiator's possession of its static key is confirmed to the
 *     responder only by the first successfully received transport message
 *     (knowledge of the psk is already confirmed by the request).
 *   - The handshake contexts hold ~4 KB of state; allocate them statically
 *     or on the heap rather than on the stack.
 */

#define NOISE_PQIKPSK1_HASHLEN 32
#define NOISE_PQIKPSK1_PSK_SIZE 32
#define NOISE_PQIKPSK1_TAG_SIZE 16

// Maximal size of a Noise message
#define NOISE_PQIKPSK1_MAX_MESSAGE_SIZE 65535

// Handshake message sizes without the payload
#define NOISE_PQIKPSK1_REQUEST_OVERHEAD                        \
  (XWING_CIPHERTEXT_SIZE + 2 * XWING_PUBLIC_KEY_SIZE + \
   2 * NOISE_PQIKPSK1_TAG_SIZE)
#define NOISE_PQIKPSK1_RESPONSE_OVERHEAD \
  (2 * XWING_CIPHERTEXT_SIZE + 2 * NOISE_PQIKPSK1_TAG_SIZE)

// Maximal payload sizes
#define NOISE_PQIKPSK1_MAX_REQUEST_PAYLOAD_SIZE \
  (NOISE_PQIKPSK1_MAX_MESSAGE_SIZE - NOISE_PQIKPSK1_REQUEST_OVERHEAD)
#define NOISE_PQIKPSK1_MAX_RESPONSE_PAYLOAD_SIZE \
  (NOISE_PQIKPSK1_MAX_MESSAGE_SIZE - NOISE_PQIKPSK1_RESPONSE_OVERHEAD)
#define NOISE_PQIKPSK1_MAX_PLAINTEXT_SIZE \
  (NOISE_PQIKPSK1_MAX_MESSAGE_SIZE - NOISE_PQIKPSK1_TAG_SIZE)

typedef struct {
  uint8_t key[NOISE_PQIKPSK1_HASHLEN];
  bool has_key;
  uint64_t nonce;
} noise_pqikpsk1_cipher_state_t;

typedef struct {
  uint8_t handshake_hash[NOISE_PQIKPSK1_HASHLEN];
  uint8_t chaining_key[NOISE_PQIKPSK1_HASHLEN];
  noise_pqikpsk1_cipher_state_t cipher_state;
} noise_pqikpsk1_symmetric_state_t;

typedef struct {
  noise_pqikpsk1_cipher_state_t send_cipher_state;
  noise_pqikpsk1_cipher_state_t receive_cipher_state;
  uint8_t handshake_hash[NOISE_PQIKPSK1_HASHLEN];
} noise_pqikpsk1_transport_state_t;

typedef struct {
  noise_pqikpsk1_symmetric_state_t symmetric_state;
  uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE];
  uint8_t static_private[XWING_PRIVATE_KEY_SIZE];
  uint8_t static_public[XWING_PUBLIC_KEY_SIZE];
  bool has_remote_static_public;
  uint8_t remote_static_public[XWING_PUBLIC_KEY_SIZE];
  bool has_ephemeral_private;
  uint8_t ephemeral_private[XWING_PRIVATE_KEY_SIZE];
  bool has_remote_ephemeral_public;
  uint8_t remote_ephemeral_public[XWING_PUBLIC_KEY_SIZE];
} noise_pqikpsk1_handshake_state_t;

// The stage values are random to make the state machine more robust against
// fault injection.
typedef enum {
  NOISE_PQIKPSK1_RSPN_WAITING_FOR_REQUEST = 0x4e21b6d3,
  NOISE_PQIKPSK1_RSPN_READY_FOR_RESPONSE = 0x9a70358c,
  NOISE_PQIKPSK1_RSPN_HANDSHAKE_COMPLETE = 0x17c5e24f
} noise_pqikpsk1_responder_handshake_stage_t;

typedef enum {
  NOISE_PQIKPSK1_INTR_READY_FOR_REQUEST = 0x62d90b3a,
  NOISE_PQIKPSK1_INTR_WAITING_FOR_RESPONSE = 0xc41f76a5,
  NOISE_PQIKPSK1_INTR_HANDSHAKE_COMPLETE = 0x2b8ea491
} noise_pqikpsk1_initiator_handshake_stage_t;

typedef struct {
  bool initialized;
  bool has_transport_state;
  noise_pqikpsk1_responder_handshake_stage_t handshake_stage;
  noise_pqikpsk1_handshake_state_t handshake_state;
  noise_pqikpsk1_transport_state_t transport_state;
} noise_pqikpsk1_responder_t;

typedef struct {
  bool initialized;
  bool has_transport_state;
  noise_pqikpsk1_initiator_handshake_stage_t handshake_stage;
  noise_pqikpsk1_handshake_state_t handshake_state;
  noise_pqikpsk1_transport_state_t transport_state;
} noise_pqikpsk1_initiator_t;

/**
 * @brief Initialize the initiator's handshake context.
 *
 * @param intr initiator context to initialize
 * @param psk pre-shared key, shared with the responder before the handshake
 * @param static_private_key initiator's static private key (X-Wing seed)
 * @param static_public_key initiator's static public key
 * @param responder_static_public_key responder's static public key
 * @param prologue optional prologue data agreed by both parties, may be NULL
 * if `prologue_size` is 0
 * @param prologue_size size of the prologue
 * @return bool
 */
bool noise_pqikpsk1_initiator_init(
    noise_pqikpsk1_initiator_t *intr,
    const uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE],
    const uint8_t static_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t responder_static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t *prologue, size_t prologue_size);

/**
 * @brief Deinitialize the initiator's context by zeroing it.
 *
 * @param intr initiator context
 */
void noise_pqikpsk1_initiator_deinit(noise_pqikpsk1_initiator_t *intr);

/**
 * @brief Create the handshake request (message 1).
 *
 * Note that the payload is 0-RTT data without forward secrecy which can be
 * replayed by an attacker, see the security notes above.
 *
 * On failure the context is deinitialized.
 *
 * @param intr initiator context
 * @param payload payload data, may be NULL if `payload_size` is 0
 * @param payload_size size of the payload, at most
 * NOISE_PQIKPSK1_MAX_REQUEST_PAYLOAD_SIZE
 * @param request output buffer for the request
 * @param max_request_size size of the `request` buffer, at least
 * NOISE_PQIKPSK1_REQUEST_OVERHEAD + `payload_size`
 * @param request_size outputs the size of the written request
 * @return bool
 */
bool noise_pqikpsk1_initiator_create_request(
    noise_pqikpsk1_initiator_t *intr, const uint8_t *payload,
    size_t payload_size, uint8_t *request, size_t max_request_size,
    size_t *request_size);

/**
 * @brief Create the handshake request from the given seeds.
 *
 * Provided for known-answer testing only, use
 * noise_pqikpsk1_initiator_create_request instead.
 *
 * @param intr initiator context
 * @param skem_seed encapsulation seed for the responder's static key
 * @param ephemeral_private_key initiator's ephemeral private key (X-Wing seed)
 * @param payload payload data, may be NULL if `payload_size` is 0
 * @param payload_size size of the payload
 * @param request output buffer for the request
 * @param max_request_size size of the `request` buffer
 * @param request_size outputs the size of the written request
 * @return bool
 */
bool noise_pqikpsk1_initiator_create_request_derand(
    noise_pqikpsk1_initiator_t *intr,
    const uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t ephemeral_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t *payload, size_t payload_size, uint8_t *request,
    size_t max_request_size, size_t *request_size);

/**
 * @brief Handle the handshake response (message 2).
 *
 * On success the handshake is complete and `intr->transport_state` can be
 * used with noise_pqikpsk1_send_message and noise_pqikpsk1_receive_message.
 *
 * On failure the context is deinitialized.
 *
 * @param intr initiator context
 * @param response received response
 * @param response_size size of the response
 * @param payload output buffer for the decrypted payload, may be NULL if
 * `max_payload_size` is 0
 * @param max_payload_size size of the `payload` buffer, at least
 * `response_size` - NOISE_PQIKPSK1_RESPONSE_OVERHEAD
 * @param payload_size outputs the size of the decrypted payload, may be NULL
 * @return bool
 */
bool noise_pqikpsk1_initiator_handle_response(
    noise_pqikpsk1_initiator_t *intr, const uint8_t *response,
    size_t response_size, uint8_t *payload, size_t max_payload_size,
    size_t *payload_size);

/**
 * @brief Initialize the responder's handshake context.
 *
 * @param rspn responder context to initialize
 * @param psk pre-shared key, shared with the initiator before the handshake
 * @param static_private_key responder's static private key (X-Wing seed)
 * @param static_public_key responder's static public key
 * @param prologue optional prologue data agreed by both parties, may be NULL
 * if `prologue_size` is 0
 * @param prologue_size size of the prologue
 * @return bool
 */
bool noise_pqikpsk1_responder_init(
    noise_pqikpsk1_responder_t *rspn,
    const uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE],
    const uint8_t static_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t *prologue, size_t prologue_size);

/**
 * @brief Deinitialize the responder's context by zeroing it.
 *
 * @param rspn responder context
 */
void noise_pqikpsk1_responder_deinit(noise_pqikpsk1_responder_t *rspn);

/**
 * @brief Handle the handshake request (message 1).
 *
 * The caller must verify the output initiator's static public key against the
 * expected key or an allowlist before using the channel.  The decrypted
 * payload is replayable 0-RTT data, see the security notes above.
 *
 * On failure the context is deinitialized.
 *
 * @param rspn responder context
 * @param request received request
 * @param request_size size of the request
 * @param initiator_static_public_key outputs the initiator's static public key
 * @param payload output buffer for the decrypted payload, may be NULL if
 * `max_payload_size` is 0
 * @param max_payload_size size of the `payload` buffer, at least
 * `request_size` - NOISE_PQIKPSK1_REQUEST_OVERHEAD
 * @param payload_size outputs the size of the decrypted payload, may be NULL
 * @return bool
 */
bool noise_pqikpsk1_responder_handle_request(
    noise_pqikpsk1_responder_t *rspn, const uint8_t *request,
    size_t request_size,
    uint8_t initiator_static_public_key[XWING_PUBLIC_KEY_SIZE],
    uint8_t *payload, size_t max_payload_size, size_t *payload_size);

/**
 * @brief Create the handshake response (message 2).
 *
 * On success the handshake is complete and `rspn->transport_state` can be
 * used with noise_pqikpsk1_send_message and noise_pqikpsk1_receive_message.
 * Note that the initiator is fully authenticated only by the first
 * successfully received transport message.
 *
 * On failure the context is deinitialized.
 *
 * @param rspn responder context
 * @param payload payload data, may be NULL if `payload_size` is 0
 * @param payload_size size of the payload, at most
 * NOISE_PQIKPSK1_MAX_RESPONSE_PAYLOAD_SIZE
 * @param response output buffer for the response
 * @param max_response_size size of the `response` buffer, at least
 * NOISE_PQIKPSK1_RESPONSE_OVERHEAD + `payload_size`
 * @param response_size outputs the size of the written response
 * @return bool
 */
bool noise_pqikpsk1_responder_create_response(
    noise_pqikpsk1_responder_t *rspn, const uint8_t *payload,
    size_t payload_size, uint8_t *response, size_t max_response_size,
    size_t *response_size);

/**
 * @brief Create the handshake response from the given seeds.
 *
 * Provided for known-answer testing only, use
 * noise_pqikpsk1_responder_create_response instead.
 *
 * @param rspn responder context
 * @param ekem_seed encapsulation seed for the initiator's ephemeral key
 * @param skem_seed encapsulation seed for the initiator's static key
 * @param payload payload data, may be NULL if `payload_size` is 0
 * @param payload_size size of the payload
 * @param response output buffer for the response
 * @param max_response_size size of the `response` buffer
 * @param response_size outputs the size of the written response
 * @return bool
 */
bool noise_pqikpsk1_responder_create_response_derand(
    noise_pqikpsk1_responder_t *rspn,
    const uint8_t ekem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t *payload, size_t payload_size, uint8_t *response,
    size_t max_response_size, size_t *response_size);

/**
 * @brief Encrypt a transport message.
 *
 * Follows the Noise specification, i.e. the associated data is empty.
 *
 * @param ts transport state
 * @param payload payload data, may be NULL if `payload_size` is 0
 * @param payload_size size of the payload, at most
 * NOISE_PQIKPSK1_MAX_PLAINTEXT_SIZE
 * @param ciphertext output buffer for the encrypted message
 * @param max_ciphertext_size size of the `ciphertext` buffer, at least
 * `payload_size` + NOISE_PQIKPSK1_TAG_SIZE
 * @param ciphertext_size outputs the size of the encrypted message
 * @return bool
 */
bool noise_pqikpsk1_send_message(noise_pqikpsk1_transport_state_t *ts,
                                 const uint8_t *payload, size_t payload_size,
                                 uint8_t *ciphertext,
                                 size_t max_ciphertext_size,
                                 size_t *ciphertext_size);

/**
 * @brief Decrypt a transport message.
 *
 * Follows the Noise specification, i.e. the associated data is empty.
 *
 * @param ts transport state
 * @param ciphertext received encrypted message
 * @param ciphertext_size size of the encrypted message
 * @param payload output buffer for the decrypted payload
 * @param max_payload_size size of the `payload` buffer, at least
 * `ciphertext_size` - NOISE_PQIKPSK1_TAG_SIZE
 * @param payload_size outputs the size of the decrypted payload
 * @return bool
 */
bool noise_pqikpsk1_receive_message(noise_pqikpsk1_transport_state_t *ts,
                                    const uint8_t *ciphertext,
                                    size_t ciphertext_size, uint8_t *payload,
                                    size_t max_payload_size,
                                    size_t *payload_size);
