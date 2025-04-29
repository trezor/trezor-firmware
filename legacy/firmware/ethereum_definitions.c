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

#define SIGNATURE_THRESHOLD 2
#define DEFS_PUBLIC_KEYS_COUNT 3

const ed25519_public_key DEFS_PUBLIC_KEYS[DEFS_PUBLIC_KEYS_COUNT] = {
    "\x43\x34\x99\x63\x43\x62\x3e\x46\x2f\x0f\xc9\x33\x11\xfe\xf1\x48\x4c\xa2"
    "\x3d\x2f\xf1\xee\xc6\xdf\x1f\xa8\xeb\x7e\x35\x73\xb3\xdb",
    "\xa9\xa2\x2c\xc2\x65\xa0\xcb\x1d\x6c\xb3\x29\xbc\x0e\x60\xbc\x45\xdf\x76"
    "\xb9\xab\x28\xfb\x87\xb6\x11\x36\xfe\xaf\x8d\x8f\xdc\x96",
    "\xb8\xd2\xb2\x1d\xe2\x71\x24\xf0\x51\x1f\x90\x3a\xe7\xe6\x0e\x07\x96\x18"
    "\x10\xa0\xb8\xf2\x8e\xa7\x55\xfa\x50\x36\x7a\x8a\x2b\x8b",
};

#if DEBUG_LINK
const ed25519_public_key DEFS_PUBLIC_KEYS_DEV[DEFS_PUBLIC_KEYS_COUNT] = {
    "\x68\x46\x0e\xbe\xf3\xb1\x38\x16\x4e\xc7\xfd\x86\x10\xe9\x58\x00\xdf"
    "\x75\x98\xf7\x0f\x2f\x2e\xa7\xdb\x51\x72\xac\x74\xeb\xc1\x44",
    "\x8d\x4a\xbe\x07\x4f\xef\x92\x29\xd3\xb4\x41\xdf\xea\x4f\x98\xf8\x05"
    "\xb1\xa2\xb3\xa0\x6a\xe6\x45\x81\x0e\xfe\xce\x77\xfd\x50\x44",
    "\x97\xf7\x13\x5a\x9a\x26\x90\xe7\x3b\xeb\x26\x55\x6f\x1c\xb1\x63\xbe"
    "\xa2\x53\x2a\xff\xa1\xe7\x78\x24\x30\xbe\x98\xc0\xe5\x68\x12",
};
#endif

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

  uint8_t sigmask;
  const uint8_t *signature;
};

static bool parse_encoded_definition(struct EncodedDefinition *const result,
                                     const pb_size_t size,
                                     const pb_byte_t *bytes) {
  // format version + definition type + data version + payload length + payload
  // (at least 1B) + proof length + sigmask + signature
  if (size < (FORMAT_VERSION_LENGTH + 1 + 4 + 2 + 1 + 1 + 1 +
              sizeof(ed25519_signature))) {
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
                  1 + sizeof(ed25519_signature)) {
    return false;
  }
  result->proof = (proof_entry *)cursor;
  cursor += result->proof_length * sizeof(proof_entry);

  result->sigmask = *cursor;
  cursor += 1;
  result->signature = cursor;

  return true;
}

static bool decode_definition(const pb_size_t size, const pb_byte_t *bytes,
                              const DefinitionType expected_type,
                              void *definition) {
  // parse received definition
  static struct EncodedDefinition parsed_def;
  const char *error_str = _("Invalid definition");

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
  if (!cryptoCosiVerify(parsed_def.signature, hash, sizeof(hash),
                        SIGNATURE_THRESHOLD, DEFS_PUBLIC_KEYS,
                        DEFS_PUBLIC_KEYS_COUNT, parsed_def.sigmask)
#if DEBUG_LINK
      && !cryptoCosiVerify(parsed_def.signature, hash, sizeof(hash),
                           SIGNATURE_THRESHOLD, DEFS_PUBLIC_KEYS_DEV,
                           DEFS_PUBLIC_KEYS_COUNT, parsed_def.sigmask)
#endif
  ) {
    // invalid signature
    error_str = _("Invalid definition signature");
    goto err;
  }

  // decode message
  const pb_msgdesc_t *fields = (expected_type == DefinitionType_ETHEREUM_NETWORK
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
                         DefinitionType_ETHEREUM_NETWORK, &decoded_network)) {
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
                         DefinitionType_ETHEREUM_TOKEN, &decoded_token)) {
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
