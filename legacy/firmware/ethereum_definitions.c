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
typedef struct _ParsedEncodedEthereumDefinitions {
  // prefix
  pb_byte_t format_version[FORMAT_VERSION_LENGTH];
  uint8_t definition_type;
  uint32_t data_version;
  uint16_t payload_length;

  // payload
  const pb_byte_t *payload;

  // suffix
  uint8_t proof_length;
  const proof_entry* proof;

  const ed25519_signature* signed_root_hash;
} ParsedEncodedEthereumDefinitions;

bool _parse_encoded_EthereumDefinitions(
    ParsedEncodedEthereumDefinitions* const result, const pb_size_t size, const pb_byte_t *bytes) {
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

  result->data_version = read_be(cursor);
  cursor += 4;

  result->payload_length = (((uint16_t)*cursor << 8) |
                          ((uint16_t)*(cursor + 1)));
  cursor += 2;

  result->payload = cursor;
  cursor += result->payload_length;

  if (size < cursor - bytes) {
    return false;
  }
  result->proof_length = *cursor;
  cursor += 1;

  // check the whole size of incoming bytes array
  if (size != (cursor - bytes) + result->proof_length * sizeof(proof_entry) + MERKLE_TREE_SIGNED_ROOT_SIZE) {
    return false;
  }
  result->proof = (proof_entry*) cursor;
  cursor += result->proof_length * sizeof(proof_entry);

  result->signed_root_hash = (ed25519_signature*) cursor;

  return true;
}

bool _decode_definition(const pb_size_t size, const pb_byte_t *bytes,
                        const EthereumDefinitionType expected_type,
                        void *definition) {
  // parse received definition
  static ParsedEncodedEthereumDefinitions parsed_def;
  if (!_parse_encoded_EthereumDefinitions(&parsed_def, size, bytes)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid Ethereum definition"));
    return false;
  }

  // check definition fields
  if (memcmp(FORMAT_VERSION, parsed_def.format_version,
             FORMAT_VERSION_LENGTH)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid definition format"));
    return false;
  }

  if (expected_type != parsed_def.definition_type) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Definition type mismatch"));
    return false;
  }

  if (MIN_DATA_VERSION > parsed_def.data_version) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Definition is outdated"));
    return false;
  }

  // compute Merkle tree root hash from proof
  uint8_t hash[SHA256_DIGEST_LENGTH] = {0};
  uint8_t hash_prefix = '\x00';
  SHA256_CTX context = {0};
  sha256_Init(&context);
  // leaf hash = sha256('\x00' + leaf data)
  sha256_Update(&context, &hash_prefix, 1);
  sha256_Update(&context, bytes, (parsed_def.payload - bytes) + parsed_def.payload_length);
  sha256_Final(&context, hash);

  int cmp = 0;
  const void *min, *max;
  hash_prefix = '\x01';
  for (uint8_t i = 0; i < parsed_def.proof_length; i++) {
    sha256_Init(&context);
    // node hash = sha256('\x01' + min(hash, next_proof) + max(hash,
    // next_proof))
    sha256_Update(&context, &hash_prefix, 1);
    cmp = memcmp(hash, parsed_def.proof + i, SHA256_DIGEST_LENGTH);
    min = cmp < 1 ? hash : (void*) (parsed_def.proof + i);
    max = cmp > 0 ? hash : (void*) (parsed_def.proof + i);
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
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid definition signature"));
    return false;
  }

  // decode message
  const pb_msgdesc_t *fields = (expected_type == EthereumDefinitionType_NETWORK
                                    ? EthereumNetworkInfo_fields
                                    : EthereumTokenInfo_fields);
  pb_istream_t stream = pb_istream_from_buffer(
      parsed_def.payload, parsed_def.payload_length);
  bool status = pb_decode(&stream, fields, definition);
  if (!status) {
    // invalid message
    fsm_sendFailure(FailureType_Failure_DataError, stream.errmsg);
    return false;
  }

  return true;
}

void _set_EthereumNetworkInfo_to_builtin(const uint64_t ref_chain_id, const uint32_t ref_slip44,
                                         EthereumNetworkInfo *network) {
  if (ref_chain_id == CHAIN_ID_UNKNOWN) {
    // we don't know chain id so we can use only slip44
    network->slip44 = is_ethereum_slip44(ref_slip44) ? ref_slip44 : SLIP44_UNKNOWN;
  } else {
    network->slip44 = ethereum_slip44_by_chain_id(ref_chain_id);
  }
  network->chain_id = ref_chain_id;
  memzero(network->shortcut, sizeof(network->shortcut));
  const char *sc = get_ethereum_suffix(ref_chain_id);
  strncpy(network->shortcut, sc, sizeof(network->shortcut) - 1);
  memzero(network->name, sizeof(network->name));
}

bool _get_EthereumNetworkInfo(
    const EncodedNetwork *encoded_network,
    const uint64_t ref_chain_id, const uint32_t ref_slip44, EthereumNetworkInfo *network) {
  // try to get built-in definition
  _set_EthereumNetworkInfo_to_builtin(ref_chain_id, ref_slip44, network);

  // if we still do not have any network definition try to decode the received
  // one
  if (network->slip44 == SLIP44_UNKNOWN && encoded_network != NULL) {
    if (_decode_definition(encoded_network->size, encoded_network->bytes,
                           EthereumDefinitionType_NETWORK, network)) {
      if (ref_chain_id != CHAIN_ID_UNKNOWN &&
          network->chain_id != ref_chain_id) {
        // chain_id mismatch - error and reset definition
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Network definition mismatch"));
        return false;
      } else if (ref_slip44 != SLIP44_UNKNOWN && network->slip44 != ref_slip44) {
        // slip44 mismatch - reset network definition
        _set_EthereumNetworkInfo_to_builtin(CHAIN_ID_UNKNOWN, SLIP44_UNKNOWN, network);
      } else {
        // chain_id does match the reference one (if provided) so prepend one
        // space character to symbol, terminate it (encoded definitions does not
        // have space prefix) and return the decoded data
        memmove(network->shortcut + 1, network->shortcut,
                sizeof(network->shortcut) - 2);
        network->shortcut[0] = ' ';
        network->shortcut[sizeof(network->shortcut) - 1] = 0;
      }
    } else {
      // decoding failed - reset network definition
      _set_EthereumNetworkInfo_to_builtin(CHAIN_ID_UNKNOWN, SLIP44_UNKNOWN, network);
    }
  }

  return true;
}

bool _get_EthereumTokenInfo(
    const EncodedToken *encoded_token,
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
                           EthereumDefinitionType_TOKEN, token)) {
      if ((ref_chain_id == CHAIN_ID_UNKNOWN ||
           token->chain_id == ref_chain_id) &&
          (!address_parsed ||
           !memcmp(token->address.bytes, ref_address_bytes.bytes,
                   sizeof(token->address.bytes)))) {
        // chain_id and/or address does match the reference ones (if provided)
        // so prepend one space character to symbol, terminate it (encoded
        // definitions does not have space prefix) and return the decoded data
        memmove(token->symbol + 1, token->symbol, sizeof(token->symbol) - 2);
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
    return false;
  }

  // copy result
  *token = *builtin;
  return true;
}

const EthereumDefinitionsDecoded *get_EthereumDefinitionsDecoded(
    const EncodedNetwork *encoded_network,
    const EncodedToken *encoded_token,
    const uint64_t ref_chain_id, const uint32_t ref_slip44, const char *ref_address) {
  static EthereumDefinitionsDecoded defs;
  memzero(&defs, sizeof(defs));

  if (!_get_EthereumNetworkInfo(encoded_network, ref_chain_id, ref_slip44, &defs.network)) {
    // error while decoding - chain IDs mismatch
    return NULL;
  }

  if (defs.network.slip44 != SLIP44_UNKNOWN && defs.network.chain_id != CHAIN_ID_UNKNOWN) {
    // we have found network definition, we can try to load token definition
    if (!_get_EthereumTokenInfo(encoded_token, defs.network.chain_id, ref_address,
                                &defs.token)) {
      return NULL;
    }
  } else {
    // if we did not find any network definition, set token definition to
    // unknown token
    defs.token = *UnknownToken;
  }
  return &defs;
}
