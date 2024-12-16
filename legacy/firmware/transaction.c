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
#include "coins.h"
#include "crypto.h"
#include "debug.h"
#include "ecdsa.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.pb.h"
#include "protect.h"
#include "ripemd160.h"
#include "secp256k1.h"
#include "segwit_addr.h"
#include "util.h"
#include "zkp_bip340.h"

#if !BITCOIN_ONLY
#include "cash_addr.h"
#endif

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
#define TXSIZE_DER_SIGNATURE 72
/* size of a Schnorr signature (32 R, 32 S, no sighash) */
#define TXSIZE_SCHNORR_SIGNATURE 64
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

static const uint8_t segwit_header[2] = {0, 1};

static const uint8_t SLIP19_VERSION_MAGIC[] = {0x53, 0x4c, 0x00, 0x19};

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
    } else if (script_type == InputScriptType_SPENDADDRESS ||
               script_type == InputScriptType_SPENDMULTISIG) {
#if !BITCOIN_ONLY
      if (coin->cashaddr_prefix) {
        raw[0] = CASHADDR_P2SH | CASHADDR_160;
        ripemd160(digest, 32, raw + 1);
        if (!cash_addr_encode(address, coin->cashaddr_prefix, raw, 21)) {
          return 0;
        }
      } else
#endif
      {
        // non-segwit p2sh multisig
        prelen = address_prefix_bytes_len(coin->address_type_p2sh);
        address_write_prefix_bytes(coin->address_type_p2sh, raw);
        ripemd160(digest, 32, raw + prelen);
        if (!base58_encode_check(raw, prelen + 20, coin->curve->hasher_base58,
                                 address, MAX_ADDR_SIZE)) {
          return 0;
        }
      }
    } else {
      // unsupported script type
      return 0;
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
    zkp_bip340_tweak_public_key(node->public_key + 1, NULL, tweaked_pubkey);
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
  } else if (script_type == InputScriptType_SPENDADDRESS) {
#if !BITCOIN_ONLY
    if (coin->cashaddr_prefix) {
      ecdsa_get_address_raw(node->public_key, CASHADDR_P2KH | CASHADDR_160,
                            coin->curve->hasher_pubkey, raw);
      if (!cash_addr_encode(address, coin->cashaddr_prefix, raw, 21)) {
        return 0;
      }
    } else
#endif
    {
      ecdsa_get_address(node->public_key, coin->address_type,
                        coin->curve->hasher_pubkey, coin->curve->hasher_base58,
                        address, MAX_ADDR_SIZE);
    }
  } else {
    // unsupported script type
    return 0;
  }
  return 1;
}

int address_to_script_pubkey(const CoinInfo *coin, const char *address,
                             uint8_t *script_pubkey, pb_size_t *size) {
  uint8_t addr_raw[MAX_ADDR_RAW_SIZE] = {0};
  size_t addr_raw_len = base58_decode_check(address, coin->curve->hasher_base58,
                                            addr_raw, MAX_ADDR_RAW_SIZE);

  // P2PKH
  size_t prefix_len = address_prefix_bytes_len(coin->address_type);
  if (addr_raw_len == 20 + prefix_len &&
      address_check_prefix(addr_raw, coin->address_type)) {
    script_pubkey[0] = 0x76;  // OP_DUP
    script_pubkey[1] = 0xA9;  // OP_HASH_160
    script_pubkey[2] = 0x14;  // pushing 20 bytes
    memcpy(script_pubkey + 3, addr_raw + prefix_len, 20);
    script_pubkey[23] = 0x88;  // OP_EQUALVERIFY
    script_pubkey[24] = 0xAC;  // OP_CHECKSIG
    *size = 25;
    return 1;
  }

  // P2SH
  prefix_len = address_prefix_bytes_len(coin->address_type_p2sh);
  if (addr_raw_len == 20 + prefix_len &&
      address_check_prefix(addr_raw, coin->address_type_p2sh)) {
    script_pubkey[0] = 0xA9;  // OP_HASH_160
    script_pubkey[1] = 0x14;  // pushing 20 bytes
    memcpy(script_pubkey + 2, addr_raw + prefix_len, 20);
    script_pubkey[22] = 0x87;  // OP_EQUAL
    *size = 23;
    return 1;
  }

#if !BITCOIN_ONLY
  if (coin->cashaddr_prefix &&
      cash_addr_decode(addr_raw, &addr_raw_len, coin->cashaddr_prefix,
                       address)) {
    if (addr_raw_len == 21 && addr_raw[0] == (CASHADDR_P2KH | CASHADDR_160)) {
      script_pubkey[0] = 0x76;  // OP_DUP
      script_pubkey[1] = 0xA9;  // OP_HASH_160
      script_pubkey[2] = 0x14;  // pushing 20 bytes
      memcpy(script_pubkey + 3, addr_raw + 1, 20);
      script_pubkey[23] = 0x88;  // OP_EQUALVERIFY
      script_pubkey[24] = 0xAC;  // OP_CHECKSIG
      *size = 25;
      return 1;
    } else if (addr_raw_len == 21 &&
               addr_raw[0] == (CASHADDR_P2SH | CASHADDR_160)) {
      script_pubkey[0] = 0xA9;  // OP_HASH_160
      script_pubkey[1] = 0x14;  // pushing 20 bytes
      memcpy(script_pubkey + 2, addr_raw + 1, 20);
      script_pubkey[22] = 0x87;  // OP_EQUAL
      *size = 23;
      return 1;
    } else {
      return 0;
    }
  }
#endif

  // SegWit
  if (coin->bech32_prefix) {
    int witver = 0;
    if (!segwit_addr_decode(&witver, addr_raw, &addr_raw_len,
                            coin->bech32_prefix, address)) {
      return 0;
    }
    // check that the witness version is recognized
    if (witver != 0 && witver != 1) {
      return 0;
    }
    // check that P2TR address encodes a valid BIP340 public key
    if (witver == 1) {
      if (addr_raw_len != 32 || zkp_bip340_verify_publickey(addr_raw) != 0) {
        return 0;
      }
    }
    // push 1 byte version id (opcode OP_0 = 0, OP_i = 80+i)
    // push addr_raw (segwit_addr_decode makes sure addr_raw_len is at most 40)
    script_pubkey[0] = witver == 0 ? 0 : 80 + witver;
    script_pubkey[1] = addr_raw_len;
    memcpy(script_pubkey + 2, addr_raw, addr_raw_len);
    *size = addr_raw_len + 2;
    return 1;
  }

  return 0;
}

void op_return_to_script_pubkey(const uint8_t *op_return_data,
                                size_t op_return_size, uint8_t *script_pubkey,
                                pb_size_t *script_pubkey_size) {
  uint32_t r = 0;
  script_pubkey[0] = 0x6A;
  r++;  // OP_RETURN
  r += op_push(op_return_size, script_pubkey + r);
  memcpy(script_pubkey + r, op_return_data, op_return_size);
  r += op_return_size;
  *script_pubkey_size = r;
}

bool get_script_pubkey(const CoinInfo *coin, HDNode *node, bool has_multisig,
                       const MultisigRedeemScriptType *multisig,
                       InputScriptType script_type, uint8_t *script_pubkey,
                       pb_size_t *script_pubkey_size) {
  char address[MAX_ADDR_SIZE] = {0};
  bool res = true;
  res = res && (hdnode_fill_public_key(node) == 0);
  res = res && compute_address(coin, script_type, node, has_multisig, multisig,
                               address);
  res = res && address_to_script_pubkey(coin, address, script_pubkey,
                                        script_pubkey_size);
  return res;
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

  uint8_t pubkeys[33 * n];
  if (!cryptoMultisigPubkeys(coin, multisig, pubkeys)) {
    return 0;
  }

  uint32_t r = 0;
  if (out) {
    out[r] = 0x50 + m;
    r++;
    for (uint32_t i = 0; i < n; i++) {
      out[r] = 33;
      r++;  // OP_PUSH 33
      memcpy(out + r, pubkeys + 33 * i, 33);
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

  // allocate on stack instead of heap
  uint8_t pubkeys[33 * n];
  if (!cryptoMultisigPubkeys(coin, multisig, pubkeys)) {
    return 0;
  }

  Hasher hasher = {0};
  hasher_Init(&hasher, coin->curve->hasher_script);

  uint8_t d[2] = {0};
  d[0] = 0x50 + m;
  hasher_Update(&hasher, d, 1);
  for (uint32_t i = 0; i < n; i++) {
    d[0] = 33;
    hasher_Update(&hasher, d, 1);  // OP_PUSH 33
    hasher_Update(&hasher, pubkeys + 33 * i, 33);
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

uint32_t serialize_p2wpkh_witness(const uint8_t *signature,
                                  uint32_t signature_len,
                                  const uint8_t *public_key,
                                  uint32_t public_key_len, uint8_t sighash,
                                  uint8_t *out) {
  uint32_t r = 0;

  // 2 stack items
  r += ser_length(2, out + r);

  // length-prefixed signature with sighash type
  r += ser_length(signature_len + 1, out + r);
  memcpy(out + r, signature, signature_len);
  r += signature_len;
  out[r] = sighash;
  r += 1;

  // length-prefixed public key
  r += tx_serialize_script(public_key_len, public_key, out + r);
  return r;
}

uint32_t serialize_p2tr_witness(const uint8_t *signature,
                                uint32_t signature_len, uint8_t sighash,
                                uint8_t *out) {
  uint32_t r = 0;

  // 1 stack item
  r += ser_length(1, out + r);

  // length-prefixed signature with optional sighash type
  uint32_t sighash_len = sighash ? 1 : 0;
  r += ser_length(signature_len + sighash_len, out + r);
  memcpy(out + r, signature, signature_len);
  r += signature_len;
  if (sighash) {
    out[r] = sighash;
    r += 1;
  }

  return r;
}

bool tx_sign_ecdsa(const ecdsa_curve *curve, const uint8_t *private_key,
                   const uint8_t *hash, uint8_t *out, pb_size_t *size) {
  uint8_t signature[64] = {0};
  if (ecdsa_sign_digest(curve, private_key, hash, signature, NULL, NULL) != 0) {
    return false;
  }

  *size = ecdsa_sig_to_der(signature, out);
  return true;
}

bool tx_sign_bip340(const uint8_t *private_key, const uint8_t *hash,
                    uint8_t *out, pb_size_t *size) {
  static CONFIDENTIAL uint8_t output_private_key[32] = {0};
  bool ret = (zkp_bip340_tweak_private_key(private_key, NULL,
                                           output_private_key) == 0);
  ret =
      ret && (zkp_bip340_sign_digest(output_private_key, hash, out, NULL) == 0);
  *size = ret ? 64 : 0;
  memzero(output_private_key, sizeof(output_private_key));
  return ret;
}

// tx methods
bool tx_input_check_hash(Hasher *hasher, const TxInputType *input) {
  hasher_Update(hasher, (const uint8_t *)&input->address_n_count,
                sizeof(input->address_n_count));
  for (int i = 0; i < input->address_n_count; ++i)
    hasher_Update(hasher, (const uint8_t *)&input->address_n[i],
                  sizeof(input->address_n[0]));
  hasher_Update(hasher, input->prev_hash.bytes, sizeof(input->prev_hash.bytes));
  hasher_Update(hasher, (const uint8_t *)&input->prev_index,
                sizeof(input->prev_index));
  tx_script_hash(hasher, input->script_sig.size, input->script_sig.bytes);
  hasher_Update(hasher, (const uint8_t *)&input->sequence,
                sizeof(input->sequence));
  hasher_Update(hasher, (const uint8_t *)&input->script_type,
                sizeof(input->script_type));
  uint8_t multisig_fp[32] = {0};
  if (input->has_multisig) {
    if (cryptoMultisigFingerprint(&input->multisig, multisig_fp) == 0) {
      // Invalid multisig parameters.
      return false;
    }
  }
  hasher_Update(hasher, multisig_fp, sizeof(multisig_fp));
  hasher_Update(hasher, (const uint8_t *)&input->amount, sizeof(input->amount));
  tx_script_hash(hasher, input->witness.size, input->witness.bytes);
  hasher_Update(hasher, (const uint8_t *)&input->has_orig_hash,
                sizeof(input->has_orig_hash));
  hasher_Update(hasher, input->orig_hash.bytes, sizeof(input->orig_hash.bytes));
  hasher_Update(hasher, (const uint8_t *)&input->orig_index,
                sizeof(input->orig_index));
  tx_script_hash(hasher, input->script_pubkey.size, input->script_pubkey.bytes);
  return true;
}

uint32_t tx_prevout_hash(Hasher *hasher, const TxInputType *input) {
  for (int i = 0; i < 32; i++) {
    hasher_Update(hasher, &(input->prev_hash.bytes[31 - i]), 1);
  }
  hasher_Update(hasher, (const uint8_t *)&input->prev_index, 4);
  return 36;
}

uint32_t tx_amount_hash(Hasher *hasher, const TxInputType *input) {
  hasher_Update(hasher, (const uint8_t *)&input->amount, 8);
  return 8;
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
  int r = 0;
#if !BITCOIN_ONLY
  if (tx->is_zcashlike && tx->version >= 3) {
    uint32_t ver = tx->version | TX_OVERWINTERED;
    memcpy(out + r, &ver, 4);
    r += 4;
    memcpy(out + r, &(tx->version_group_id), 4);
    r += 4;
    if (tx->version == 5) {
      memcpy(out + r, &(tx->branch_id), 4);
      r += 4;
      memcpy(out + r, &(tx->lock_time), 4);
      r += 4;
      memcpy(out + r, &(tx->expiry), 4);
      r += 4;
    }
  } else
#endif
  {
    memcpy(out + r, &(tx->version), 4);
    r += 4;
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
  uint32_t r = 0;
#if !BITCOIN_ONLY
  if (tx->is_zcashlike) {
    if (tx->version == 4) {
      memcpy(out, &(tx->lock_time), 4);
      r += 4;
      memcpy(out + r, &(tx->expiry), 4);
      r += 4;
      memzero(out + r, 8);  // valueBalance
      r += 8;
      out[r] = 0x00;  // nShieldedSpend
      r += 1;
      out[r] = 0x00;  // nShieldedOutput
      r += 1;
      out[r] = 0x00;  // nJoinSplit
      r += 1;
    } else if (tx->version == 5) {
      out[r] = 0x00;  // nSpendsSapling
      r += 1;
      out[r] = 0x00;  // nOutputsSapling
      r += 1;
      out[r] = 0x00;  // nActionsOrchard
      r += 1;
    }
  } else if (tx->is_decred) {
    memcpy(out, &(tx->lock_time), 4);
    r += 4;
    memcpy(out + r, &(tx->expiry), 4);
    r += 4;
  } else
#endif
  {
    memcpy(out, &(tx->lock_time), 4);
    r += 4;
  }
  return r;
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
             uint32_t branch_id, uint32_t extra_data_len,
             HasherType hasher_sign, bool is_zcashlike,
             uint32_t version_group_id, uint32_t timestamp) {
  tx->inputs_len = inputs_len;
  tx->outputs_len = outputs_len;
  tx->version = version;
  tx->lock_time = lock_time;
  tx->expiry = expiry;
  tx->branch_id = branch_id;
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

static uint32_t tx_input_script_size(const TxInputType *txinput,
                                     InputScriptType script_type) {
  uint32_t input_script_size = 0;
  if (txinput->has_multisig) {
    uint32_t multisig_script_size =
        TXSIZE_MULTISIGSCRIPT +
        cryptoMultisigPubkeyCount(&(txinput->multisig)) * (1 + TXSIZE_PUBKEY);
    if (script_type == InputScriptType_SPENDWITNESS ||
        script_type == InputScriptType_SPENDP2SHWITNESS) {
      multisig_script_size += ser_length_size(multisig_script_size);
    } else {
      multisig_script_size += op_push_size(multisig_script_size);
    }
    input_script_size = 1  // the OP_FALSE bug in multisig
                        + txinput->multisig.m * (1 + TXSIZE_DER_SIGNATURE) +
                        multisig_script_size;
  } else if (script_type == InputScriptType_SPENDTAPROOT) {
    input_script_size = 1 + TXSIZE_SCHNORR_SIGNATURE;
  } else {
    input_script_size = (1 + TXSIZE_DER_SIGNATURE + 1 + TXSIZE_PUBKEY);
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

  InputScriptType script_type = txinput->script_type;
  if (script_type == InputScriptType_EXTERNAL) {
    // Guess the script type from the scriptPubKey.
    switch (txinput->script_pubkey.bytes[0]) {
      case 0x76:  // OP_DUP (P2PKH)
        script_type = InputScriptType_SPENDADDRESS;
        break;
      case 0xA9:  // OP_HASH_160 (P2SH, probably nested P2WPKH)
        script_type = InputScriptType_SPENDP2SHWITNESS;
        break;
      case 0x00:  // SegWit v0 (probably P2WPKH)
        script_type = InputScriptType_SPENDWITNESS;
        break;
      case 0x51:  // SegWit v1 (P2TR)
        script_type = InputScriptType_SPENDTAPROOT;
        break;
      default:  // Unknown script type.
        break;
    }
  }

  uint32_t input_script_size = tx_input_script_size(txinput, script_type);
  uint32_t weight = 4 * TXSIZE_INPUT;
  if (script_type == InputScriptType_SPENDADDRESS ||
      script_type == InputScriptType_SPENDMULTISIG) {
    input_script_size += ser_length_size(input_script_size);
    weight += 4 * input_script_size;
  } else if (script_type == InputScriptType_SPENDWITNESS ||
             script_type == InputScriptType_SPENDTAPROOT ||
             script_type == InputScriptType_SPENDP2SHWITNESS) {
    if (script_type == InputScriptType_SPENDP2SHWITNESS) {
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
#if !BITCOIN_ONLY
    if (coin->cashaddr_prefix &&
        cash_addr_decode(addr_raw, &addr_raw_len, coin->cashaddr_prefix,
                         txoutput->address)) {
      if (addr_raw_len == 21 && addr_raw[0] == (CASHADDR_P2KH | CASHADDR_160)) {
        output_script_size = TXSIZE_P2PKHASH;
      } else if (addr_raw_len == 21 &&
                 addr_raw[0] == (CASHADDR_P2SH | CASHADDR_160)) {
        output_script_size = TXSIZE_P2SCRIPT;
      }
    } else
#endif
    {
      if (coin->bech32_prefix &&
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
  uint32_t input_script_size =
      tx_input_script_size(txinput, txinput->script_type);
  if (txinput->script_type == InputScriptType_SPENDMULTISIG) {
    // Decred fixed the the OP_FALSE bug in multisig.
    input_script_size -= 1;  // Subtract one OP_FALSE byte.
  }
  uint32_t size = TXSIZE_DECRED_WITNESS + ser_length_size(input_script_size) +
                  input_script_size;

  return 4 * size;
}
#endif

bool get_ownership_proof(const CoinInfo *coin, InputScriptType script_type,
                         const HDNode *node, uint8_t flags,
                         const uint8_t ownership_id[OWNERSHIP_ID_SIZE],
                         const uint8_t *script_pubkey,
                         size_t script_pubkey_size,
                         const uint8_t *commitment_data,
                         size_t commitment_data_size, OwnershipProof *out) {
  size_t r = 0;

  // Write versionMagic (4 bytes).
  memcpy(out->ownership_proof.bytes + r, SLIP19_VERSION_MAGIC,
         sizeof(SLIP19_VERSION_MAGIC));
  r += sizeof(SLIP19_VERSION_MAGIC);

  // Write flags (1 byte).
  out->ownership_proof.bytes[r] = flags;
  r += 1;

  // Write number of ownership IDs (1 byte).
  r += ser_length(1, out->ownership_proof.bytes + r);

  // Write ownership ID (32 bytes).
  memcpy(out->ownership_proof.bytes + r, ownership_id, OWNERSHIP_ID_SIZE);
  r += OWNERSHIP_ID_SIZE;

  // Compute sighash = SHA-256(proofBody || proofFooter).
  Hasher hasher = {0};
  uint8_t sighash[SHA256_DIGEST_LENGTH] = {0};
  hasher_InitParam(&hasher, HASHER_SHA2, NULL, 0);
  hasher_Update(&hasher, out->ownership_proof.bytes, r);
  tx_script_hash(&hasher, script_pubkey_size, script_pubkey);
  tx_script_hash(&hasher, commitment_data_size, commitment_data);
  hasher_Final(&hasher, sighash);

  // Write proofSignature.
  if (script_type == InputScriptType_SPENDWITNESS) {
    if (!tx_sign_ecdsa(coin->curve->params, node->private_key, sighash,
                       out->signature.bytes, &out->signature.size)) {
      return false;
    }
    // Write length-prefixed empty scriptSig (1 byte).
    r += ser_length(0, out->ownership_proof.bytes + r);

    // Write
    // 1. number of stack items (1 byte)
    // 2. signature + sighash type length (1 byte)
    // 3. DER-encoded signature (max. 71 bytes)
    // 4. sighash type (1 byte)
    // 5. public key length (1 byte)
    // 6. public key (33 bytes)
    r += serialize_p2wpkh_witness(out->signature.bytes, out->signature.size,
                                  node->public_key, 33, SIGHASH_ALL,
                                  out->ownership_proof.bytes + r);
  } else if (script_type == InputScriptType_SPENDTAPROOT) {
    if (!tx_sign_bip340(node->private_key, sighash, out->signature.bytes,
                        &out->signature.size)) {
      return false;
    }
    // Write length-prefixed empty scriptSig (1 byte).
    r += ser_length(0, out->ownership_proof.bytes + r);

    // Write
    // 1. number of stack items (1 byte)
    // 2. signature length (1 byte)
    // 3. signature (64 bytes)
    r += serialize_p2tr_witness(out->signature.bytes, out->signature.size, 0,
                                out->ownership_proof.bytes + r);
  } else {
    return false;
  }

  out->ownership_proof.size = r;
  return true;
}

bool tx_input_verify_nonownership(
    const CoinInfo *coin, const TxInputType *txinput,
    const uint8_t ownership_id[OWNERSHIP_ID_SIZE]) {
  size_t r = 0;
  // Check versionMagic.
  if (txinput->ownership_proof.size < r + sizeof(SLIP19_VERSION_MAGIC) ||
      memcmp(txinput->ownership_proof.bytes + r, SLIP19_VERSION_MAGIC,
             sizeof(SLIP19_VERSION_MAGIC)) != 0) {
    return false;
  }
  r += sizeof(SLIP19_VERSION_MAGIC);

  // Skip flags.
  r += 1;

  // Ensure that there is only one ownership ID.
  if (txinput->ownership_proof.size < r + 1 ||
      txinput->ownership_proof.bytes[r] != 1) {
    return false;
  }
  r += 1;

  // Ensure that the ownership ID is not ours.
  if (txinput->ownership_proof.size < r + OWNERSHIP_ID_SIZE ||
      memcmp(txinput->ownership_proof.bytes + r, ownership_id,
             OWNERSHIP_ID_SIZE) == 0) {
    return false;
  }
  r += OWNERSHIP_ID_SIZE;

  // Compute the ownership proof digest.
  Hasher hasher = {0};
  hasher_InitParam(&hasher, HASHER_SHA2, NULL, 0);
  hasher_Update(&hasher, txinput->ownership_proof.bytes, r);
  tx_script_hash(&hasher, txinput->script_pubkey.size,
                 txinput->script_pubkey.bytes);
  tx_script_hash(&hasher, txinput->commitment_data.size,
                 txinput->commitment_data.bytes);
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  hasher_Final(&hasher, digest);

  // Ensure that there is no scriptSig, since we only support native SegWit
  // ownership proofs.
  if (txinput->ownership_proof.size < r + 1 ||
      txinput->ownership_proof.bytes[r] != 0) {
    return false;
  }
  r += 1;

  if (txinput->script_pubkey.size == 22 &&
      memcmp(txinput->script_pubkey.bytes, "\x00\x14", 2) == 0) {
    // SegWit v0 (probably P2WPKH)
    const uint8_t *pubkey_hash = txinput->script_pubkey.bytes + 2;

    // Ensure that there are two stack items.
    if (txinput->ownership_proof.size < r + 1 ||
        txinput->ownership_proof.bytes[r] != 2) {
      return false;
    }
    r += 1;

    // Read the signature.
    if (txinput->ownership_proof.size < r + 1) {
      return false;
    }
    size_t signature_size = txinput->ownership_proof.bytes[r];
    r += 1;

    uint8_t signature[64] = {0};
    if (txinput->ownership_proof.size < r + signature_size ||
        ecdsa_sig_from_der(txinput->ownership_proof.bytes + r,
                           signature_size - 1, signature) != 0) {
      return false;
    }
    r += signature_size;

    // Read the public key.
    if (txinput->ownership_proof.size < r + 34 ||
        txinput->ownership_proof.bytes[r] != 33) {
      return false;
    }
    const uint8_t *public_key = txinput->ownership_proof.bytes + r + 1;
    r += 34;

    // Check the public key matches the scriptPubKey.
    uint8_t expected_pubkey_hash[20] = {0};
    ecdsa_get_pubkeyhash(public_key, coin->curve->hasher_pubkey,
                         expected_pubkey_hash);
    if (memcmp(pubkey_hash, expected_pubkey_hash,
               sizeof(expected_pubkey_hash)) != 0) {
      return false;
    }

    // Ensure that we have read the entire ownership proof.
    if (r != txinput->ownership_proof.size) {
      return false;
    }

    if (ecdsa_verify_digest(coin->curve->params, public_key, signature,
                            digest) != 0) {
      return false;
    }
  } else if (txinput->script_pubkey.size == 34 &&
             memcmp(txinput->script_pubkey.bytes, "\x51\x20", 2) == 0) {
    // SegWit v1 (P2TR)
    const uint8_t *output_public_key = txinput->script_pubkey.bytes + 2;

    // Ensure that there is one stack item consisting of 64 bytes.
    if (txinput->ownership_proof.size < r + 2 ||
        memcmp(txinput->ownership_proof.bytes + r, "\x01\x40", 2) != 0) {
      return false;
    }
    r += 2;

    // Read the signature.
    const uint8_t *signature = txinput->ownership_proof.bytes + r;
    r += 64;

    // Ensure that we have read the entire ownership proof.
    if (r != txinput->ownership_proof.size) {
      return false;
    }

    if (zkp_bip340_verify_digest(output_public_key, signature, digest) != 0) {
      return false;
    }
  } else {
    // Unsupported script type.
    return false;
  }

  return true;
}
