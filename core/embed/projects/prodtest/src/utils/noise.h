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

#include <trezor_rtl.h>

#define HASHLEN 32
#define DHLEN 32

// Uncomment to enable initiator/responder functionality in the noise protocol
// implementation.
#define USE_NOISE_INITIATOR
#define USE_NOISE_RESPONDER

typedef struct {
  uint8_t key[HASHLEN];
  bool has_key;
  uint64_t nonce;
} cipher_state_t;

typedef struct {
  uint8_t handshake_hash[HASHLEN];
  uint8_t chaining_key[HASHLEN];
  cipher_state_t cipher_state;
} symmetric_state_t;

typedef struct {
  cipher_state_t send_cipher_state;
  cipher_state_t receive_cipher_state;
  uint8_t handshake_hash[HASHLEN];
} transport_state_t;

typedef struct {
  symmetric_state_t symmetric_state;
  uint8_t static_private[DHLEN];
  uint8_t static_public[DHLEN];
  uint8_t psk[DHLEN];

  bool has_ephemeral_private;
  uint8_t ephemeral_private[DHLEN];

  bool has_remote_ephemeral_public;
  uint8_t remote_ephemeral_public[DHLEN];

  bool has_remote_static_public;
  uint8_t remote_static_public[DHLEN];

  bool has_transport_state;
  transport_state_t transport_state;
} noise_state_t;

#ifdef USE_NOISE_RESPONDER

/* TODO: think about giving those states some 32bit random numbers */
typedef enum {
  WAITING_FOR_REQUEST1,
  READY_FOR_RESPONSE1,
  WAITING_FOR_REQUEST2,
  RSPN_HANDSHAKE_COMPLETE
} responder_handshake_stage_t;

typedef struct {
  bool initialized;
  responder_handshake_stage_t handshake_stage;
  noise_state_t state;
} responder_xxpsk3_t;

#endif /* USE_NOISE_RESPONDER */

#ifdef USE_NOISE_INITIATOR

typedef enum {
  READY_FOR_REQUEST1,
  WAITING_FOR_RESPONSE1,
  READY_FOR_REQUEST2,
  INTR_HANDSHAKE_COMPLETE
} initiator_handshake_stage_t;

typedef struct {
  bool initialized;
  initiator_handshake_stage_t handshake_stage;
  noise_state_t state;
} initiator_xxpsk3_t;

#endif /* USE_NOISE_INITIATOR */

#ifdef USE_NOISE_RESPONDER

/**
 * follwing set of functions implements the responder side of
 * Noise_XXpsk3_25519_AESGCM_SHA256 protocol and has to be used in the following
 * order:
 *
 * 1. noise_responder_init() - to initialize the responder structure with the
 * pre-shared key and static key pair
 * 2. noise_responder_handle_request1() - to handle the first message from the
 * initiator and extract the initiator's ephemeral public key
 * 3. noise_responder_create_response1() - to create the response to the first
 * message, which includes the responder's ephemeral public key, encrypted
 * static public key and encrypted payload
 * 4. noise_responder_handle_request2() - to handle the second message from the
 * initiator, which includes the encrypted initiator's static
 *
 * Incorrect usage of the functions or incorrect message formats will lead to
 * error status being returned and the caller should handle it accordingly (e.g.
 * by terminating the connection). After the handshake is complete, the caller
 * can use the established transport state for secure communication.
 */

/**
 * @brief Initialize the responder structure with the pre-shared key and static
 * key pair.
 *
 * @param rspn Pointer to the responder structure to initialize
 * @param psk Pre-shared key for the Noise protocol (32 bytes)
 * @param static_private_key Static private key for the responder (32 bytes)
 * @return TS_OK if the responder was initialized correctly, error status
 * otherwise
 */
ts_t noise_responder_init(responder_xxpsk3_t *rspn, const uint8_t psk[DHLEN],
                          const uint8_t static_private_key[DHLEN]);

/**
 * @brief Deinitialize the responder structure and clear any sensitive data.
 *
 * @param rspn Pointer to the responder structure to deinitialize
 */
void noise_responder_deinit(responder_xxpsk3_t *rspn);

/**
 * @brief Handle request1 from handshake initiator.
 *
 * In: 	Incoming message format: <initiator_ephemeral_public_key[32B]>
 * Out: No response
 *
 * @param rspn Pointer to the responder structure
 * @param msg Incoming message buffer
 * @param msg_len Length of the incoming message buffer
 * @return TS_OK if the response was handled correctly
 */
ts_t noise_responder_handle_request1(responder_xxpsk3_t *rspn,
                                     const uint8_t *msg, size_t msg_len);

/**
 * @brief Create response to the first handshake message.
 *
 * In:    Response plain payload
 * Out:   Response message format:
 * <ephemeral_public_key[32B]><encrypted_static_public_key[48B]><encrypted_payload[payload_size
 * + 16B]>
 * @return TS_OK if the response was created correctly
 */
ts_t noise_responder_create_response1(responder_xxpsk3_t *rspn,
                                      const uint8_t *payload,
                                      uint8_t payload_size, uint8_t *response,
                                      size_t response_buf_size,
                                      size_t *response_size);

/**
 * @brief Handle second handshake message.
 *
 * In:    Request message format:
 * <encrypted_remote_static_public>[48B]+<empty_payload(just noise tag)>[16B]
 *
 * @return TS_OK if the message was correctly handled
 */
ts_t noise_responder_handle_request2(responder_xxpsk3_t *rspn,
                                     const uint8_t *msg, size_t msg_len);

/**
 * @brief Create response to the second handshake message.
 *
 * In:    Response plain payload
 * Out:   Response message format:
 * <encrypted_payload[payload_size + 16B]>
 *
 * @return TS_OK if the response was created correctly
 */
ts_t noise_responder_create_response2(responder_xxpsk3_t *rspn,
                                      uint8_t *response,
                                      size_t response_buf_size,
                                      size_t *response_size);

#endif /* USE_NOISE_RESPONDER */

#ifdef USE_NOISE_INITIATOR

ts_t noise_initiator_init(initiator_xxpsk3_t *intr, const uint8_t psk[DHLEN],
                          const uint8_t static_private_key[DHLEN]);

void noise_initiator_deinit(initiator_xxpsk3_t *intr);

ts_t noise_initiator_create_request1(initiator_xxpsk3_t *intr, uint8_t *request,
                                     size_t max_request_size,
                                     size_t *request_size);

ts_t noise_initiator_handle_response1(initiator_xxpsk3_t *intr,
                                      const uint8_t *msg, size_t msg_len,
                                      uint8_t *payload, size_t max_payload_size,
                                      size_t *payload_size);

ts_t noise_initiator_create_request2(initiator_xxpsk3_t *intr, uint8_t *request,
                                     size_t max_request_size,
                                     size_t *request_size);

ts_t noise_initiator_handle_response2(initiator_xxpsk3_t *intr,
                                      const uint8_t *msg, size_t msg_len);

#endif /* USE_NOISE_INITIATOR */
