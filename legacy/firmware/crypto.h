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

#ifndef __CRYPTO_H__
#define __CRYPTO_H__

#include <bip32.h>
#include <ecdsa.h>
#include <pb.h>
#include <sha2.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include "coins.h"
#include "hasher.h"
#include "messages-bitcoin.pb.h"
#include "messages-crypto.pb.h"

#define PATH_HARDENED 0x80000000
#define PATH_UNHARDEN_MASK 0x7fffffff
#define PATH_MAX_ACCOUNT 100
#define PATH_MAX_CHANGE 1
// The maximum allowed change address.  This should be large enough for normal
// use and still allow to quickly brute-force the correct bip32 path.
#define PATH_MAX_ADDRESS_INDEX 1000000
#define PATH_SLIP25_PURPOSE (PATH_HARDENED | 10025)

// The number of bip32 levels used in a wallet (chain and address)
#define BIP32_WALLET_DEPTH 2

#define ser_length_size(len) ((len) < 253 ? 1 : (len) < 0x10000 ? 3 : 5)

typedef enum {
  SCHEMA_NONE,
  SCHEMA_SLIP25_TAPROOT,
  SCHEMA_SLIP25_TAPROOT_EXTERNAL
} PathSchema;

typedef struct {
  uint8_t data[64];
} Slip21Node;

uint32_t ser_length(uint32_t len, uint8_t *out);

uint32_t ser_length_hash(Hasher *hasher, uint32_t len);

int sshMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                   uint8_t *signature);

int gpgMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                   uint8_t *signature);

int signifyMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                       uint8_t *signature);

int cryptoMessageSign(const CoinInfo *coin, HDNode *node,
                      InputScriptType script_type, bool no_script_type,
                      const uint8_t *message, size_t message_len,
                      uint8_t *signature);

int cryptoMessageVerify(const CoinInfo *coin, const uint8_t *message,
                        size_t message_len, const char *address,
                        const uint8_t *signature);

const HDNode *cryptoMultisigPubkey(const CoinInfo *coin,
                                   const MultisigRedeemScriptType *multisig,
                                   uint32_t index);

uint32_t cryptoMultisigPubkeyCount(const MultisigRedeemScriptType *multisig);

int cryptoMultisigPubkeyIndex(const CoinInfo *coin,
                              const MultisigRedeemScriptType *multisig,
                              const uint8_t *pubkey);

int cryptoMultisigXpubIndex(const CoinInfo *coin,
                            const MultisigRedeemScriptType *multisig,
                            const uint8_t *pubkey);

uint32_t cryptoMultisigPubkeys(const CoinInfo *coin,
                               const MultisigRedeemScriptType *multisig,
                               uint8_t *pubkeys);

int cryptoMultisigFingerprint(const MultisigRedeemScriptType *multisig,
                              uint8_t *hash);

int cryptoIdentityFingerprint(const IdentityType *identity, uint8_t *hash);

bool cryptoCosiVerify(const ed25519_signature signature, const uint8_t *message,
                      const size_t message_len, const int threshold,
                      const ed25519_public_key *pubkeys,
                      const int pubkeys_count, const uint8_t sigmask);

bool coin_path_check(const CoinInfo *coin, InputScriptType script_type,
                     uint32_t address_n_count, const uint32_t *address_n,
                     bool has_multisig, PathSchema unlock, bool full_check);

bool is_multisig_input_script_type(InputScriptType script_type);
bool is_multisig_output_script_type(OutputScriptType script_type);
bool is_internal_input_script_type(InputScriptType script_type);
bool is_change_output_script_type(OutputScriptType script_type);
bool is_segwit_input_script_type(InputScriptType script_type);
bool is_segwit_output_script_type(OutputScriptType script_type);
bool change_output_to_input_script_type(OutputScriptType output_script_type,
                                        InputScriptType *input_script_type);

void slip21_from_seed(const uint8_t *seed, int seed_len, Slip21Node *out);
void slip21_derive_path(Slip21Node *inout, const uint8_t *label,
                        size_t label_len);
const uint8_t *slip21_key(const Slip21Node *node);
bool multisig_uses_single_path(const MultisigRedeemScriptType *multisig);

#endif
