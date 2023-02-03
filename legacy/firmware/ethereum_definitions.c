/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2022 Martin Novak <martin.novak@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdbool.h>
#include <string.h>

#include "crypto.h"
#include "ethereum.h"
#include "ethereum_definitions.h"
#include "ethereum_definitions_constants.h"
#include "ethereum_networks.h"
#include "ethereum_tokens.h"
#include "fsm.h"
#include "gettext.h"
#include "memzero.h"
#include "messages.h"
#include "pb.h"
#include "pb_decode.h"
#include "trezor.h"  // because of the "VERSTR" macro used in "fsm_sendFailureDebug" function
#include "util.h"

typedef pb_byte_t proof_entry[SHA256_DIGEST_LENGTH];

struct EncodedDefinition {
  // prefix
  pb_byte_t format_version[FORMAT_VERSION_LENGTH];
  uint8_t definition_type;
  uint32_t data_version;
  uint16_t payload_length;

  // payload
  const pb_byte_t *payload;

  // suffix
  uint8_t proof_length;
  const proof_entry *proof;

  const ed25519_signature *signed_root_hash;
};

static bool parse_encoded_definition(struct EncodedDefinition *const result,
                                     const pb_size_t size,
                                     const pb_byte_t *bytes) {
  // format version + definition type + data version + payload length + payload
  // (at least 1B) + proof length + signed Merkle tree root hash
  if (size < (FORMAT_VERSION_LENGTH + 1 + 4 + 2 + 1 + 1 +
              MERKLE_TREE_SIGNED_ROOT_SIZE)) {
    return false;
  }

  const pb_byte_t *cursor = bytes;
  memcpy(result->format_version, cursor, FORMAT_VERSION_LENGTH);
  cursor += FORMAT_VERSION_LENGTH;

  result->definition_type = *cursor;
  cursor += 1;

  result->data_version = *(uint32_t *)cursor;
  cursor += 4;

  result->payload_length = *(uint16_t *)cursor;
  cursor += 2;

  result->payload = cursor;
  cursor += result->payload_length;

  if (size <= cursor - bytes) {
    return false;
  }
  result->proof_length = *cursor;
  cursor += 1;

  // check the whole size of incoming bytes array
  if (size != (cursor - bytes) + result->proof_length * sizeof(proof_entry) +
                  MERKLE_TREE_SIGNED_ROOT_SIZE) {
    return false;
  }
  result->proof = (proof_entry *)cursor;
  cursor += result->proof_length * sizeof(proof_entry);

  result->signed_root_hash = (ed25519_signature *)cursor;

  return true;
}

static bool decode_definition(const pb_size_t size, const pb_byte_t *bytes,
                              const EthereumDefinitionType expected_type,
                              void *definition) {
  // parse received definition
  static struct EncodedDefinition parsed_def;
  const char *error_str = _("Invalid Ethereum definition");

  memzero(&parsed_def, sizeof(parsed_def));
  if (!parse_encoded_definition(&parsed_def, size, bytes)) {
    goto err;
  }

  // check definition fields
  if (memcmp(FORMAT_VERSION, parsed_def.format_version,
             FORMAT_VERSION_LENGTH)) {
    goto err;
  }

  if (expected_type != parsed_def.definition_type) {
    error_str = _("Definition type mismatch");
    goto err;
  }

  if (MIN_DATA_VERSION > parsed_def.data_version) {
    error_str = _("Definition is outdated");
    goto err;
  }

  // compute Merkle tree root hash from proof
  uint8_t hash[SHA256_DIGEST_LENGTH] = {0};
  SHA256_CTX context = {0};
  sha256_Init(&context);

  // leaf hash = sha256('\x00' + leaf data)
  sha256_Update(&context, (uint8_t[]){0}, 1);
  // signed data is everything from start of `bytes` to the end of `payload`
  const pb_byte_t *payload_end = parsed_def.payload + parsed_def.payload_length;
  size_t signed_data_size = payload_end - bytes;
  sha256_Update(&context, bytes, signed_data_size);

  sha256_Final(&context, hash);

  const uint8_t *min, *max;
  for (uint8_t i = 0; i < parsed_def.proof_length; i++) {
    sha256_Init(&context);
    // node hash = sha256('\x01' + min(hash, next_proof) + max(hash,
    // next_proof))
    sha256_Update(&context, (uint8_t[]){1}, 1);
    if (memcmp(hash, parsed_def.proof[i], SHA256_DIGEST_LENGTH) <= 0) {
      min = hash;
      max = parsed_def.proof[i];
    } else {
      min = parsed_def.proof[i];
      max = hash;
    }
    sha256_Update(&context, min, SHA256_DIGEST_LENGTH);
    sha256_Update(&context, max, SHA256_DIGEST_LENGTH);
    sha256_Final(&context, hash);
  }

  // and verify its signature
  if (ed25519_sign_open(hash, SHA256_DIGEST_LENGTH, DEFINITIONS_PUBLIC_KEY,
                        *(parsed_def.signed_root_hash)) != 0
#if DEBUG_LINK
      &&
      ed25519_sign_open(hash, SHA256_DIGEST_LENGTH, DEFINITIONS_DEV_PUBLIC_KEY,
                        *(parsed_def.signed_root_hash)) != 0
#endif
  ) {
    // invalid signature
    error_str = _("Invalid definition signature");
    goto err;
  }

  // decode message
  const pb_msgdesc_t *fields = (expected_type == EthereumDefinitionType_NETWORK
                                    ? EthereumNetworkInfo_fields
                                    : EthereumTokenInfo_fields);
  pb_istream_t stream =
      pb_istream_from_buffer(parsed_def.payload, parsed_def.payload_length);
  bool status = pb_decode(&stream, fields, definition);
  if (status) {
    return true;
  }

  // fallthrough to error handling in case of decoding failure

err:
  memzero(&parsed_def, sizeof(parsed_def));
  fsm_sendFailure(FailureType_Failure_DataError, error_str);
  return false;
}

static const EthereumNetworkInfo *get_network(
    const EncodedNetwork *encoded_network, const uint64_t chain_id,
    const uint32_t slip44) {
  static EthereumNetworkInfo decoded_network;
  const EthereumNetworkInfo *network = &UNKNOWN_NETWORK;

  // try to get built-in definition
  if (chain_id != CHAIN_ID_UNKNOWN) {
    network = ethereum_get_network_by_chain_id(chain_id);
  } else if (slip44 != SLIP44_UNKNOWN) {
    network = ethereum_get_network_by_slip44(slip44);
  } else {
    // if both chain_id and slip44 is unspecified, we do not have anything to
    // match to the encoded definition, so just short-circuit here
    return &UNKNOWN_NETWORK;
  }
  // if we found built-in definition, or if there's no data to decode, we are
  // done
  if (!is_unknown_network(network) || encoded_network == NULL) {
    return network;
  }

  // if we still do not have any network definition try to decode received data
  memzero(&decoded_network, sizeof(decoded_network));
  if (!decode_definition(encoded_network->size, encoded_network->bytes,
                         EthereumDefinitionType_NETWORK, &decoded_network)) {
    // error already sent by decode_definition
    return NULL;
  }

  if (chain_id != CHAIN_ID_UNKNOWN && decoded_network.chain_id != chain_id) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Network definition mismatch"));
    return NULL;
  }
  if (slip44 != SLIP44_UNKNOWN && decoded_network.slip44 != slip44) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Network definition mismatch"));
    return NULL;
  }

  return &decoded_network;
}

static const EthereumTokenInfo *get_token(const EncodedToken *encoded_token,
                                          const uint64_t chain_id,
                                          const char *address) {
  static EthereumTokenInfo decoded_token;

  // if we do not know the chain_id, we cannot get the token
  if (chain_id == CHAIN_ID_UNKNOWN) {
    return &UNKNOWN_TOKEN;
  }

  // convert address string to bytes
  EthereumTokenInfo_address_t address_bytes;
  bool address_parsed = address && ethereum_parse(address, address_bytes.bytes);
  if (!address_parsed) {
    // without a valid address, we cannot get the token
    return &UNKNOWN_TOKEN;
  }

  // try to get built-in definition
  const EthereumTokenInfo *token =
      ethereum_token_by_address(chain_id, address_bytes.bytes);
  if (!is_unknown_token(token) || encoded_token == NULL) {
    // if we found one, or if there's no data to decode, we are done
    return token;
  }

  // try to decode received definition
  memzero(&decoded_token, sizeof(decoded_token));
  if (!decode_definition(encoded_token->size, encoded_token->bytes,
                         EthereumDefinitionType_TOKEN, &decoded_token)) {
    // error already sent by decode_definition
    return NULL;
  }

  if (decoded_token.chain_id != chain_id ||
      memcmp(decoded_token.address.bytes, address_bytes.bytes,
             sizeof(decoded_token.address.bytes))) {
    // receiving a mismatched token is not an error (we expect being able to get
    // multiple token definitions in the future, for multiple networks)
    // but we must not accept the mismatched definition
    memzero(&decoded_token, sizeof(decoded_token));
    return &UNKNOWN_TOKEN;
  }

  return &decoded_token;
}

const EthereumDefinitionsDecoded *ethereum_get_definitions(
    const EncodedNetwork *encoded_network, const EncodedToken *encoded_token,
    const uint64_t chain_id, const uint32_t slip44, const char *token_address) {
  static EthereumDefinitionsDecoded defs;
  memzero(&defs, sizeof(defs));

  const EthereumNetworkInfo *network =
      get_network(encoded_network, chain_id, slip44);
  if (network == NULL) {
    // error while decoding, failure was sent by get_network
    return NULL;
  }
  defs.network = network;

  if (!is_unknown_network(network) && token_address != NULL) {
    const EthereumTokenInfo *token =
        get_token(encoded_token, network->chain_id, token_address);
    if (token == NULL) {
      // error while decoding, failure was sent by get_token
      return NULL;
    }
    defs.token = token;
  } else {
    defs.token = &UNKNOWN_TOKEN;
  }

  return &defs;
}
