/*
 * This file is part of the TREZOR project.
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
#include "sha2.h"
#include "bip32.h"
#include "types.pb.h"

typedef struct {
	uint32_t inputs_len;
	uint32_t outputs_len;

	uint32_t version;
	uint32_t lock_time;
	bool add_hash_type;

	uint32_t have_inputs;
	uint32_t have_outputs;

	uint32_t extra_data_len;
	uint32_t extra_data_received;

	uint32_t size;

	SHA256_CTX ctx;
} TxStruct;

uint32_t compile_script_sig(uint32_t address_type, const uint8_t *pubkeyhash, uint8_t *out);
uint32_t compile_script_multisig(const MultisigRedeemScriptType *multisig, uint8_t *out);
uint32_t compile_script_multisig_hash(const MultisigRedeemScriptType *multisig, uint8_t *hash);
uint32_t serialize_script_sig(const uint8_t *signature, uint32_t signature_len, const uint8_t *pubkey, uint32_t pubkey_len, uint8_t *out);
uint32_t serialize_script_multisig(const MultisigRedeemScriptType *multisig, uint8_t *out);
int compile_output(const CoinType *coin, const HDNode *root, TxOutputType *in, TxOutputBinType *out, bool needs_confirm);
uint32_t tx_serialize_input(TxStruct *tx, const TxInputType *input, uint8_t *out);
uint32_t tx_serialize_output(TxStruct *tx, const TxOutputBinType *output, uint8_t *out);

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len, uint32_t version, uint32_t lock_time, uint32_t extra_data_len, bool add_hash_type);
uint32_t tx_serialize_header_hash(TxStruct *tx);
uint32_t tx_serialize_input_hash(TxStruct *tx, const TxInputType *input);
uint32_t tx_serialize_output_hash(TxStruct *tx, const TxOutputBinType *output);
uint32_t tx_serialize_extra_data_hash(TxStruct *tx, const uint8_t *data, uint32_t datalen);
void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse);

uint32_t transactionEstimateSize(uint32_t inputs, uint32_t outputs);

uint32_t transactionEstimateSizeKb(uint32_t inputs, uint32_t outputs);

#endif
