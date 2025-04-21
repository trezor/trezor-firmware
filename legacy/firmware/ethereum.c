/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2016 Alex Beregszaszi <alex@rtfs.hu>
 * Copyright (C) 2016 Pavol Rusnak <stick@satoshilabs.com>
 * Copyright (C) 2016 Jochen Hoenicke <hoenicke@gmail.com>
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

#include "ethereum.h"
#include "address.h"
#include "crypto.h"
#include "ecdsa.h"
#include "ethereum_networks.h"
#include "ethereum_tokens.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "protect.h"
#include "secp256k1.h"
#include "sha3.h"
#include "transaction.h"
#include "util.h"

/* Maximum chain_id which returns the full signature_v (which must fit into an
uint32). chain_ids larger than this will only return one bit and the caller must
recalculate the full value: v = 2 * chain_id + 35 + v_bit */
#define MAX_CHAIN_ID ((0xFFFFFFFF - 36) >> 1)
#define EIP1559_TX_TYPE 2

#define PUBKEYHASH_LEN 20

static bool ethereum_signing = false;
static uint32_t data_total, data_left;
static EthereumTxRequest msg_tx_request;
static CONFIDENTIAL uint8_t privkey[32];
static uint64_t chain_id;
static const char *chain_suffix;
static bool eip1559;
struct SHA3_CTX keccak_ctx = {0};

static uint32_t signing_access_list_count;
static EthereumAccessList signing_access_list[8];
_Static_assert(sizeof(signing_access_list) ==
                   sizeof(((EthereumSignTxEIP1559 *)NULL)->access_list),
               "access_list buffer size mismatch");

struct signing_params {
  bool pubkeyhash_set;
  uint8_t pubkeyhash[PUBKEYHASH_LEN];
  uint64_t chain_id;
  const char *chain_suffix;

  uint32_t data_length;
  uint32_t data_initial_chunk_size;
  const uint8_t *data_initial_chunk_bytes;

  bool has_to;
  const char *to;

  const EthereumTokenInfo *token;

  uint32_t value_size;
  const uint8_t *value_bytes;
};

static inline void hash_data(const uint8_t *buf, size_t size) {
  sha3_Update(&keccak_ctx, buf, size);
}

/*
 * Push an RLP encoded length to the hash buffer.
 */
static void hash_rlp_length(uint32_t length, uint8_t firstbyte) {
  uint8_t buf[4] = {0};
  if (length == 1 && firstbyte <= 0x7f) {
    /* empty length header */
  } else if (length <= 55) {
    buf[0] = 0x80 + length;
    hash_data(buf, 1);
  } else if (length <= 0xff) {
    buf[0] = 0xb7 + 1;
    buf[1] = length;
    hash_data(buf, 2);
  } else if (length <= 0xffff) {
    buf[0] = 0xb7 + 2;
    buf[1] = length >> 8;
    buf[2] = length & 0xff;
    hash_data(buf, 3);
  } else {
    buf[0] = 0xb7 + 3;
    buf[1] = length >> 16;
    buf[2] = length >> 8;
    buf[3] = length & 0xff;
    hash_data(buf, 4);
  }
}

/*
 * Push an RLP encoded list length to the hash buffer.
 */
static void hash_rlp_list_length(uint32_t length) {
  uint8_t buf[4] = {0};
  if (length <= 55) {
    buf[0] = 0xc0 + length;
    hash_data(buf, 1);
  } else if (length <= 0xff) {
    buf[0] = 0xf7 + 1;
    buf[1] = length;
    hash_data(buf, 2);
  } else if (length <= 0xffff) {
    buf[0] = 0xf7 + 2;
    buf[1] = length >> 8;
    buf[2] = length & 0xff;
    hash_data(buf, 3);
  } else {
    buf[0] = 0xf7 + 3;
    buf[1] = length >> 16;
    buf[2] = length >> 8;
    buf[3] = length & 0xff;
    hash_data(buf, 4);
  }
}

/*
 * Push an RLP encoded length field and data to the hash buffer.
 */
static void hash_rlp_field(const uint8_t *buf, size_t size) {
  hash_rlp_length(size, buf[0]);
  hash_data(buf, size);
}

/*
 * Push an RLP encoded number to the hash buffer.
 * Ethereum yellow paper says to convert to big endian and strip leading zeros.
 */
static void hash_rlp_number(uint64_t number) {
  if (!number) {
    return;
  }
  uint8_t data[8] = {0};
  data[0] = (number >> 56) & 0xff;
  data[1] = (number >> 48) & 0xff;
  data[2] = (number >> 40) & 0xff;
  data[3] = (number >> 32) & 0xff;
  data[4] = (number >> 24) & 0xff;
  data[5] = (number >> 16) & 0xff;
  data[6] = (number >> 8) & 0xff;
  data[7] = (number) & 0xff;
  int offset = 0;
  while (!data[offset]) {
    offset++;
  }
  hash_rlp_field(data + offset, 8 - offset);
}

/*
 * Calculate the number of bytes needed for an RLP length header.
 * NOTE: supports up to 16MB of data (how unlikely...)
 * FIXME: improve
 */
static int rlp_calculate_length(int length, uint8_t firstbyte) {
  if (length == 1 && firstbyte <= 0x7f) {
    return 1;
  } else if (length <= 55) {
    return 1 + length;
  } else if (length <= 0xff) {
    return 2 + length;
  } else if (length <= 0xffff) {
    return 3 + length;
  } else {
    return 4 + length;
  }
}

/* If number is less than 0x80 the RLP encoding is iteself (1 byte).
 * If it is 0x80 or larger, RLP encoding is 1 + length in bytes.
 */
static int rlp_calculate_number_length(uint64_t number) {
  int length = 1;
  if (number >= 0x80) {
    while (number) {
      length++;
      number = number >> 8;
    }
  }
  return length;
}

static uint32_t rlp_calculate_access_list_keys_length(
    const EthereumAccessList_storage_keys_t *keys, uint32_t keys_count) {
  uint32_t keys_length = 0;
  for (size_t i = 0; i < keys_count; i++) {
    keys_length += rlp_calculate_length(keys[i].size, keys[i].bytes[0]);
  }
  return keys_length;
}

static uint32_t rlp_calculate_access_list_length(
    const EthereumAccessList access_list[8], uint32_t access_list_count) {
  uint32_t length = 0;
  for (size_t i = 0; i < access_list_count; i++) {
    uint32_t address_length = rlp_calculate_length(PUBKEYHASH_LEN, 0xff);
    uint32_t keys_length = rlp_calculate_access_list_keys_length(
        access_list[i].storage_keys, access_list[i].storage_keys_count);
    length += rlp_calculate_length(
        address_length + rlp_calculate_length(keys_length, 0xff), 0xff);
  }

  return length;
}

static void send_request_chunk(void) {
  int progress = 1000 - (data_total > 1000000 ? data_left / (data_total / 800)
                                              : data_left * 800 / data_total);
  layoutProgress(_("Signing"), progress);
  msg_tx_request.has_data_length = true;
  msg_tx_request.data_length = data_left <= 1024 ? data_left : 1024;
  msg_write(MessageType_MessageType_EthereumTxRequest, &msg_tx_request);
}

static int ethereum_is_canonic(uint8_t v, uint8_t signature[64]) {
  (void)signature;
  return (v & 2) == 0;
}

static void send_signature(void) {
  uint8_t hash[32] = {0}, sig[64] = {0};
  uint8_t v = 0;
  layoutProgress(_("Signing"), 1000);

  if (eip1559) {
    hash_rlp_list_length(rlp_calculate_access_list_length(
        signing_access_list, signing_access_list_count));
    for (size_t i = 0; i < signing_access_list_count; i++) {
      uint8_t address[PUBKEYHASH_LEN] = {0};
      if (!ethereum_parse(signing_access_list[i].address, address)) {
        fsm_sendFailure(FailureType_Failure_DataError, _("Malformed address"));
        ethereum_signing_abort();
        return;
      }

      uint32_t address_length =
          rlp_calculate_length(sizeof(address), address[0]);
      uint32_t keys_length = rlp_calculate_access_list_keys_length(
          signing_access_list[i].storage_keys,
          signing_access_list[i].storage_keys_count);

      hash_rlp_list_length(address_length +
                           rlp_calculate_length(keys_length, 0xff));
      hash_rlp_field(address, sizeof(address));
      hash_rlp_list_length(keys_length);
      for (size_t j = 0; j < signing_access_list[i].storage_keys_count; j++) {
        hash_rlp_field(signing_access_list[i].storage_keys[j].bytes,
                       signing_access_list[i].storage_keys[j].size);
      }
    }
  } else {
    /* eip-155 replay protection */
    /* hash v=chain_id, r=0, s=0 */
    hash_rlp_number(chain_id);
    hash_rlp_length(0, 0);
    hash_rlp_length(0, 0);
  }

  keccak_Final(&keccak_ctx, hash);
  if (ecdsa_sign_digest(&secp256k1, privkey, hash, sig, &v,
                        ethereum_is_canonic) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    ethereum_signing_abort();
    return;
  }

  memzero(privkey, sizeof(privkey));

  /* Send back the result */
  msg_tx_request.has_data_length = false;

  msg_tx_request.has_signature_v = true;
  if (eip1559 || chain_id > MAX_CHAIN_ID) {
    msg_tx_request.signature_v = v;
  } else {
    msg_tx_request.signature_v = v + 2 * chain_id + 35;
  }

  msg_tx_request.has_signature_r = true;
  msg_tx_request.signature_r.size = 32;
  memcpy(msg_tx_request.signature_r.bytes, sig, 32);

  msg_tx_request.has_signature_s = true;
  msg_tx_request.signature_s.size = 32;
  memcpy(msg_tx_request.signature_s.bytes, sig + 32, 32);

  msg_write(MessageType_MessageType_EthereumTxRequest, &msg_tx_request);

  ethereum_signing_abort();
}
/* Format a 256 bit number (amount in wei) into a human readable format
 * using standard ethereum units.
 * The buffer must be at least 25 bytes.
 */
static void ethereumFormatAmount(const bignum256 *amnt,
                                 const EthereumTokenInfo *token, char *buf,
                                 int buflen, bool use_gwei) {
  bignum256 bn1e9 = {0};
  bn_read_uint32(1000000000, &bn1e9);

  bignum256 bn1e3 = {0};
  bn_read_uint32(1000, &bn1e3);

  char suffix[50] = {' ', 0};
  int decimals = 18;
  if (token) {
    strlcpy(suffix + 1, token->symbol, sizeof(suffix) - 1);
    decimals = token->decimals;
  } else if (bn_is_less(amnt, &bn1e9)) {
    if (use_gwei && !bn_is_less(amnt, &bn1e3)) {
      strlcpy(suffix + 1, "Gwei", sizeof(suffix) - 1);
      decimals = 9;
    } else {
      strlcpy(suffix + 1, "Wei", sizeof(suffix) - 1);
      decimals = 0;
    }
  } else {
    strlcpy(suffix + 1, chain_suffix, sizeof(suffix) - 1);
  }
  bn_format(amnt, NULL, suffix, decimals, 0, false, ',', buf, buflen);
}

static void parse_bignum256(const uint8_t *value, uint32_t value_len,
                            bignum256 *result) {
  uint8_t padded[32] = {0};
  memcpy(padded + (32 - value_len), value, value_len);
  bn_read_be(padded, result);
}

static void layoutEthereumConfirmTx(const uint8_t *to, uint32_t to_len,
                                    const uint8_t *value, uint32_t value_len,
                                    const EthereumTokenInfo *token) {
  bignum256 val = {0};
  parse_bignum256(value, value_len, &val);

  char amount[64] = {0};
  if (token == NULL) {
    if (bn_is_zero(&val)) {
      strcpy(amount, _("message"));
    } else {
      ethereumFormatAmount(&val, NULL, amount, sizeof(amount),
                           /*use_gwei=*/false);
    }
  } else {
    ethereumFormatAmount(&val, token, amount, sizeof(amount),
                         /*use_gwei=*/false);
  }

  char _to1[] = "to ____________";
  char _to2[] = "_______________";
  char _to3[] = "_______________?";

  if (to_len) {
    char to_str[43] = {0};

    bool rskip60 = false;
    // constants from trezor-common/defs/ethereum/networks.json
    switch (chain_id) {
      case 30:
        rskip60 = true;
        break;
      case 31:
        rskip60 = true;
        break;
    }

    ethereum_address_checksum(to, to_str, rskip60, chain_id);
    memcpy(_to1 + 3, to_str, 12);
    memcpy(_to2, to_str + 12, 15);
    memcpy(_to3, to_str + 27, 15);
  } else {
    strlcpy(_to1, _("to new contract?"), sizeof(_to1));
    strlcpy(_to2, "", sizeof(_to2));
    strlcpy(_to3, "", sizeof(_to3));
  }

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Send"), amount, _to1, _to2, _to3, NULL);
}

static void layoutEthereumData(const uint8_t *data, uint32_t len,
                               uint32_t total_len) {
  char hexdata[3][17] = {0};
  char summary[20] = {0};
  uint32_t printed = 0;
  for (int i = 0; i < 3; i++) {
    uint32_t linelen = len - printed;
    if (linelen > 8) {
      linelen = 8;
    }
    data2hex(data, linelen, hexdata[i]);
    data += linelen;
    printed += linelen;
  }

  strcpy(summary, "...          bytes");
  char *p = summary + 11;
  uint32_t number = total_len;
  while (number > 0) {
    *p-- = '0' + number % 10;
    number = number / 10;
  }
  char *summarystart = summary;
  if (total_len == printed) summarystart = summary + 4;

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Transaction data:"), hexdata[0], hexdata[1], hexdata[2],
                    summarystart, NULL);
}

static void layoutEthereumFee(const uint8_t *value, uint32_t value_len,
                              const uint8_t *gas_price, uint32_t gas_price_len,
                              const uint8_t *gas_limit, uint32_t gas_limit_len,
                              bool is_token) {
  bignum256 val = {0}, gas = {0};
  char tx_value[32] = {0};
  char gas_value[32] = {0};

  memzero(tx_value, sizeof(tx_value));
  memzero(gas_value, sizeof(gas_value));

  parse_bignum256(gas_price, gas_price_len, &val);
  parse_bignum256(gas_limit, gas_limit_len, &gas);
  bn_multiply(&val, &gas, &secp256k1.prime);

  ethereumFormatAmount(&gas, NULL, gas_value, sizeof(gas_value),
                       /*use_gwei=*/true);

  parse_bignum256(value, value_len, &val);

  if (bn_is_zero(&val)) {
    strcpy(tx_value, is_token ? _("token") : _("message"));
  } else {
    ethereumFormatAmount(&val, NULL, tx_value, sizeof(tx_value),
                         /*use_gwei=*/false);
  }

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Really send"), tx_value, _("paying up to"), gas_value,
                    _("for gas?"), NULL);
}

static void layoutEthereumFeeEIP1559(const char *description,
                                     const uint8_t *amount_bytes,
                                     uint32_t amount_len,
                                     const uint8_t *multiplier_bytes,
                                     uint32_t multiplier_len) {
  bignum256 amount_val = {0};
  char amount_str[32] = {0};

  parse_bignum256(amount_bytes, amount_len, &amount_val);

  if (multiplier_len > 0) {
    bignum256 multiplier_val = {0};

    parse_bignum256(multiplier_bytes, multiplier_len, &multiplier_val);
    bn_multiply(&multiplier_val, &amount_val, &secp256k1.prime);
  }

  ethereumFormatAmount(&amount_val, NULL, amount_str, sizeof(amount_str),
                       /*use_gwei=*/true);

  layoutDialogSwipeWrapping(&bmp_icon_question, _("Cancel"), _("Confirm"),
                            _("Confirm fee"), description, amount_str);
}

/*
 * RLP fields:
 * - nonce (0 .. 32)
 * - gas_price (0 .. 32)
 * - gas_limit (0 .. 32)
 * - to (0, 20)
 * - value (0 .. 32)
 * - data (0 ..)
 */

static bool ethereum_signing_init_common(struct signing_params *params) {
  ethereum_signing = true;
  sha3_256_Init(&keccak_ctx);

  data_total = data_left = 0;
  chain_id = 0;

  memzero(&msg_tx_request, sizeof(EthereumTxRequest));
  memzero(signing_access_list, sizeof(signing_access_list));
  signing_access_list_count = 0;

  /* eip-155 chain id */
  if (params->chain_id < 1) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Chain ID out of bounds"));
    return false;
  }
  chain_id = params->chain_id;
  chain_suffix = params->chain_suffix;

  if (params->data_length > 0) {
    if (params->data_initial_chunk_size == 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Data length provided, but no initial chunk"));
      return false;
    }
    /* Our encoding only supports transactions up to 2^24 bytes.  To
     * prevent exceeding the limit we use a stricter limit on data length.
     */
    if (params->data_length > 16000000) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Data length exceeds limit"));
      return false;
    }
    data_total = params->data_length;
  } else {
    data_total = 0;
  }
  if (params->data_initial_chunk_size > data_total) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid size of initial chunk"));
    return false;
  }

  // safety checks

  size_t tolen = params->has_to ? strlen(params->to) : 0;
  /* Address has wrong length */
  bool wrong_length = (tolen != 42 && tolen != 40 && tolen != 0);

  // sending transaction to address 0 (contract creation) without a data field
  bool contract_without_data = (tolen == 0 && params->data_length == 0);

  if (wrong_length || contract_without_data) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Safety check failed"));
    return false;
  }

  return true;
}

static void ethereum_signing_handle_erc20(struct signing_params *params,
                                          const EthereumTokenInfo *token) {
  if (params->has_to && ethereum_parse(params->to, params->pubkeyhash)) {
    params->pubkeyhash_set = true;
  } else {
    params->pubkeyhash_set = false;
    memzero(params->pubkeyhash, sizeof(params->pubkeyhash));
  }

  // detect ERC-20 token
  if (params->pubkeyhash_set && params->value_size == 0 && data_total == 68 &&
      params->data_initial_chunk_size == 68 &&
      memcmp(params->data_initial_chunk_bytes,
             "\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
             16) == 0) {
    params->token = token;
  }
}

// smart contract 'data' field lengths in bytes
static const size_t SC_FUNC_SIG_BYTES = 4;
static const size_t SC_ARGUMENT_BYTES = 32;

// staking operations function signatures
static const uint8_t SC_FUNC_SIG_STAKE[] = {0x3a, 0x29, 0xdb, 0xae};
static const uint8_t SC_FUNC_SIG_UNSTAKE[] = {0x76, 0xec, 0x87, 0x1c};
static const uint8_t SC_FUNC_SIG_CLAIM[] = {0x33, 0x98, 0x6f, 0xfa};

// addresses for pool (stake/unstake) and accounting (claim) operations
static const uint8_t POOL_HOLESKY_TESTNET[] = {
    0xaf, 0xa8, 0x48, 0x35, 0x71, 0x54, 0xa6, 0xa6, 0x24, 0x68,
    0x6b, 0x34, 0x83, 0x3,  0xef, 0x9a, 0x13, 0xf6, 0x32, 0x64};
static const uint8_t POOL_MAINNET[] = {0xd5, 0x23, 0x79, 0x4c, 0x87, 0x9d, 0x9e,
                                       0xc0, 0x28, 0x96, 0xa,  0x23, 0x1f, 0x86,
                                       0x67, 0x58, 0xe4, 0x5,  0xbe, 0x34};
static const uint8_t ACCOUNTING_HOLESKY_TESTNET[] = {
    0x62, 0x40, 0x87, 0xdd, 0x19, 0x4,  0xab, 0x12, 0x2a, 0x32,
    0x87, 0x8c, 0xe9, 0xe9, 0x33, 0xc7, 0x7,  0x1f, 0x53, 0xb9};
static const uint8_t ACCOUNTING_MAINNET[] = {
    0x7a, 0x7f, 0xb,  0x3c, 0x23, 0xc2, 0x3a, 0x31, 0xcf, 0xcb,
    0xc,  0x44, 0x70, 0x9b, 0xe7, 0xd,  0x4d, 0x54, 0x5c, 0x6e};

enum staking_operation_t {
  ETH_STAKING_STAKE,
  ETH_STAKING_UNSTAKE,
  ETH_STAKING_CLAIM,
};

// Returns `true` if it is a staking-related transaction and updates `op` with
// its specific operation.
static bool isEthereumStakingTx(const struct signing_params *params,
                                enum staking_operation_t *op) {
  if (params->data_initial_chunk_size < SC_FUNC_SIG_BYTES) {
    return false;
  }
  const uint8_t *pubkeyhash = params->pubkeyhash;
  const uint8_t *data_chunk = params->data_initial_chunk_bytes;
  bool is_address_pool =
      ((memcmp(pubkeyhash, POOL_HOLESKY_TESTNET, PUBKEYHASH_LEN) == 0) ||
       (memcmp(pubkeyhash, POOL_MAINNET, PUBKEYHASH_LEN) == 0));
  if (is_address_pool) {
    if (memcmp(data_chunk, SC_FUNC_SIG_STAKE, SC_FUNC_SIG_BYTES) == 0) {
      *op = ETH_STAKING_STAKE;
      return true;
    }
    if (memcmp(data_chunk, SC_FUNC_SIG_UNSTAKE, SC_FUNC_SIG_BYTES) == 0) {
      *op = ETH_STAKING_UNSTAKE;
      return true;
    }
  }
  bool is_address_accounting =
      ((memcmp(pubkeyhash, ACCOUNTING_HOLESKY_TESTNET, PUBKEYHASH_LEN) == 0) ||
       (memcmp(pubkeyhash, ACCOUNTING_MAINNET, PUBKEYHASH_LEN) == 0));
  if (is_address_accounting) {
    if (memcmp(data_chunk, SC_FUNC_SIG_CLAIM, SC_FUNC_SIG_BYTES) == 0) {
      *op = ETH_STAKING_CLAIM;
      return true;
    }
  }
  return false;
}

static bool layoutEthereumConfirmStakingTx(const struct signing_params *params,
                                           enum staking_operation_t op) {
  uint32_t args_size = params->data_initial_chunk_size - SC_FUNC_SIG_BYTES;
  const uint8_t *args_bytes =
      params->data_initial_chunk_bytes + SC_FUNC_SIG_BYTES;

  bignum256 value = {0}, source = {0};
  char value_str[64] = {0};
  const char *_line1 = NULL;
  const char *_line2 = NULL;
  const char *_line3 = NULL;
  switch (op) {
    case ETH_STAKING_STAKE:
      // stake args:
      // - arg0: uint64, source (should be 1)
      if (args_size != SC_ARGUMENT_BYTES) {
        return false;
      }
      bn_read_be(args_bytes, &source);
      if (!bn_is_one(&source)) {
        return false;
      }
      parse_bignum256(params->value_bytes, params->value_size, &value);
      ethereumFormatAmount(&value, NULL, value_str, sizeof(value_str),
                           /*use_gwei=*/false);
      _line1 = _("Stake");
      _line2 = value_str;
      _line3 = _("on Everstake?");
      break;
    case ETH_STAKING_UNSTAKE:
      // unstake args:
      // - arg0: uint256, value
      // - arg1: uint16, isAllowedInterchange (bool) - skipped
      // - arg2: uint64, source, should be 1
      if (args_size != 3 * SC_ARGUMENT_BYTES) {
        return false;
      }
      bn_read_be(args_bytes + 2 * SC_ARGUMENT_BYTES, &source);
      if (!bn_is_one(&source)) {
        return false;
      }
      bn_read_be(args_bytes, &value);
      ethereumFormatAmount(&value, NULL, value_str, sizeof(value_str),
                           /*use_gwei=*/false);
      _line1 = _("Unstake");
      _line2 = value_str;
      _line3 = _("from Everstake?");
      break;
    case ETH_STAKING_CLAIM:
      // claim has no args
      if (args_size != 0) {
        return false;
      }
      _line1 = _("Claim ETH");
      _line2 = _("from Everstake?");
      break;
  }
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _line1,
                    _line2, _line3, NULL, NULL, NULL);
  return true;
}

static bool ethereum_signing_confirm_common(
    const struct signing_params *params) {
  enum staking_operation_t staking_op;
  if (isEthereumStakingTx(params, &staking_op)) {
    if (!layoutEthereumConfirmStakingTx(params, staking_op)) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Invalid staking transaction call"));
      return false;
    }
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      return false;
    }
    // in case of staking, skip common ETH confirmation layout
    return true;
  }

  if (params->token != NULL) {
    layoutEthereumConfirmTx(
        params->data_initial_chunk_bytes + 16, PUBKEYHASH_LEN,
        params->data_initial_chunk_bytes + 16 + PUBKEYHASH_LEN, 32,
        params->token);
  } else {
    layoutEthereumConfirmTx(params->pubkeyhash, PUBKEYHASH_LEN,
                            params->value_bytes, params->value_size, NULL);
  }

  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    return false;
  }

  if (params->token == NULL && data_total > 0) {
    layoutEthereumData(params->data_initial_chunk_bytes,
                       params->data_initial_chunk_size, data_total);
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      return false;
    }
  }

  return true;
}

void ethereum_signing_init(const EthereumSignTx *msg, const HDNode *node,
                           const EthereumDefinitionsDecoded *defs) {
  struct signing_params params = {
      .chain_id = msg->chain_id,
      .chain_suffix = defs->network->symbol,
      .data_length = msg->data_length,
      .data_initial_chunk_size = msg->data_initial_chunk.size,
      .data_initial_chunk_bytes = msg->data_initial_chunk.bytes,

      .has_to = msg->has_to,
      .to = msg->to,

      .value_size = msg->value.size,
      .value_bytes = msg->value.bytes,
  };

  eip1559 = false;
  if (!ethereum_signing_init_common(&params)) {
    ethereum_signing_abort();
    return;
  }

  // sanity check that fee doesn't overflow
  if (msg->gas_price.size + msg->gas_limit.size > 30) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Safety check failed"));
    ethereum_signing_abort();
    return;
  }

  uint32_t tx_type = 0;
  /* Wanchain txtype */
  if (msg->has_tx_type) {
    if (msg->tx_type == 1 || msg->tx_type == 6) {
      tx_type = msg->tx_type;
    } else {
      fsm_sendFailure(FailureType_Failure_DataError, _("Txtype out of bounds"));
      ethereum_signing_abort();
      return;
    }
  }

  ethereum_signing_handle_erc20(&params, defs->token);

  if (!ethereum_signing_confirm_common(&params)) {
    ethereum_signing_abort();
    return;
  }

  layoutEthereumFee(msg->value.bytes, msg->value.size, msg->gas_price.bytes,
                    msg->gas_price.size, msg->gas_limit.bytes,
                    msg->gas_limit.size, params.token != NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    ethereum_signing_abort();
    return;
  }

  /* Stage 1: Calculate total RLP length */
  uint32_t rlp_length = 0;

  layoutProgress(_("Signing"), 0);

  rlp_length += rlp_calculate_length(msg->nonce.size, msg->nonce.bytes[0]);
  rlp_length +=
      rlp_calculate_length(msg->gas_price.size, msg->gas_price.bytes[0]);
  rlp_length +=
      rlp_calculate_length(msg->gas_limit.size, msg->gas_limit.bytes[0]);
  rlp_length += rlp_calculate_length(params.pubkeyhash_set ? PUBKEYHASH_LEN : 0,
                                     params.pubkeyhash[0]);
  rlp_length += rlp_calculate_length(params.value_size, params.value_bytes[0]);
  rlp_length +=
      rlp_calculate_length(data_total, params.data_initial_chunk_bytes[0]);
  if (tx_type) {
    rlp_length += rlp_calculate_number_length(tx_type);
  }
  rlp_length += rlp_calculate_number_length(chain_id);
  rlp_length += rlp_calculate_length(0, 0);
  rlp_length += rlp_calculate_length(0, 0);

  /* Stage 2: Store header fields */
  hash_rlp_list_length(rlp_length);

  layoutProgress(_("Signing"), 100);

  if (tx_type) {
    hash_rlp_number(tx_type);
  }
  hash_rlp_field(msg->nonce.bytes, msg->nonce.size);
  hash_rlp_field(msg->gas_price.bytes, msg->gas_price.size);
  hash_rlp_field(msg->gas_limit.bytes, msg->gas_limit.size);
  hash_rlp_field(params.pubkeyhash, params.pubkeyhash_set ? PUBKEYHASH_LEN : 0);
  hash_rlp_field(params.value_bytes, params.value_size);
  hash_rlp_length(data_total, params.data_initial_chunk_bytes[0]);
  hash_data(params.data_initial_chunk_bytes, params.data_initial_chunk_size);
  data_left = data_total - params.data_initial_chunk_size;

  memcpy(privkey, node->private_key, 32);

  if (data_left > 0) {
    send_request_chunk();
  } else {
    send_signature();
  }
}

void ethereum_signing_init_eip1559(const EthereumSignTxEIP1559 *msg,
                                   const HDNode *node,
                                   const EthereumDefinitionsDecoded *defs) {
  struct signing_params params = {
      .chain_id = msg->chain_id,
      .chain_suffix = defs->network->symbol,

      .data_length = msg->data_length,
      .data_initial_chunk_size = msg->data_initial_chunk.size,
      .data_initial_chunk_bytes = msg->data_initial_chunk.bytes,

      .has_to = msg->has_to,
      .to = msg->to,

      .value_size = msg->value.size,
      .value_bytes = msg->value.bytes,
  };

  eip1559 = true;
  if (!ethereum_signing_init_common(&params)) {
    ethereum_signing_abort();
    return;
  }

  // sanity check that fee doesn't overflow
  if (msg->max_gas_fee.size + msg->gas_limit.size > 30 ||
      msg->max_priority_fee.size + msg->gas_limit.size > 30) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Safety check failed"));
    ethereum_signing_abort();
    return;
  }

  ethereum_signing_handle_erc20(&params, defs->token);

  if (!ethereum_signing_confirm_common(&params)) {
    ethereum_signing_abort();
    return;
  }

  layoutEthereumFeeEIP1559(_("Maximum fee per gas"), msg->max_gas_fee.bytes,
                           msg->max_gas_fee.size, NULL, 0);
  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    ethereum_signing_abort();
    return;
  }

  layoutEthereumFeeEIP1559(_("Priority fee per gas"),
                           msg->max_priority_fee.bytes,
                           msg->max_priority_fee.size, NULL, 0);
  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    ethereum_signing_abort();
    return;
  }

  layoutEthereumFeeEIP1559(_("Maximum fee"), msg->gas_limit.bytes,
                           msg->gas_limit.size, msg->max_gas_fee.bytes,
                           msg->max_gas_fee.size);
  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    ethereum_signing_abort();
    return;
  }

  /* Stage 1: Calculate total RLP length */
  uint32_t rlp_length = 0;

  layoutProgress(_("Signing"), 0);

  rlp_length += rlp_calculate_number_length(chain_id);
  rlp_length += rlp_calculate_length(msg->nonce.size, msg->nonce.bytes[0]);
  rlp_length += rlp_calculate_length(msg->max_priority_fee.size,
                                     msg->max_priority_fee.bytes[0]);
  rlp_length +=
      rlp_calculate_length(msg->max_gas_fee.size, msg->max_gas_fee.bytes[0]);
  rlp_length +=
      rlp_calculate_length(msg->gas_limit.size, msg->gas_limit.bytes[0]);
  rlp_length += rlp_calculate_length(params.pubkeyhash_set ? PUBKEYHASH_LEN : 0,
                                     params.pubkeyhash[0]);
  rlp_length += rlp_calculate_length(params.value_size, params.value_bytes[0]);
  rlp_length +=
      rlp_calculate_length(data_total, params.data_initial_chunk_bytes[0]);

  rlp_length +=
      rlp_calculate_length(rlp_calculate_access_list_length(
                               msg->access_list, msg->access_list_count),
                           0xff);

  /* Stage 2: Store header fields */
  hash_rlp_number(EIP1559_TX_TYPE);
  hash_rlp_list_length(rlp_length);

  layoutProgress(_("Signing"), 100);

  hash_rlp_number(chain_id);
  hash_rlp_field(msg->nonce.bytes, msg->nonce.size);
  hash_rlp_field(msg->max_priority_fee.bytes, msg->max_priority_fee.size);
  hash_rlp_field(msg->max_gas_fee.bytes, msg->max_gas_fee.size);
  hash_rlp_field(msg->gas_limit.bytes, msg->gas_limit.size);
  hash_rlp_field(params.pubkeyhash, params.pubkeyhash_set ? PUBKEYHASH_LEN : 0);
  hash_rlp_field(params.value_bytes, params.value_size);
  hash_rlp_length(data_total, params.data_initial_chunk_bytes[0]);
  hash_data(params.data_initial_chunk_bytes, params.data_initial_chunk_size);
  data_left = data_total - params.data_initial_chunk_size;

  /* make a copy of access_list, hash it after data is processed */
  memcpy(signing_access_list, msg->access_list, sizeof(signing_access_list));
  signing_access_list_count = msg->access_list_count;

  memcpy(privkey, node->private_key, 32);

  if (data_left > 0) {
    send_request_chunk();
  } else {
    send_signature();
  }
}

void ethereum_signing_txack(const EthereumTxAck *tx) {
  if (!ethereum_signing) {
    fsm_sendFailure(FailureType_Failure_UnexpectedMessage,
                    _("Not in Ethereum signing mode"));
    layoutHome();
    return;
  }

  if (tx->data_chunk.size > data_left) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Too much data"));
    ethereum_signing_abort();
    return;
  }

  if (data_left > 0 && tx->data_chunk.size == 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Empty data chunk received"));
    ethereum_signing_abort();
    return;
  }

  hash_data(tx->data_chunk.bytes, tx->data_chunk.size);

  data_left -= tx->data_chunk.size;

  if (data_left > 0) {
    send_request_chunk();
  } else {
    send_signature();
  }
}

void ethereum_signing_abort(void) {
  if (ethereum_signing) {
    memzero(privkey, sizeof(privkey));
    layoutHome();
    ethereum_signing = false;
  }
}

static void ethereum_message_hash(const uint8_t *message, size_t message_len,
                                  uint8_t hash[32]) {
  struct SHA3_CTX ctx = {0};
  sha3_256_Init(&ctx);
  sha3_Update(&ctx, (const uint8_t *)"\x19" "Ethereum Signed Message:\n", 26);
  uint8_t c = 0;
  if (message_len >= 1000000000) {
    c = '0' + message_len / 1000000000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 100000000) {
    c = '0' + message_len / 100000000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 10000000) {
    c = '0' + message_len / 10000000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 1000000) {
    c = '0' + message_len / 1000000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 100000) {
    c = '0' + message_len / 100000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 10000) {
    c = '0' + message_len / 10000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 1000) {
    c = '0' + message_len / 1000 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 100) {
    c = '0' + message_len / 100 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  if (message_len >= 10) {
    c = '0' + message_len / 10 % 10;
    sha3_Update(&ctx, &c, 1);
  }
  c = '0' + message_len % 10;
  sha3_Update(&ctx, &c, 1);
  sha3_Update(&ctx, message, message_len);
  keccak_Final(&ctx, hash);
}

void ethereum_message_sign(const EthereumSignMessage *msg, const HDNode *node,
                           EthereumMessageSignature *resp) {
  uint8_t hash[32] = {0};
  ethereum_message_hash(msg->message.bytes, msg->message.size, hash);

  uint8_t v = 0;
  if (ecdsa_sign_digest(&secp256k1, node->private_key, hash,
                        resp->signature.bytes, &v, ethereum_is_canonic) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    return;
  }

  resp->signature.bytes[64] = 27 + v;
  resp->signature.size = 65;
  msg_write(MessageType_MessageType_EthereumMessageSignature, resp);
}

int ethereum_message_verify(const EthereumVerifyMessage *msg) {
  if (msg->signature.size != 65) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Malformed signature"));
    return 1;
  }

  uint8_t pubkeyhash[PUBKEYHASH_LEN] = {0};
  if (!ethereum_parse(msg->address, pubkeyhash)) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Malformed address"));
    return 1;
  }

  uint8_t pubkey[65] = {0};
  uint8_t hash[32] = {0};

  ethereum_message_hash(msg->message.bytes, msg->message.size, hash);

  /* v should be 27, 28 but some implementations use 0,1.  We are
   * compatible with both.
   */
  uint8_t v = msg->signature.bytes[64];
  if (v >= 27) {
    v -= 27;
  }

  if (v >= 2) {
    return 2;
  }

  if (ecdsa_recover_pub_from_sig(&secp256k1, pubkey, msg->signature.bytes, hash,
                                 v) != 0) {
    return 2;
  }

  struct SHA3_CTX ctx = {0};
  sha3_256_Init(&ctx);
  sha3_Update(&ctx, pubkey + 1, 64);
  keccak_Final(&ctx, hash);

  /* result are the least significant 160 bits */
  if (memcmp(pubkeyhash, hash + 12, PUBKEYHASH_LEN) != 0) {
    return 2;
  }
  return 0;
}

/*
 * EIP-712 hashes might have no message_hash if primaryType="EIP712Domain".
 * In this case, set has_message_hash=false.
 */
static void ethereum_typed_hash(const uint8_t domain_separator_hash[32],
                                const uint8_t message_hash[32],
                                bool has_message_hash, uint8_t hash[32]) {
  struct SHA3_CTX ctx = {0};
  sha3_256_Init(&ctx);
  sha3_Update(&ctx, (const uint8_t *)"\x19\x01", 2);
  sha3_Update(&ctx, domain_separator_hash, 32);
  if (has_message_hash) {
    sha3_Update(&ctx, message_hash, 32);
  }
  keccak_Final(&ctx, hash);
}

void ethereum_typed_hash_sign(const EthereumSignTypedHash *msg,
                              const HDNode *node,
                              EthereumTypedDataSignature *resp) {
  uint8_t hash[32] = {0};

  ethereum_typed_hash(msg->domain_separator_hash.bytes, msg->message_hash.bytes,
                      msg->has_message_hash, hash);

  uint8_t v = 0;
  if (ecdsa_sign_digest(&secp256k1, node->private_key, hash,
                        resp->signature.bytes, &v, ethereum_is_canonic) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    return;
  }

  resp->signature.bytes[64] = 27 + v;
  resp->signature.size = 65;
  msg_write(MessageType_MessageType_EthereumTypedDataSignature, resp);
}

bool ethereum_parse(const char *address, uint8_t pubkeyhash[PUBKEYHASH_LEN]) {
  memzero(pubkeyhash, PUBKEYHASH_LEN);
  size_t len = strlen(address);
  if (len == 40) {
    // do nothing
  } else if (len == 42) {
    // check for "0x" prefix and strip it when required
    if (address[0] != '0') return false;
    if (address[1] != 'x' && address[1] != 'X') return false;
    address += 2;
    len -= 2;
  } else {
    return false;
  }
  for (size_t i = 0; i < len; i++) {
    if (address[i] >= '0' && address[i] <= '9') {
      pubkeyhash[i / 2] |= (address[i] - '0') << ((1 - (i % 2)) * 4);
    } else if (address[i] >= 'a' && address[i] <= 'f') {
      pubkeyhash[i / 2] |= ((address[i] - 'a') + 10) << ((1 - (i % 2)) * 4);
    } else if (address[i] >= 'A' && address[i] <= 'F') {
      pubkeyhash[i / 2] |= ((address[i] - 'A') + 10) << ((1 - (i % 2)) * 4);
    } else {
      return false;
    }
  }
  return true;
}

static bool check_ethereum_slip44_unhardened(
    uint32_t slip44, const EthereumNetworkInfo *network) {
  if (is_unknown_network(network)) {
    // Allow Ethereum or testnet paths for unknown networks.
    return slip44 == 60 || slip44 == 1;
  } else if (network->slip44 != 60 && network->slip44 != 1) {
    // Allow cross-signing with Ethereum unless it's testnet.
    return (slip44 == network->slip44 || slip44 == 60);
  } else {
    return (slip44 == network->slip44);
  }
}

static bool ethereum_path_check_bip44(uint32_t address_n_count,
                                      const uint32_t *address_n,
                                      bool pubkey_export,
                                      const EthereumNetworkInfo *network) {
  bool valid = (address_n_count >= 3);
  valid = valid && (address_n[0] == (PATH_HARDENED | 44));
  valid = valid && (address_n[1] & PATH_HARDENED);
  valid = valid && (address_n[2] & PATH_HARDENED);
  valid = valid && ((address_n[2] & PATH_UNHARDEN_MASK) <= PATH_MAX_ACCOUNT);

  uint32_t path_slip44 = address_n[1] & PATH_UNHARDEN_MASK;
  valid = valid && check_ethereum_slip44_unhardened(path_slip44, network);

  if (pubkey_export) {
    // m/44'/coin_type'/account'/*
    return valid;
  }

  if (address_n_count == 3) {
    // SEP-0005 for non-UTXO-based currencies, defined by Stellar:
    // https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
    // m/44'/coin_type'/account'
    return valid;
  }

  if (address_n_count == 4) {
    // Also to support "Ledger Live" legacy paths
    // https://github.com/trezor/trezor-firmware/issues/1749
    // m/44'/coin_type'/0'/account
    valid = valid && (address_n[2] == (PATH_HARDENED | 0));
    valid = valid && (address_n[3] <= PATH_MAX_ACCOUNT);
    return valid;
  }

  // We believe Ethereum should use the SEP-0005 scheme for everything, because
  // it is account-based, rather than UTXO-based. Unfortunately, a lot of
  // Ethereum tools (MEW, Metamask) do not use such scheme and set account = 0
  // and then iterate the address index. For compatibility, we allow this scheme
  // as well.
  // m/44'/coin_type'/account'/change/address_index
  valid = valid && (address_n_count == 5);
  valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
  valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);

  return valid;
}

static bool ethereum_path_check_casa45(uint32_t address_n_count,
                                       const uint32_t *address_n,
                                       const EthereumNetworkInfo *network) {
  bool valid = (address_n_count == 5);
  valid = valid && (address_n[0] == (PATH_HARDENED | 45));
  valid = valid && (address_n[1] < PATH_HARDENED);
  valid = valid && (address_n[2] <= PATH_MAX_ACCOUNT);
  valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
  valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);

  uint32_t path_slip44 = address_n[1];
  valid = valid && check_ethereum_slip44_unhardened(path_slip44, network);

  return valid;
}

bool ethereum_path_check(uint32_t address_n_count, const uint32_t *address_n,
                         bool pubkey_export,
                         const EthereumNetworkInfo *network) {
  if (address_n_count == 0) {
    return false;
  }
  if (address_n[0] == (PATH_HARDENED | 44)) {
    return ethereum_path_check_bip44(address_n_count, address_n, pubkey_export,
                                     network);
  }
  if (address_n[0] == (PATH_HARDENED | 45)) {
    return ethereum_path_check_casa45(address_n_count, address_n, network);
  }
  return false;
}
