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


typedef struct {
  // prefix
  pb_size_t format_version_start;
  uint8_t definition_type;
  uint32_t data_version;
  uint16_t payload_length_in_bytes;

  // payload
  pb_size_t payload_start;

  // suffix
  uint8_t proof_length;
  pb_size_t proof_start;

  ed25519_signature signed_root_hash;
} ParsedEncodedEthereumDefinitions;

const ParsedEncodedEthereumDefinitions *_parse_encoded_EthereumDefinitions(
    const pb_size_t size, const pb_byte_t *bytes) {
  static ParsedEncodedEthereumDefinitions parsed;

  // format version + definition type + data version + payload length + payload
  // (at least 1B) + proof length + signed Merkle tree root hash
  if (size < (FORMAT_VERSION_LENGTH + 1 + 4 + 2 + 1 + 1 +
              MERKLE_TREE_SIGNED_ROOT_SIZE)) {
    return (const ParsedEncodedEthereumDefinitions *const)NULL;
  }

  pb_size_t current_position = 0;
  parsed.format_version_start = current_position;
  current_position += FORMAT_VERSION_LENGTH;

  parsed.definition_type = bytes[current_position];
  current_position += 1;

  parsed.data_version = read_be(&bytes[current_position]);
  current_position += 4;

  parsed.payload_length_in_bytes = (((uint16_t)bytes[current_position]) << 8) |
                                   (((uint16_t)bytes[current_position + 1]));
  current_position += 2;

  if (size < current_position - 1) {
    return (const ParsedEncodedEthereumDefinitions *const)NULL;
  }
  parsed.payload_start = current_position;
  current_position += parsed.payload_length_in_bytes;

  if (size < current_position - 1) {
    return (const ParsedEncodedEthereumDefinitions *const)NULL;
  }
  parsed.proof_length = bytes[current_position];
  current_position += 1;

  if (size < current_position - 1) {
    return (const ParsedEncodedEthereumDefinitions *const)NULL;
  }
  parsed.proof_start = current_position;
  current_position += parsed.proof_length * SHA256_DIGEST_LENGTH;

  if (size < current_position + MERKLE_TREE_SIGNED_ROOT_SIZE - 1) {
    return (const ParsedEncodedEthereumDefinitions *const)NULL;
  }
  memcpy(&parsed.signed_root_hash, &bytes[current_position],
         MERKLE_TREE_SIGNED_ROOT_SIZE);

  return (const ParsedEncodedEthereumDefinitions *const)&parsed;
}

bool _decode_definition(const pb_size_t size, const pb_byte_t *bytes,
                        const EthereumDefinitionType expected_type,
                        void *definition) {
  // parse received definition
  const ParsedEncodedEthereumDefinitions *parsed_def =
      _parse_encoded_EthereumDefinitions(size, bytes);
  if (!parsed_def) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid Ethereum definition"));
    return false;
  }

  // check definition fields
  if (memcmp(FORMAT_VERSION, &bytes[parsed_def->format_version_start],
             FORMAT_VERSION_LENGTH)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid definition format"));
    return false;
  }

  if (expected_type != parsed_def->definition_type) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Definition type mismatch"));
    return false;
  }

  if (MIN_DATA_VERSION > parsed_def->data_version) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Definition is outdated"));
    return false;
  }

  // compute Merkle tree root hash from proof
  uint8_t hash[SHA256_DIGEST_LENGTH] = {0};
  uint8_t hash_data[HASH_DATA_BUFFER_SIZE];
  memzero(hash_data, HASH_DATA_BUFFER_SIZE);
  // leaf hash = sha256('\x00' + leaf data)
  memcpy(&hash_data[1], bytes,
         parsed_def->payload_start + parsed_def->payload_length_in_bytes);
  sha256_Raw(
      hash_data,
      1 + parsed_def->payload_start + parsed_def->payload_length_in_bytes,
      hash);

  pb_size_t index = parsed_def->proof_start;
  int cmp = 0;
  const void *min, *max;
  for (uint8_t i = 0; i < parsed_def->proof_length; i++) {
    memzero(hash_data, HASH_DATA_BUFFER_SIZE);
    // node hash = sha256('\x01' + min(hash, next_proof) + max(hash,
    // next_proof))
    hash_data[0] = '\x01';
    cmp = memcmp(hash, &bytes[index], SHA256_DIGEST_LENGTH);
    min = cmp < 1 ? hash : &bytes[index];
    max = cmp > 0 ? hash : &bytes[index];
    memcpy(&hash_data[1], min, SHA256_DIGEST_LENGTH);
    memcpy(&hash_data[1 + SHA256_DIGEST_LENGTH], max, SHA256_DIGEST_LENGTH);
    sha256_Raw(hash_data, 1 + SHA256_DIGEST_LENGTH * 2, hash);
    index += SHA256_DIGEST_LENGTH;
  }

  // and verify its signature
  if (ed25519_sign_open(hash, SHA256_DIGEST_LENGTH, DEFINITIONS_PUBLIC_KEY,
                        parsed_def->signed_root_hash) != 0
#if DEBUG_LINK
      &&
      ed25519_sign_open(hash, SHA256_DIGEST_LENGTH, DEFINITIONS_DEV_PUBLIC_KEY,
                        parsed_def->signed_root_hash) != 0
#endif
  ) {
    // invalid signature
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid definition signature"));
    return false;
  }

  // decode message
  const pb_msgdesc_t *fields = (expected_type == EthereumDefinitionType_NETWORK
                                    ? EthereumNetworkInfo_fields
                                    : EthereumTokenInfo_fields);
  memzero(definition, sizeof(definition));
  pb_istream_t stream = pb_istream_from_buffer(
      &bytes[parsed_def->payload_start], parsed_def->payload_length_in_bytes);
  bool status = pb_decode(&stream, fields, definition);
  if (!status) {
    // invalid message
    fsm_sendFailure(FailureType_Failure_DataError, stream.errmsg);
    return false;
  }

  return true;
}

void _set_EthereumNetworkInfo_to_builtin(const uint64_t ref_chain_id,
                                         EthereumNetworkInfo *network) {
  network->chain_id = ref_chain_id;
  network->slip44 = ethereum_slip44_by_chain_id(ref_chain_id);
  memzero(network->shortcut, sizeof(network->shortcut));
  const char *sc = get_ethereum_suffix(ref_chain_id);
  strncpy(network->shortcut, sc, sizeof(network->shortcut) - 1);
  memzero(network->name, sizeof(network->name));
}

bool _get_EthereumNetworkInfo(
    const EthereumDefinitions_encoded_network_t *encoded_network,
    const uint64_t ref_chain_id, EthereumNetworkInfo *network) {
  // try to get built-in definition
  _set_EthereumNetworkInfo_to_builtin(ref_chain_id, network);

  // if we still do not have any network definition try to decode the received
  // one
  if (strncmp(network->shortcut, UNKNOWN_NETWORK_SHORTCUT,
              sizeof(network->shortcut)) == 0 &&
      encoded_network != NULL) {
    if (_decode_definition(encoded_network->size, encoded_network->bytes,
                           EthereumDefinitionType_NETWORK, (void *)network)) {
      if (ref_chain_id != CHAIN_ID_UNKNOWN &&
          network->chain_id != ref_chain_id) {
        // chain_id mismatch - error and reset definition
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Network definition mismatch"));
        _set_EthereumNetworkInfo_to_builtin(CHAIN_ID_UNKNOWN, network);
        return false;
      } else {
        // chain_id does match the reference one (if provided) so prepend one
        // space character to symbol, terminate it (encoded definitions does not
        // have space prefix) and return the decoded data
        memmove(&network->shortcut[1], &network->shortcut,
                sizeof(network->shortcut) - 2);
        network->shortcut[0] = ' ';
        network->shortcut[sizeof(network->shortcut) - 1] = 0;
      }
    } else {
      // decoding failed - reset network definition
      _set_EthereumNetworkInfo_to_builtin(CHAIN_ID_UNKNOWN, network);
    }
  }

  return true;
}

void _set_EthereumTokenInfo(const EthereumTokenInfo *ref_token, EthereumTokenInfo *token) {
  // reset
  memzero(token->symbol, sizeof(token->symbol));
  token->decimals = 0;
  memzero(token->address.bytes, sizeof(token->address.bytes));
  token->address.size = 0;
  token->chain_id = CHAIN_ID_UNKNOWN;
  memzero(token->name, sizeof(token->name));

  // copy data to token definition
  strncpy(token->symbol, ref_token->symbol, sizeof(token->symbol) - 1);
  token->decimals = ref_token->decimals;
  memcpy(token->address.bytes, ref_token->address.bytes,
         sizeof(token->address.bytes));
  token->address.size = sizeof(token->address.bytes);
  token->chain_id = ref_token->chain_id;
}

bool _get_EthereumTokenInfo(
    const EthereumDefinitions_encoded_token_t *encoded_token,
    const uint64_t ref_chain_id, const char *ref_address,
    EthereumTokenInfo *token) {
  EthereumTokenInfo_address_t ref_address_bytes;
  const EthereumTokenInfo *builtin = UnknownToken;

  // convert ref_address string to bytes
  bool address_parsed =
      ref_address && ethereum_parse(ref_address, ref_address_bytes.bytes);

  // try to get built-in definition
  if (address_parsed) {
    builtin = tokenByChainAddress(ref_chain_id, ref_address_bytes.bytes);
  }

  // if we do not have any token definition try to decode the received one
  if (builtin == UnknownToken && encoded_token != NULL) {
    if (_decode_definition(encoded_token->size, encoded_token->bytes,
                           EthereumDefinitionType_TOKEN, (void *)token)) {
      if ((ref_chain_id == CHAIN_ID_UNKNOWN ||
           token->chain_id == ref_chain_id) &&
          (!address_parsed ||
           !memcmp(token->address.bytes, ref_address_bytes.bytes,
                   sizeof(token->address.bytes)))) {
        // chain_id and/or address does match the reference ones (if provided)
        // so prepend one space character to symbol, terminate it (encoded
        // definitions does not have space prefix) and return the decoded data
        memmove(&token->symbol[1], &token->symbol, sizeof(token->symbol) - 2);
        token->symbol[0] = ' ';
        token->symbol[sizeof(token->symbol) - 1] = 0;
        return true;
      } else {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Token definition mismatch"));
      }
    }

    // decoding failed or token definition has different
    // chain_id and/or address
    _set_EthereumTokenInfo(UnknownToken, token);
    return false;
  }

  // copy result
  _set_EthereumTokenInfo(builtin, token);
  return true;
}

const EthereumDefinitionsDecoded *get_EthereumDefinitionsDecoded(
    const EthereumDefinitions_encoded_network_t *encoded_network,
    const EthereumDefinitions_encoded_token_t *encoded_token,
    const uint64_t ref_chain_id, const char *ref_address) {
  static EthereumDefinitionsDecoded defs;

  if (!_get_EthereumNetworkInfo(encoded_network, ref_chain_id, &defs.network)) {
    // error while decoding - chain IDs mismatch
    return NULL;
  }

  if (strncmp(defs.network.shortcut, UNKNOWN_NETWORK_SHORTCUT,
              sizeof(defs.network.shortcut)) != 0) {
    // we have found network definition, we can try to load token definition
    if (!_get_EthereumTokenInfo(encoded_token, ref_chain_id, ref_address,
                           &defs.token)) {
                            return NULL;
                           }
  } else {
    // if we did not find any network definition, set token definition to
    // unknown token
    _set_EthereumTokenInfo(UnknownToken, &defs.token);
  }
  return &defs;
}
