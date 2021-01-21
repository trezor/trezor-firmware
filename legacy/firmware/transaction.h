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

typedef struct {
  uint32_t inputs_len;
  uint32_t outputs_len;

  uint32_t version;
  uint32_t version_group_id;
  uint32_t timestamp;
  uint32_t lock_time;
  uint32_t expiry;
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
int compile_output(const CoinInfo *coin, AmountUnit amount_unit,
                   const HDNode *root, TxOutputType *in, TxOutputBinType *out,
                   bool needs_confirm);

void tx_input_check_hash(Hasher *hasher, const TxInputType *input);
uint32_t tx_prevout_hash(Hasher *hasher, const TxInputType *input);
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
             uint32_t extra_data_len, HasherType hasher_sign, bool is_zcashlike,
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

#endif
