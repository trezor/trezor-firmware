/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include "transaction.h"
#include <string.h>
#include "address.h"
#include "base58.h"
#include "cash_addr.h"
#include "coins.h"
#include "crypto.h"
#include "debug.h"
#include "ecdsa.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.pb.h"
#include "protect.h"
#include "ripemd160.h"
#include "segwit_addr.h"
#include "util.h"

#define SEGWIT_VERSION_0 0
#define SEGWIT_VERSION_1 1

#define CASHADDR_P2KH (0)
#define CASHADDR_P2SH (8)
#define CASHADDR_160 (0)

/* transaction input size (without script): 32 prevhash, 4 idx, 4 sequence */
#define TXSIZE_INPUT 40
/* transaction output size (without script): 8 amount */
#define TXSIZE_OUTPUT 8
/* size of a pubkey */
#define TXSIZE_PUBKEY 33
/* size of a DER signature (3 type bytes, 3 len bytes, 33 R, 32 S, 1 sighash */
#define TXSIZE_SIGNATURE 72
/* size of a multiscript without pubkey (1 M, 1 N, 1 checksig) */
#define TXSIZE_MULTISIGSCRIPT 3
/* size of a p2wpkh script (1 version, 1 push, 20 hash) */
#define TXSIZE_WITNESSPKHASH 22
/* size of a p2wsh script (1 version, 1 push, 32 hash) */
#define TXSIZE_WITNESSSCRIPT 34
/* size of a p2tr script (1 version, 1 push, 32 hash) */
#define TXSIZE_TAPROOT 34
/* size of a p2pkh script (dup, hash, push, 20 pubkeyhash, equal, checksig) */
#define TXSIZE_P2PKHASH 25
/* size of a p2sh script (hash, push, 20 scripthash, equal) */
#define TXSIZE_P2SCRIPT 23
/* size of a Decred witness (without script): 8 amount, 4 block height, 4 block
 * index */
#define TXSIZE_DECRED_WITNESS 16
/* support version of Decred script_version */
#define DECRED_SCRIPT_VERSION 0

static const uint8_t segwit_header[2] = {0, 1};

static inline uint32_t op_push_size(uint32_t i) {
  if (i < 0x4C) {
    return 1;
  }
  if (i < 0x100) {
    return 2;
  }
  if (i < 0x10000) {
    return 3;
  }
  return 5;
}

uint32_t op_push(uint32_t i, uint8_t *out) {
  if (i < 0x4C) {
    out[0] = i & 0xFF;
    return 1;
  }
  if (i < 0x100) {
    out[0] = 0x4C;
    out[1] = i & 0xFF;
    return 2;
  }
  if (i < 0x10000) {
    out[0] = 0x4D;
    out[1] = i & 0xFF;
    out[2] = (i >> 8) & 0xFF;
    return 3;
  }
  out[0] = 0x4E;
  out[1] = i & 0xFF;
  out[2] = (i >> 8) & 0xFF;
  out[3] = (i >> 16) & 0xFF;
  out[4] = (i >> 24) & 0xFF;
  return 5;
}

bool compute_address(const CoinInfo *coin, InputScriptType script_type,
                     const HDNode *node, bool has_multisig,
                     const MultisigRedeemScriptType *multisig,
                     char address[MAX_ADDR_SIZE]) {
  uint8_t raw[MAX_ADDR_RAW_SIZE] = {0};
  uint8_t digest[32] = {0};
  size_t prelen = 0;

  if (has_multisig) {
    if (cryptoMultisigPubkeyIndex(coin, multisig, node->public_key) < 0) {
      return 0;
    }
    if (compile_script_multisig_hash(coin, multisig, digest) == 0) {
      return 0;
    }
    if (script_type == InputScriptType_SPENDWITNESS) {
      // segwit p2wsh:  script hash is single sha256
      if (!coin->has_segwit || !coin->bech32_prefix) {
        return 0;
      }
      if (!segwit_addr_encode(address, coin->bech32_prefix, SEGWIT_VERSION_0,
                              digest, 32)) {
        return 0;
      }
    } else if (script_type == InputScriptType_SPENDP2SHWITNESS) {
      // segwit p2wsh encapsuled in p2sh address
      if (!coin->has_segwit) {
        return 0;
      }
      raw[0] = 0;                   // push version
      raw[1] = 32;                  // push 32 bytes
      memcpy(raw + 2, digest, 32);  // push hash
      hasher_Raw(coin->curve->hasher_pubkey, raw, 34, digest);
      prelen = address_prefix_bytes_len(coin->address_type_p2sh);
      address_write_prefix_bytes(coin->address_type_p2sh, raw);
      memcpy(raw + prelen, digest, 32);
      if (!base58_encode_check(raw, prelen + 20, coin->curve->hasher_base58,
                               address, MAX_ADDR_SIZE)) {
        return 0;
      }
    } else if (coin->cashaddr_prefix) {
      raw[0] = CASHADDR_P2SH | CASHADDR_160;
      ripemd160(digest, 32, raw + 1);
      if (!cash_addr_encode(address, coin->cashaddr_prefix, raw, 21)) {
        return 0;
      }
    } else {
      // non-segwit p2sh multisig
      prelen = address_prefix_bytes_len(coin->address_type_p2sh);
      address_write_prefix_bytes(coin->address_type_p2sh, raw);
      ripemd160(digest, 32, raw + prelen);
      if (!base58_encode_check(raw, prelen + 20, coin->curve->hasher_base58,
                               address, MAX_ADDR_SIZE)) {
        return 0;
      }
    }
  } else if (script_type == InputScriptType_SPENDWITNESS) {
    // segwit p2wpkh:  pubkey hash is ripemd160 of sha256
    if (!coin->has_segwit || !coin->bech32_prefix) {
      return 0;
    }
    ecdsa_get_pubkeyhash(node->public_key, coin->curve->hasher_pubkey, digest);
    if (!segwit_addr_encode(address, coin->bech32_prefix, SEGWIT_VERSION_0,
                            digest, 20)) {
      return 0;
    }
  } else if (script_type == InputScriptType_SPENDTAPROOT) {
    // taproot
    if (!coin->has_taproot || !coin->has_segwit || !coin->bech32_prefix) {
      return 0;
    }
    uint8_t tweaked_pubkey[32];
    // TODO: replace the memcpy below with
    // ecdsa_tweak_pubkey(node->public_key, tweaked_pubkey);
    memcpy(tweaked_pubkey, node->public_key, 32);  // HACK!
    if (!segwit_addr_encode(address, coin->bech32_prefix, SEGWIT_VERSION_1,
                            tweaked_pubkey, 32)) {
      return 0;
    }
  } else if (script_type == InputScriptType_SPENDP2SHWITNESS) {
    // segwit p2wpkh embedded in p2sh
    if (!coin->has_segwit) {
      return 0;
    }
    ecdsa_get_address_segwit_p2sh(
        node->public_key, coin->address_type_p2sh, coin->curve->hasher_pubkey,
        coin->curve->hasher_base58, address, MAX_ADDR_SIZE);
  } else if (coin->cashaddr_prefix) {
    ecdsa_get_address_raw(node->public_key, CASHADDR_P2KH | CASHADDR_160,
                          coin->curve->hasher_pubkey, raw);
    if (!cash_addr_encode(address, coin->cashaddr_prefix, raw, 21)) {
      return 0;
    }
  } else {
    ecdsa_get_address(node->public_key, coin->address_type,
                      coin->curve->hasher_pubkey, coin->curve->hasher_base58,
                      address, MAX_ADDR_SIZE);
  }
  return 1;
}

int compile_output(const CoinInfo *coin, AmountUnit amount_unit,
                   const HDNode *root, TxOutputType *in, TxOutputBinType *out,
                   bool needs_confirm) {
  memzero(out, sizeof(TxOutputBinType));
  out->amount = in->amount;
  out->decred_script_version = DECRED_SCRIPT_VERSION;
  uint8_t addr_raw[MAX_ADDR_RAW_SIZE] = {0};
  size_t addr_raw_len = 0;

  if (in->script_type == OutputScriptType_PAYTOOPRETURN) {
    // only 0 satoshi allowed for OP_RETURN
    if (in->amount != 0 || in->has_address || (in->address_n_count > 0) ||
        in->has_multisig) {
      return 0;  // failed to compile output
    }
    if (needs_confirm) {
      if (in->op_return_data.size >= 8 &&
          memcmp(in->op_return_data.bytes, "omni", 4) ==
              0) {  // OMNI transaction
        layoutConfirmOmni(in->op_return_data.bytes, in->op_return_data.size);
      } else {
        layoutConfirmOpReturn(in->op_return_data.bytes,
                              in->op_return_data.size);
      }
      if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput,
                         false)) {
        return -1;  // user aborted
      }
    }
    uint32_t r = 0;
    out->script_pubkey.bytes[0] = 0x6A;
    r++;  // OP_RETURN
    r += op_push(in->op_return_data.size, out->script_pubkey.bytes + r);
    memcpy(out->script_pubkey.bytes + r, in->op_return_data.bytes,
           in->op_return_data.size);
    r += in->op_return_data.size;
    out->script_pubkey.size = r;
    return r;
  }

  if (in->address_n_count > 0) {
    static CONFIDENTIAL HDNode node;
    InputScriptType input_script_type = 0;

    switch (in->script_type) {
      case OutputScriptType_PAYTOADDRESS:
        input_script_type = InputScriptType_SPENDADDRESS;
        break;
      case OutputScriptType_PAYTOMULTISIG:
        input_script_type = InputScriptType_SPENDMULTISIG;
        break;
      case OutputScriptType_PAYTOWITNESS:
        input_script_type = InputScriptType_SPENDWITNESS;
        break;
      case OutputScriptType_PAYTOP2SHWITNESS:
        input_script_type = InputScriptType_SPENDP2SHWITNESS;
        break;
      case OutputScriptType_PAYTOTAPROOT:
        input_script_type = InputScriptType_SPENDTAPROOT;
        break;
      default:
        return 0;  // failed to compile output
    }
    memcpy(&node, root, sizeof(HDNode));
    if (hdnode_private_ckd_cached(&node, in->address_n, in->address_n_count,
                                  NULL) == 0) {
      return 0;  // failed to compile output
    }
    hdnode_fill_public_key(&node);
    if (!compute_address(coin, input_script_type, &node, in->has_multisig,
                         &in->multisig, in->address)) {
      return 0;  // failed to compile output
    }
  } else if (!in->has_address) {
    return 0;  // failed to compile output
  }

  addr_raw_len = base58_decode_check(in->address, coin->curve->hasher_base58,
                                     addr_raw, MAX_ADDR_RAW_SIZE);
  size_t prefix_len = 0;
  // p2pkh
  if (addr_raw_len ==
          20 + (prefix_len = address_prefix_bytes_len(coin->address_type)) &&
      address_check_prefix(addr_raw, coin->address_type)) {
    out->script_pubkey.bytes[0] = 0x76;  // OP_DUP
    out->script_pubkey.bytes[1] = 0xA9;  // OP_HASH_160
    out->script_pubkey.bytes[2] = 0x14;  // pushing 20 bytes
    memcpy(out->script_pubkey.bytes + 3, addr_raw + prefix_len, 20);
    out->script_pubkey.bytes[23] = 0x88;  // OP_EQUALVERIFY
    out->script_pubkey.bytes[24] = 0xAC;  // OP_CHECKSIG
    out->script_pubkey.size = 25;
  } else
      // p2sh
      if (addr_raw_len == 20 + (prefix_len = address_prefix_bytes_len(
                                    coin->address_type_p2sh)) &&
          address_check_prefix(addr_raw, coin->address_type_p2sh)) {
    out->script_pubkey.bytes[0] = 0xA9;  // OP_HASH_160
    out->script_pubkey.bytes[1] = 0x14;  // pushing 20 bytes
    memcpy(out->script_pubkey.bytes + 2, addr_raw + prefix_len, 20);
    out->script_pubkey.bytes[22] = 0x87;  // OP_EQUAL
    out->script_pubkey.size = 23;
  } else if (coin->cashaddr_prefix &&
             cash_addr_decode(addr_raw, &addr_raw_len, coin->cashaddr_prefix,
                              in->address)) {
    if (addr_raw_len == 21 && addr_raw[0] == (CASHADDR_P2KH | CASHADDR_160)) {
      out->script_pubkey.bytes[0] = 0x76;  // OP_DUP
      out->script_pubkey.bytes[1] = 0xA9;  // OP_HASH_160
      out->script_pubkey.bytes[2] = 0x14;  // pushing 20 bytes
      memcpy(out->script_pubkey.bytes + 3, addr_raw + 1, 20);
      out->script_pubkey.bytes[23] = 0x88;  // OP_EQUALVERIFY
      out->script_pubkey.bytes[24] = 0xAC;  // OP_CHECKSIG
      out->script_pubkey.size = 25;

    } else if (addr_raw_len == 21 &&
               addr_raw[0] == (CASHADDR_P2SH | CASHADDR_160)) {
      out->script_pubkey.bytes[0] = 0xA9;  // OP_HASH_160
      out->script_pubkey.bytes[1] = 0x14;  // pushing 20 bytes
      memcpy(out->script_pubkey.bytes + 2, addr_raw + 1, 20);
      out->script_pubkey.bytes[22] = 0x87;  // OP_EQUAL
      out->script_pubkey.size = 23;
    } else {
      return 0;
    }
  } else if (coin->bech32_prefix) {
    int witver = 0;
    if (!segwit_addr_decode(&witver, addr_raw, &addr_raw_len,
                            coin->bech32_prefix, in->address)) {
      return 0;
    }
    // segwit:
    // push 1 byte version id (opcode OP_0 = 0, OP_i = 80+i)
    // push addr_raw (segwit_addr_decode makes sure addr_raw_len is at most 40)
    out->script_pubkey.bytes[0] = witver == 0 ? 0 : 80 + witver;
    out->script_pubkey.bytes[1] = addr_raw_len;
    memcpy(out->script_pubkey.bytes + 2, addr_raw, addr_raw_len);
    out->script_pubkey.size = addr_raw_len + 2;
  } else {
    return 0;
  }

  if (needs_confirm) {
    layoutConfirmOutput(coin, amount_unit, in);
    if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
      return -1;  // user aborted
    }
  }

  return out->script_pubkey.size;
}

uint32_t compile_script_sig(uint32_t address_type, const uint8_t *pubkeyhash,
                            uint8_t *out) {
  if (coinByAddressType(address_type)) {  // valid coin type
    out[0] = 0x76;                        // OP_DUP
    out[1] = 0xA9;                        // OP_HASH_160
    out[2] = 0x14;                        // pushing 20 bytes
    memcpy(out + 3, pubkeyhash, 20);
    out[23] = 0x88;  // OP_EQUALVERIFY
    out[24] = 0xAC;  // OP_CHECKSIG
    return 25;
  } else {
    return 0;  // unsupported
  }
}

// if out == NULL just compute the length
uint32_t compile_script_multisig(const CoinInfo *coin,
                                 const MultisigRedeemScriptType *multisig,
                                 uint8_t *out) {
  const uint32_t m = multisig->m;
  const uint32_t n = cryptoMultisigPubkeyCount(multisig);
  if (m < 1 || m > 15) return 0;
  if (n < 1 || n > 15) return 0;
  uint32_t r = 0;
  if (out) {
    out[r] = 0x50 + m;
    r++;
    for (uint32_t i = 0; i < n; i++) {
      out[r] = 33;
      r++;  // OP_PUSH 33
      const HDNode *pubnode = cryptoMultisigPubkey(coin, multisig, i);
      if (!pubnode) return 0;
      memcpy(out + r, pubnode->public_key, 33);
      r += 33;
    }
    out[r] = 0x50 + n;
    r++;
    out[r] = 0xAE;
    r++;  // OP_CHECKMULTISIG
  } else {
    r = 1 + 34 * n + 2;
  }
  return r;
}

uint32_t compile_script_multisig_hash(const CoinInfo *coin,
                                      const MultisigRedeemScriptType *multisig,
                                      uint8_t *hash) {
  const uint32_t m = multisig->m;
  const uint32_t n = cryptoMultisigPubkeyCount(multisig);
  if (m < 1 || m > 15) return 0;
  if (n < 1 || n > 15) return 0;

  Hasher hasher = {0};
  hasher_Init(&hasher, coin->curve->hasher_script);

  uint8_t d[2] = {0};
  d[0] = 0x50 + m;
  hasher_Update(&hasher, d, 1);
  for (uint32_t i = 0; i < n; i++) {
    d[0] = 33;
    hasher_Update(&hasher, d, 1);  // OP_PUSH 33
    const HDNode *pubnode = cryptoMultisigPubkey(coin, multisig, i);
    if (!pubnode) return 0;
    hasher_Update(&hasher, pubnode->public_key, 33);
  }
  d[0] = 0x50 + n;
  d[1] = 0xAE;
  hasher_Update(&hasher, d, 2);

  hasher_Final(&hasher, hash);

  return 1;
}

uint32_t serialize_script_sig(const uint8_t *signature, uint32_t signature_len,
                              const uint8_t *pubkey, uint32_t pubkey_len,
                              uint8_t sighash, uint8_t *out) {
  uint32_t r = 0;
  r += op_push(signature_len + 1, out + r);
  memcpy(out + r, signature, signature_len);
  r += signature_len;
  out[r] = sighash;
  r++;
  r += op_push(pubkey_len, out + r);
  memcpy(out + r, pubkey, pubkey_len);
  r += pubkey_len;
  return r;
}

uint32_t serialize_script_multisig(const CoinInfo *coin,
                                   const MultisigRedeemScriptType *multisig,
                                   uint8_t sighash, uint8_t *out) {
  uint32_t r = 0;
#if !BITCOIN_ONLY
  if (!coin->decred) {
    // Decred fixed the off-by-one bug
#endif
    out[r] = 0x00;
    r++;
#if !BITCOIN_ONLY
  }
#endif
  for (uint32_t i = 0; i < multisig->signatures_count; i++) {
    if (multisig->signatures[i].size == 0) {
      continue;
    }
    r += op_push(multisig->signatures[i].size + 1, out + r);
    memcpy(out + r, multisig->signatures[i].bytes,
           multisig->signatures[i].size);
    r += multisig->signatures[i].size;
    out[r] = sighash;
    r++;
  }
  uint32_t script_len = compile_script_multisig(coin, multisig, 0);
  if (script_len == 0) {
    return 0;
  }
  r += op_push(script_len, out + r);
  r += compile_script_multisig(coin, multisig, out + r);
  return r;
}

// tx methods
void tx_input_check_hash(Hasher *hasher, const TxInputType *input) {
  hasher_Update(hasher, input->prev_hash.bytes, sizeof(input->prev_hash.bytes));
  hasher_Update(hasher, (const uint8_t *)&input->prev_index,
                sizeof(input->prev_index));
  hasher_Update(hasher, (const uint8_t *)&input->script_type,
                sizeof(input->script_type));
  hasher_Update(hasher, (const uint8_t *)&input->address_n_count,
                sizeof(input->address_n_count));
  for (int i = 0; i < input->address_n_count; ++i)
    hasher_Update(hasher, (const uint8_t *)&input->address_n[i],
                  sizeof(input->address_n[0]));
  hasher_Update(hasher, (const uint8_t *)&input->sequence,
                sizeof(input->sequence));
  hasher_Update(hasher, (const uint8_t *)&input->amount, sizeof(input->amount));
  return;
}

uint32_t tx_prevout_hash(Hasher *hasher, const TxInputType *input) {
  for (int i = 0; i < 32; i++) {
    hasher_Update(hasher, &(input->prev_hash.bytes[31 - i]), 1);
  }
  hasher_Update(hasher, (const uint8_t *)&input->prev_index, 4);
  return 36;
}

uint32_t tx_script_hash(Hasher *hasher, uint32_t size, const uint8_t *data) {
  int r = ser_length_hash(hasher, size);
  hasher_Update(hasher, data, size);
  return r + size;
}

uint32_t tx_sequence_hash(Hasher *hasher, const TxInputType *input) {
  hasher_Update(hasher, (const uint8_t *)&input->sequence, 4);
  return 4;
}

uint32_t tx_output_hash(Hasher *hasher, const TxOutputBinType *output,
                        bool decred) {
  uint32_t r = 0;
  hasher_Update(hasher, (const uint8_t *)&output->amount, 8);
  r += 8;
  if (decred) {
    uint16_t script_version = output->decred_script_version & 0xFFFF;
    hasher_Update(hasher, (const uint8_t *)&script_version, 2);
    r += 2;
  }
  r += tx_script_hash(hasher, output->script_pubkey.size,
                      output->script_pubkey.bytes);
  return r;
}

uint32_t tx_serialize_script(uint32_t size, const uint8_t *data, uint8_t *out) {
  int r = ser_length(size, out);
  memcpy(out + r, data, size);
  return r + size;
}

uint32_t tx_serialize_header(TxStruct *tx, uint8_t *out) {
  int r = 4;
#if !BITCOIN_ONLY
  if (tx->is_zcashlike && tx->version >= 3) {
    uint32_t ver = tx->version | TX_OVERWINTERED;
    memcpy(out, &ver, 4);
    memcpy(out + 4, &(tx->version_group_id), 4);
    r += 4;
  } else
#endif
  {
    memcpy(out, &(tx->version), 4);
#if !BITCOIN_ONLY
    if (tx->timestamp) {
      memcpy(out + r, &(tx->timestamp), 4);
      r += 4;
    }
#endif
    if (tx->is_segwit) {
      memcpy(out + r, segwit_header, 2);
      r += 2;
    }
  }
  return r + ser_length(tx->inputs_len, out + r);
}

uint32_t tx_serialize_header_hash(TxStruct *tx) {
  int r = 4;
#if !BITCOIN_ONLY
  if (tx->is_zcashlike && tx->version >= 3) {
    uint32_t ver = tx->version | TX_OVERWINTERED;
    hasher_Update(&(tx->hasher), (const uint8_t *)&ver, 4);
    hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->version_group_id), 4);
    r += 4;
  } else
#endif
  {
    hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->version), 4);
#if !BITCOIN_ONLY
    if (tx->timestamp) {
      hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->timestamp), 4);
    }
#endif
    if (tx->is_segwit) {
      hasher_Update(&(tx->hasher), segwit_header, 2);
      r += 2;
    }
  }
  return r + ser_length_hash(&(tx->hasher), tx->inputs_len);
}

uint32_t tx_serialize_input(TxStruct *tx, const TxInputType *input,
                            uint8_t *out) {
  if (tx->have_inputs >= tx->inputs_len) {
    // already got all inputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_inputs == 0) {
    r += tx_serialize_header(tx, out + r);
  }
  for (int i = 0; i < 32; i++) {
    *(out + r + i) = input->prev_hash.bytes[31 - i];
  }
  r += 32;
  memcpy(out + r, &input->prev_index, 4);
  r += 4;
#if !BITCOIN_ONLY
  if (tx->is_decred) {
    uint8_t tree = input->decred_tree & 0xFF;
    out[r++] = tree;
  } else
#endif
  {
    r += tx_serialize_script(input->script_sig.size, input->script_sig.bytes,
                             out + r);
  }
  memcpy(out + r, &input->sequence, 4);
  r += 4;

  tx->have_inputs++;
  tx->size += r;

  return r;
}

uint32_t tx_serialize_input_hash(TxStruct *tx, const TxInputType *input) {
  if (tx->have_inputs >= tx->inputs_len) {
    // already got all inputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_inputs == 0) {
    r += tx_serialize_header_hash(tx);
  }
  r += tx_prevout_hash(&(tx->hasher), input);
#if !BITCOIN_ONLY
  if (tx->is_decred) {
    uint8_t tree = input->decred_tree & 0xFF;
    hasher_Update(&(tx->hasher), (const uint8_t *)&(tree), 1);
    r++;
  } else
#endif
  {
    r += tx_script_hash(&(tx->hasher), input->script_sig.size,
                        input->script_sig.bytes);
  }
  r += tx_sequence_hash(&(tx->hasher), input);

  tx->have_inputs++;
  tx->size += r;

  return r;
}

#if !BITCOIN_ONLY
uint32_t tx_serialize_decred_witness(TxStruct *tx, const TxInputType *input,
                                     uint8_t *out) {
  static const uint64_t amount = 0;
  static const uint32_t block_height = 0x00000000;
  static const uint32_t block_index = 0xFFFFFFFF;

  if (tx->have_inputs >= tx->inputs_len) {
    // already got all inputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_inputs == 0) {
    r += ser_length(tx->inputs_len, out + r);
  }
  if (input->has_amount) {
    memcpy(out + r, &input->amount, 8);
  } else {
    memcpy(out + r, &amount, 8);
  }
  r += 8;
  memcpy(out + r, &block_height, 4);
  r += 4;
  memcpy(out + r, &block_index, 4);
  r += 4;
  r += tx_serialize_script(input->script_sig.size, input->script_sig.bytes,
                           out + r);

  tx->have_inputs++;
  tx->size += r;

  return r;
}

uint32_t tx_serialize_decred_witness_hash(TxStruct *tx,
                                          const TxInputType *input) {
  if (tx->have_inputs >= tx->inputs_len) {
    // already got all inputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_inputs == 0) {
    r += tx_serialize_header_hash(tx);
  }
  if (input == NULL) {
    r += ser_length_hash(&(tx->hasher), 0);
  } else {
    r += tx_script_hash(&(tx->hasher), input->script_sig.size,
                        input->script_sig.bytes);
  }

  tx->have_inputs++;
  tx->size += r;

  return r;
}
#endif

uint32_t tx_serialize_middle(TxStruct *tx, uint8_t *out) {
  return ser_length(tx->outputs_len, out);
}

uint32_t tx_serialize_middle_hash(TxStruct *tx) {
  return ser_length_hash(&(tx->hasher), tx->outputs_len);
}

uint32_t tx_serialize_footer(TxStruct *tx, uint8_t *out) {
  memcpy(out, &(tx->lock_time), 4);
#if !BITCOIN_ONLY
  if (tx->is_zcashlike && tx->version == 4) {
    memcpy(out + 4, &(tx->expiry), 4);
    memzero(out + 8, 8);  // valueBalance
    out[16] = 0x00;       // nShieldedSpend
    out[17] = 0x00;       // nShieldedOutput
    out[18] = 0x00;       // nJoinSplit
    return 19;
  }
  if (tx->is_decred) {
    memcpy(out + 4, &(tx->expiry), 4);
    return 8;
  }
#endif
  return 4;
}

uint32_t tx_serialize_footer_hash(TxStruct *tx) {
  hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->lock_time), 4);
#if !BITCOIN_ONLY
  if (tx->is_zcashlike && tx->version >= 3) {
    hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->expiry), 4);
    return 8;
  }
  if (tx->is_decred) {
    hasher_Update(&(tx->hasher), (const uint8_t *)&(tx->expiry), 4);
    return 8;
  }
#endif
  return 4;
}

uint32_t tx_serialize_output(TxStruct *tx, const TxOutputBinType *output,
                             uint8_t *out) {
  if (tx->have_inputs < tx->inputs_len) {
    // not all inputs provided
    return 0;
  }
  if (tx->have_outputs >= tx->outputs_len) {
    // already got all outputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_outputs == 0) {
    r += tx_serialize_middle(tx, out + r);
  }
  memcpy(out + r, &output->amount, 8);
  r += 8;
#if !BITCOIN_ONLY
  if (tx->is_decred) {
    uint16_t script_version = output->decred_script_version & 0xFFFF;
    memcpy(out + r, &script_version, 2);
    r += 2;
  }
#endif
  r += tx_serialize_script(output->script_pubkey.size,
                           output->script_pubkey.bytes, out + r);
  tx->have_outputs++;
  if (tx->have_outputs == tx->outputs_len && !tx->is_segwit) {
    r += tx_serialize_footer(tx, out + r);
  }
  tx->size += r;
  return r;
}

uint32_t tx_serialize_output_hash(TxStruct *tx, const TxOutputBinType *output) {
  if (tx->have_inputs < tx->inputs_len) {
    // not all inputs provided
    return 0;
  }
  if (tx->have_outputs >= tx->outputs_len) {
    // already got all outputs
    return 0;
  }
  uint32_t r = 0;
  if (tx->have_outputs == 0) {
    r += tx_serialize_middle_hash(tx);
  }
  r += tx_output_hash(&(tx->hasher), output, tx->is_decred);
  tx->have_outputs++;
  if (tx->have_outputs == tx->outputs_len && !tx->is_segwit) {
    r += tx_serialize_footer_hash(tx);
  }
  tx->size += r;
  return r;
}

#if !BITCOIN_ONLY
uint32_t tx_serialize_extra_data_hash(TxStruct *tx, const uint8_t *data,
                                      uint32_t datalen) {
  if (tx->have_inputs < tx->inputs_len) {
    // not all inputs provided
    return 0;
  }
  if (tx->have_outputs < tx->outputs_len) {
    // not all inputs provided
    return 0;
  }
  if (tx->extra_data_received + datalen > tx->extra_data_len) {
    // we are receiving too much data
    return 0;
  }
  hasher_Update(&(tx->hasher), data, datalen);
  tx->extra_data_received += datalen;
  tx->size += datalen;
  return datalen;
}
#endif

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len,
             uint32_t version, uint32_t lock_time, uint32_t expiry,
             uint32_t extra_data_len, HasherType hasher_sign, bool is_zcashlike,
             uint32_t version_group_id, uint32_t timestamp) {
  tx->inputs_len = inputs_len;
  tx->outputs_len = outputs_len;
  tx->version = version;
  tx->lock_time = lock_time;
  tx->expiry = expiry;
  tx->have_inputs = 0;
  tx->have_outputs = 0;
  tx->extra_data_len = extra_data_len;
  tx->extra_data_received = 0;
  tx->size = 0;
  tx->is_segwit = false;
  tx->is_decred = false;
  tx->is_zcashlike = is_zcashlike;
  tx->version_group_id = version_group_id;
  tx->timestamp = timestamp;
  hasher_Init(&(tx->hasher), hasher_sign);
}

void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse) {
  hasher_Final(&(t->hasher), hash);
  if (!reverse) return;
  for (uint8_t i = 0; i < 16; i++) {
    uint8_t k = hash[31 - i];
    hash[31 - i] = hash[i];
    hash[i] = k;
  }
}

static uint32_t tx_input_script_size(const TxInputType *txinput) {
  uint32_t input_script_size = 0;
  if (txinput->has_multisig) {
    uint32_t multisig_script_size =
        TXSIZE_MULTISIGSCRIPT +
        cryptoMultisigPubkeyCount(&(txinput->multisig)) * (1 + TXSIZE_PUBKEY);
    input_script_size = 1  // the OP_FALSE bug in multisig
                        + txinput->multisig.m * (1 + TXSIZE_SIGNATURE) +
                        op_push_size(multisig_script_size) +
                        multisig_script_size;
  } else {
    input_script_size = (1 + TXSIZE_SIGNATURE + 1 + TXSIZE_PUBKEY);
  }

  return input_script_size;
}

uint32_t tx_input_weight(const CoinInfo *coin, const TxInputType *txinput) {
#if !BITCOIN_ONLY
  if (coin->decred) {
    return 4 * (TXSIZE_INPUT + 1);  // Decred tree
  }
#else
  (void)coin;
#endif

  uint32_t input_script_size = tx_input_script_size(txinput);
  uint32_t weight = 4 * TXSIZE_INPUT;
  if (txinput->script_type == InputScriptType_SPENDADDRESS ||
      txinput->script_type == InputScriptType_SPENDMULTISIG) {
    input_script_size += ser_length_size(input_script_size);
    weight += 4 * input_script_size;
  } else if (txinput->script_type == InputScriptType_SPENDWITNESS ||
             // TODO: is the following line correct?
             txinput->script_type == InputScriptType_SPENDTAPROOT ||
             txinput->script_type == InputScriptType_SPENDP2SHWITNESS) {
    if (txinput->script_type == InputScriptType_SPENDP2SHWITNESS) {
      weight += 4 * (2 + (txinput->has_multisig ? TXSIZE_WITNESSSCRIPT
                                                : TXSIZE_WITNESSPKHASH));
    } else {
      weight += 4;  // empty input script
    }
    weight += input_script_size;  // discounted witness
  }
  return weight;
}

uint32_t tx_output_weight(const CoinInfo *coin, const TxOutputType *txoutput) {
  uint32_t output_script_size = 0;
  if (txoutput->script_type == OutputScriptType_PAYTOOPRETURN) {
    output_script_size = 1 + op_push_size(txoutput->op_return_data.size) +
                         txoutput->op_return_data.size;
  } else if (txoutput->address_n_count > 0) {
    if (txoutput->script_type == OutputScriptType_PAYTOWITNESS) {
      output_script_size =
          txoutput->has_multisig ? TXSIZE_WITNESSSCRIPT : TXSIZE_WITNESSPKHASH;
    } else if (txoutput->script_type == OutputScriptType_PAYTOTAPROOT) {
      output_script_size = TXSIZE_TAPROOT;
    } else if (txoutput->script_type == OutputScriptType_PAYTOP2SHWITNESS) {
      output_script_size = TXSIZE_P2SCRIPT;
    } else {
      output_script_size =
          txoutput->has_multisig ? TXSIZE_P2SCRIPT : TXSIZE_P2PKHASH;
    }
  } else {
    uint8_t addr_raw[MAX_ADDR_RAW_SIZE] = {0};
    int witver = 0;
    size_t addr_raw_len = 0;
    if (coin->cashaddr_prefix &&
        cash_addr_decode(addr_raw, &addr_raw_len, coin->cashaddr_prefix,
                         txoutput->address)) {
      if (addr_raw_len == 21 && addr_raw[0] == (CASHADDR_P2KH | CASHADDR_160)) {
        output_script_size = TXSIZE_P2PKHASH;
      } else if (addr_raw_len == 21 &&
                 addr_raw[0] == (CASHADDR_P2SH | CASHADDR_160)) {
        output_script_size = TXSIZE_P2SCRIPT;
      }
    } else if (coin->bech32_prefix &&
               segwit_addr_decode(&witver, addr_raw, &addr_raw_len,
                                  coin->bech32_prefix, txoutput->address)) {
      output_script_size = 2 + addr_raw_len;
    } else {
      addr_raw_len =
          base58_decode_check(txoutput->address, coin->curve->hasher_base58,
                              addr_raw, MAX_ADDR_RAW_SIZE);
      if (address_check_prefix(addr_raw, coin->address_type)) {
        output_script_size = TXSIZE_P2PKHASH;
      } else if (address_check_prefix(addr_raw, coin->address_type_p2sh)) {
        output_script_size = TXSIZE_P2SCRIPT;
      }
    }
  }
  output_script_size += ser_length_size(output_script_size);

  uint32_t size = TXSIZE_OUTPUT;
#if !BITCOIN_ONLY
  if (coin->decred) {
    size += 2;  // Decred script version
  }
#endif

  return 4 * (size + output_script_size);
}

#if !BITCOIN_ONLY
uint32_t tx_decred_witness_weight(const TxInputType *txinput) {
  uint32_t input_script_size = tx_input_script_size(txinput);
  uint32_t size = TXSIZE_DECRED_WITNESS + ser_length_size(input_script_size) +
                  input_script_size;

  return 4 * size;
}
#endif
