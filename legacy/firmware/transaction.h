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

#ifndef __TRANSACTION_H__
#define __TRANSACTION_H__

#include <stdbool.h>
#include <stdint.h>
#include "bip32.h"
#include "coins.h"
#include "hasher.h"
#include "messages-bitcoin.pb.h"
#include "sha2.h"

#define TX_OVERWINTERED 0x80000000

#define OWNERSHIP_ID_SIZE 32

enum {
  // Signature hash type with the same semantics as SIGHASH_ALL, but instead of
  // having to include the byte in the signature, it is implied.
  SIGHASH_ALL_TAPROOT = 0,

  // Default signature hash type in Bitcoin which signs all inputs and all
  // outputs of the transaction.
  SIGHASH_ALL = 1,

  // Signature hash flag used in some Bitcoin-like altcoins for replay
  // protection.
  SIGHASH_FORKID = 0x40,
};

typedef struct {
  uint32_t inputs_len;
  uint32_t outputs_len;

  uint32_t version;
  uint32_t version_group_id;
  uint32_t timestamp;
  uint32_t lock_time;
  uint32_t expiry;
  uint32_t branch_id;
  bool is_segwit;
  bool is_decred;
  bool is_zcashlike;

  uint32_t have_inputs;
  uint32_t have_outputs;

  uint32_t extra_data_len;
  uint32_t extra_data_received;

  uint32_t size;

  Hasher hasher;
} TxStruct;

bool compute_address(const CoinInfo *coin, InputScriptType script_type,
                     const HDNode *node, bool has_multisig,
                     const MultisigRedeemScriptType *multisig,
                     char address[MAX_ADDR_SIZE]);
int address_to_script_pubkey(const CoinInfo *coin, const char *address,
                             uint8_t *script_pubkey, pb_size_t *size);
uint32_t compile_script_sig(uint32_t address_type, const uint8_t *pubkeyhash,
                            uint8_t *out);
uint32_t compile_script_multisig(const CoinInfo *coin,
                                 const MultisigRedeemScriptType *multisig,
                                 uint8_t *out);
uint32_t compile_script_multisig_hash(const CoinInfo *coin,
                                      const MultisigRedeemScriptType *multisig,
                                      uint8_t *hash);
uint32_t serialize_script_sig(const uint8_t *signature, uint32_t signature_len,
                              const uint8_t *pubkey, uint32_t pubkey_len,
                              uint8_t sighash, uint8_t *out);
uint32_t serialize_script_multisig(const CoinInfo *coin,
                                   const MultisigRedeemScriptType *multisig,
                                   uint8_t sighash, uint8_t *out);
uint32_t serialize_p2wpkh_witness(const uint8_t *signature,
                                  uint32_t signature_len,
                                  const uint8_t *public_key,
                                  uint32_t public_key_len, uint8_t sighash,
                                  uint8_t *out);
uint32_t serialize_p2tr_witness(const uint8_t *signature,
                                uint32_t signature_len, uint8_t sighash,
                                uint8_t *out);
bool tx_sign_ecdsa(const ecdsa_curve *curve, const uint8_t *private_key,
                   const uint8_t *hash, uint8_t *out, pb_size_t *size);
bool tx_sign_bip340(const uint8_t *private_key, const uint8_t *hash,
                    uint8_t *out, pb_size_t *size);
void op_return_to_script_pubkey(const uint8_t *op_return_data,
                                size_t op_return_size, uint8_t *script_pubkey,
                                pb_size_t *script_pubkey_size);
bool get_script_pubkey(const CoinInfo *coin, HDNode *node, bool has_multisig,
                       const MultisigRedeemScriptType *multisig,
                       InputScriptType script_type, uint8_t *script_pubkey,
                       pb_size_t *script_pubkey_size);

bool tx_input_check_hash(Hasher *hasher, const TxInputType *input);
uint32_t tx_prevout_hash(Hasher *hasher, const TxInputType *input);
uint32_t tx_amount_hash(Hasher *hasher, const TxInputType *input);
uint32_t tx_script_hash(Hasher *hasher, uint32_t size, const uint8_t *data);
uint32_t tx_sequence_hash(Hasher *hasher, const TxInputType *input);
uint32_t tx_output_hash(Hasher *hasher, const TxOutputBinType *output,
                        bool decred);
uint32_t tx_serialize_script(uint32_t size, const uint8_t *data, uint8_t *out);

uint32_t tx_serialize_footer(TxStruct *tx, uint8_t *out);
uint32_t tx_serialize_input(TxStruct *tx, const TxInputType *input,
                            uint8_t *out);
uint32_t tx_serialize_output(TxStruct *tx, const TxOutputBinType *output,
                             uint8_t *out);
uint32_t tx_serialize_decred_witness(TxStruct *tx, const TxInputType *input,
                                     uint8_t *out);

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len,
             uint32_t version, uint32_t lock_time, uint32_t expiry,
             uint32_t branch_id, uint32_t extra_data_len,
             HasherType hasher_sign, bool is_zcashlike,
             uint32_t version_group_id, uint32_t timestamp);
uint32_t tx_serialize_header_hash(TxStruct *tx);
uint32_t tx_serialize_input_hash(TxStruct *tx, const TxInputType *input);
uint32_t tx_serialize_output_hash(TxStruct *tx, const TxOutputBinType *output);
uint32_t tx_serialize_extra_data_hash(TxStruct *tx, const uint8_t *data,
                                      uint32_t datalen);
uint32_t tx_serialize_decred_witness_hash(TxStruct *tx,
                                          const TxInputType *input);
void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse);

uint32_t tx_input_weight(const CoinInfo *coin, const TxInputType *txinput);
uint32_t tx_output_weight(const CoinInfo *coin, const TxOutputType *txoutput);
uint32_t tx_decred_witness_weight(const TxInputType *txinput);
bool get_ownership_proof(const CoinInfo *coin, InputScriptType script_type,
                         const HDNode *node, uint8_t flags,
                         const uint8_t ownership_id[OWNERSHIP_ID_SIZE],
                         const uint8_t *script_pubkey,
                         size_t script_pubkey_size,
                         const uint8_t *commitment_data,
                         size_t commitment_data_size, OwnershipProof *out);
bool tx_input_verify_nonownership(
    const CoinInfo *coin, const TxInputType *txinput,
    const uint8_t ownership_id[OWNERSHIP_ID_SIZE]);

#endif
