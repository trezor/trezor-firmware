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

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#define NOISE_XXPSK3_HASHLEN 32
#define NOISE_XXPSK3_DHLEN 32

// Uncomment to enable initiator/responder functionality in the noise protocol
// implementation.
#define USE_NOISE_XXPSK3_INITIATOR
#define USE_NOISE_XXPSK3_RESPONDER

typedef struct {
  uint8_t key[NOISE_XXPSK3_HASHLEN];
  bool has_key;
  uint64_t nonce;
} noise_xxpsk3_cipher_state_t;

typedef struct {
  uint8_t handshake_hash[NOISE_XXPSK3_HASHLEN];
  uint8_t chaining_key[NOISE_XXPSK3_HASHLEN];
  noise_xxpsk3_cipher_state_t cipher_state;
} noise_xxpsk3_symmetric_state_t;

typedef struct {
  noise_xxpsk3_cipher_state_t send_cipher_state;
  noise_xxpsk3_cipher_state_t receive_cipher_state;
  uint8_t handshake_hash[NOISE_XXPSK3_HASHLEN];
} noise_xxpsk3_transport_state_t;

typedef struct {
  noise_xxpsk3_symmetric_state_t symmetric_state;
  uint8_t static_private[NOISE_XXPSK3_DHLEN];
  uint8_t static_public[NOISE_XXPSK3_DHLEN];
  uint8_t psk[NOISE_XXPSK3_DHLEN];

  bool has_ephemeral_private;
  uint8_t ephemeral_private[NOISE_XXPSK3_DHLEN];

  bool has_remote_ephemeral_public;
  uint8_t remote_ephemeral_public[NOISE_XXPSK3_DHLEN];

  bool has_remote_static_public;
  uint8_t remote_static_public[NOISE_XXPSK3_DHLEN];

} noise_xxpsk3_handshake_state_t;

#ifdef USE_NOISE_XXPSK3_RESPONDER

// Random values are used for greater resilience agains glitching attacks.
typedef enum {
  WAITING_FOR_REQUEST1 = 0x5091d95c,
  READY_FOR_RESPONSE1 = 0x252d533a,
  WAITING_FOR_REQUEST2 = 0xe3b601eb,
  RSPN_HANDSHAKE_COMPLETE = 0x54acac08
} noise_xxpsk3_responder_handshake_stage_t;

typedef struct {
  bool initialized;
  bool has_transport_state;
  noise_xxpsk3_responder_handshake_stage_t handshake_stage;
  noise_xxpsk3_handshake_state_t handshake_state;
  noise_xxpsk3_transport_state_t transport_state;
} noise_xxpsk3_responder_t;

#endif /* USE_NOISE_XXPSK3_RESPONDER */

#ifdef USE_NOISE_XXPSK3_INITIATOR

// Random values are used for greater resilience agains glitching attacks.
typedef enum {
  READY_FOR_REQUEST1 = 0x24a23a5e,
  WAITING_FOR_RESPONSE1 = 0xa748a792,
  READY_FOR_REQUEST2 = 0xba244240,
  INTR_HANDSHAKE_COMPLETE = 0xf149f042
} noise_xxpsk3_initiator_handshake_stage_t;

typedef struct {
  bool initialized;
  bool has_transport_state;
  noise_xxpsk3_initiator_handshake_stage_t handshake_stage;
  noise_xxpsk3_handshake_state_t handshake_state;
  noise_xxpsk3_transport_state_t transport_state;
} noise_xxpsk3_initiator_t;

/**
 * The following set of functions implements the initiator side of the
 * Noise_XXpsk3_25519_AESGCM_SHA256 protocol and has to be used in the following
 * order:
 *
 * 1. noise_xxpsk3_initiator_init() - to initialize the initiator structure with
 * the pre-shared key and static key pair
 * 2. noise_xxpsk3_initiator_create_request1() - to create the first message,
 * which includes the initiator's ephemeral public key and an encrypted payload
 * 3. noise_xxpsk3_initiator_handle_response1() - to handle the response from
 * the responder, which includes the responder's ephemeral public key, encrypted
 * static public key and encrypted payload
 * 4. noise_xxpsk3_initiator_create_request2() - to create the second message,
 * which includes the initiator's encrypted static public key and an encrypted
 * payload, completing the handshake
 *
 * Incorrect usage of the functions or incorrect message formats will lead to a
 * false status being returned and the caller should handle it accordingly (e.g.
 * by terminating the connection). After the handshake is complete, the caller
 * can use the established transport state for secure communication.
 */

/**
 * @brief Initialize the initiator structure with the pre-shared key and static
 * key pair.
 *
 * @param intr Pointer to the initiator structure to initialize
 * @param psk Pre-shared key for the Noise protocol (32 bytes)
 * @param static_private_key Static private key for the initiator (32 bytes)
 * @return true if the initiator was initialized correctly, false otherwise
 */
bool noise_xxpsk3_initiator_init(
    noise_xxpsk3_initiator_t *intr, const uint8_t psk[NOISE_XXPSK3_DHLEN],
    const uint8_t static_private_key[NOISE_XXPSK3_DHLEN]);

/**
 * @brief Deinitialize the initiator structure and clear any sensitive data.
 *
 * @param intr Pointer to the initiator structure to deinitialize
 */
void noise_xxpsk3_initiator_deinit(noise_xxpsk3_initiator_t *intr);

/**
 * @brief Create request1, the first handshake message from the initiator.
 *
 * Generates the initiator's ephemeral key pair and, because this is a PSK
 * handshake, mixes the ephemeral public key into the cipher key so the payload
 * is encrypted.
 *
 * In:    Request plain payload
 * Out:   Request message format:
 * <ephemeral_public_key[32B]><encrypted_payload[payload_size + 16B]>
 *
 * @param intr Pointer to the initiator structure
 * @param payload Plain payload to send (may be empty)
 * @param payload_size Length of the payload in bytes
 * @param request Output buffer for the request message
 * @param max_request_size Size of the output buffer
 * @param request_size Set to the number of bytes written to the request buffer
 * @return true if the request was created correctly, false otherwise
 */
bool noise_xxpsk3_initiator_create_request1(
    noise_xxpsk3_initiator_t *intr, const uint8_t *payload, size_t payload_size,
    uint8_t *request, size_t max_request_size, size_t *request_size);

/**
 * @brief Handle response1, the response to the first handshake message.
 *
 * Processes the responder's ephemeral public key, performs the ee and es DH
 * operations, decrypts and authenticates the responder's static public key,
 * and decrypts the response payload.
 *
 * In:    Incoming response format:
 * <ephemeral_public_key[32B]><encrypted_static_public_key[48B]><encrypted_payload[payload_size
 * + 16B]>
 * Out:   Decrypted payload
 *
 * @param intr Pointer to the initiator structure
 * @param response Incoming response buffer
 * @param response_len Length of the incoming response buffer
 * @param payload Output buffer for the decrypted payload
 * @param max_payload_size Size of the output buffer
 * @param payload_size Set to the number of decrypted payload bytes
 * @return true if the response was handled correctly, false otherwise
 */
bool noise_xxpsk3_initiator_handle_response1(noise_xxpsk3_initiator_t *intr,
                                             const uint8_t *response,
                                             size_t response_len,
                                             uint8_t *payload,
                                             size_t max_payload_size,
                                             size_t *payload_size);

/**
 * @brief Create request2, the third handshake message from the initiator.
 *
 * Encrypts and sends the initiator's static public key, performs the se DH
 * operation, mixes in the pre-shared key, encrypts the payload, and completes
 * the handshake by deriving the transport state.
 *
 * In:    Request plain payload
 * Out:   Request message format:
 * <encrypted_static_public_key[48B]><encrypted_payload[payload_size + 16B]>
 *
 * @param intr Pointer to the initiator structure
 * @param payload Plain payload to send (may be empty)
 * @param payload_size Length of the payload in bytes
 * @param request Output buffer for the request message
 * @param max_request_size Size of the output buffer
 * @param request_size Set to the number of bytes written to the request buffer
 * @return true if the request was created correctly, false otherwise
 */
bool noise_xxpsk3_initiator_create_request2(
    noise_xxpsk3_initiator_t *intr, const uint8_t *payload, size_t payload_size,
    uint8_t *request, size_t max_request_size, size_t *request_size);

#endif /* USE_NOISE_XXPSK3_INITIATOR */

#ifdef USE_NOISE_XXPSK3_RESPONDER

/**
 * The following set of functions implements the responder side of the
 * Noise_XXpsk3_25519_AESGCM_SHA256 protocol and has to be used in the following
 * order:
 *
 * 1. noise_xxpsk3_responder_init() - to initialize the responder structure with
 * the pre-shared key and static key pair
 * 2. noise_xxpsk3_responder_handle_request1() - to handle the first message
 * from the initiator and extract the initiator's ephemeral public key
 * 3. noise_xxpsk3_responder_create_response1() - to create the response to the
 * first message, which includes the responder's ephemeral public key, encrypted
 * static public key and encrypted payload
 * 4. noise_xxpsk3_responder_handle_request2() - to handle the second message
 * from the initiator, which includes the initiator's encrypted static public
 * key, completing the handshake
 *
 * Incorrect usage of the functions or incorrect message formats will lead to a
 * false status being returned and the caller should handle it accordingly (e.g.
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
 * @return true if the responder was initialized correctly, false otherwise
 */
bool noise_xxpsk3_responder_init(
    noise_xxpsk3_responder_t *rspn, const uint8_t psk[NOISE_XXPSK3_DHLEN],
    const uint8_t static_private_key[NOISE_XXPSK3_DHLEN]);

/**
 * @brief Deinitialize the responder structure and clear any sensitive data.
 *
 * @param rspn Pointer to the responder structure to deinitialize
 */
void noise_xxpsk3_responder_deinit(noise_xxpsk3_responder_t *rspn);

/**
 * @brief Handle request1 from the handshake initiator.
 *
 * Because this is a PSK handshake, request1 carries an encrypted payload after
 * the initiator's ephemeral public key. The payload is decrypted and returned
 * to the caller.
 *
 * In:    Incoming request format:
 * <initiator_ephemeral_public_key[32B]><encrypted_payload[payload_size + 16B]>
 * Out:   Decrypted payload
 *
 * @param rspn Pointer to the responder structure
 * @param request Incoming request buffer
 * @param request_len Length of the incoming request buffer
 * @param payload Output buffer for the decrypted payload
 * @param max_payload_size Size of the output buffer
 * @param payload_size Set to the number of decrypted payload bytes
 * @return true if the request was handled correctly, false otherwise
 */
bool noise_xxpsk3_responder_handle_request1(
    noise_xxpsk3_responder_t *rspn, const uint8_t *request, size_t request_len,
    uint8_t *payload, size_t max_payload_size, size_t *payload_size);

/**
 * @brief Create response to the first handshake message.
 *
 * In:    Response plain payload
 * Out:   Response message format:
 * <ephemeral_public_key[32B]><encrypted_static_public_key[48B]><encrypted_payload[payload_size
 * + 16B]>
 *
 * @param rspn Pointer to the responder structure
 * @param payload Plain payload to send (may be empty)
 * @param payload_size Length of the payload in bytes
 * @param response Output buffer for the response message
 * @param max_response_size Size of the output buffer
 * @param response_size Set to the number of bytes written to the response
 * buffer
 * @return true if the response was created correctly, false otherwise
 */
bool noise_xxpsk3_responder_create_response1(
    noise_xxpsk3_responder_t *rspn, const uint8_t *payload, size_t payload_size,
    uint8_t *response, size_t max_response_size, size_t *response_size);

/**
 * @brief Handle the second handshake message.
 *
 * Decrypts and authenticates the initiator's static public key, performs the se
 * DH operation, mixes in the pre-shared key, decrypts the payload, and derives
 * the transport state, completing the handshake.
 *
 * In:    Request message format:
 * <encrypted_remote_static_public[48B]><encrypted_payload[payload_size + 16B]>
 * Out:   Decrypted payload
 *
 * @param rspn Pointer to the responder structure
 * @param request Incoming request buffer
 * @param request_len Length of the incoming request buffer
 * @param payload Output buffer for the decrypted payload
 * @param max_payload_size Size of the output buffer
 * @param payload_size Set to the number of decrypted payload bytes
 * @return true if the request was handled correctly, false otherwise
 */
bool noise_xxpsk3_responder_handle_request2(
    noise_xxpsk3_responder_t *rspn, const uint8_t *request, size_t request_len,
    uint8_t *payload, size_t max_payload_size, size_t *payload_size);

#endif /* USE_NOISE_XXPSK3_RESPONDER */

/**
 * @brief Encrypt a transport message on the send cipher state.
 *
 * @param ts Pointer to the established transport state
 * @param payload Plaintext to encrypt (may be empty)
 * @param payload_size Length of the plaintext in bytes
 * @param ciphertext Output buffer for the encrypted message
 * @param max_ciphertext_size Size of the output buffer; must be at least
 * payload_size + 16
 * @param ciphertext_size Set to the number of bytes written
 * (payload_size + 16)
 * @return true if the message was encrypted correctly, false otherwise
 */
bool noise_xxpsk3_send_message(noise_xxpsk3_transport_state_t *ts,
                               const uint8_t *payload, size_t payload_size,
                               uint8_t *ciphertext, size_t max_ciphertext_size,
                               size_t *ciphertext_size);

/**
 * @brief Decrypt a transport message on the receive cipher state.
 *
 * @param ts Pointer to the established transport state
 * @param ciphertext Encrypted message to decrypt
 * @param ciphertext_size Length of the encrypted message; must be at least 16
 * @param payload Output buffer for the decrypted plaintext
 * @param max_payload_size Size of the output buffer; must be at least
 * ciphertext_size - 16
 * @param payload_size Set to the number of decrypted plaintext bytes
 * (ciphertext_size - 16)
 * @return true if the message was decrypted and authenticated correctly, false
 * otherwise
 */
bool noise_xxpsk3_receive_message(noise_xxpsk3_transport_state_t *ts,
                                  const uint8_t *ciphertext,
                                  size_t ciphertext_size, uint8_t *payload,
                                  size_t max_payload_size,
                                  size_t *payload_size);
