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
	uint32_t size;

	SHA256_CTX ctx;
} TxStruct;

uint32_t compile_script_sig(uint8_t address_type, const uint8_t *pubkeyhash, uint8_t *out);
int serialize_script_sig(uint8_t *signature, uint32_t signature_len, uint8_t *pubkey, uint32_t pubkey_len, uint8_t *out);
int compile_output(const CoinType *coin, const HDNode *root, TxOutputType *in, TxOutputBinType *out, bool needs_confirm);
uint32_t tx_serialize_input(TxStruct *tx, uint8_t *prev_hash, uint32_t prev_index, uint8_t *script_sig, uint32_t script_sig_len, uint32_t sequence, uint8_t *out);
uint32_t tx_serialize_output(TxStruct *tx, uint64_t amount, uint8_t *script_pubkey, uint32_t script_pubkey_len, uint8_t *out);

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len, uint32_t version, uint32_t lock_time, bool add_hash_type);
bool tx_hash_input(TxStruct *t, TxInputType *input);
bool tx_hash_output(TxStruct *t, TxOutputBinType *output);
void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse);

bool transactionHash(TransactionType *tx, uint8_t *hash);

int transactionSimpleSign(const CoinType *coin, HDNode *root, TxInputType *inputs, uint32_t inputs_count, TxOutputType *outputs, uint32_t outputs_count, uint32_t version, uint32_t lock_time, uint8_t *out);

uint32_t transactionEstimateSize(uint32_t inputs, uint32_t outputs);

uint32_t transactionEstimateSizeKb(uint32_t inputs, uint32_t outputs);

bool transactionMessageSign(uint8_t *message, uint32_t message_len, uint8_t *privkey, const char *address, uint8_t *signature);

bool transactionMessageVerify(uint8_t *message, uint32_t message_len, uint8_t *signature, const char *address);

#endif
