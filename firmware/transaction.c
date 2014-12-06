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

#include <string.h>
#include "transaction.h"
#include "ecdsa.h"
#include "coins.h"
#include "util.h"
#include "debug.h"
#include "protect.h"
#include "layout2.h"
#include "crypto.h"
#include "messages.pb.h"

uint32_t op_push(uint32_t i, uint8_t *out) {
	if (i < 0x4C) {
		out[0] = i & 0xFF;
		return 1;
	}
	if (i < 0xFF) {
		out[0] = 0x4C;
		out[1] = i & 0xFF;
		return 2;
	}
	if (i < 0xFFFF) {
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

int compile_output(const CoinType *coin, const HDNode *root, TxOutputType *in, TxOutputBinType *out, bool needs_confirm)
{
	// address_n provided-> change address -> calculate from address_n
	if (in->address_n_count > 0) {
		HDNode node;
		uint32_t k;
		memcpy(&node, root, sizeof(HDNode));
		for (k = 0; k < in->address_n_count; k++) {
			hdnode_private_ckd(&node, in->address_n[k]);
		}
		ecdsa_get_address(node.public_key, coin->address_type, in->address);
	} else
	if (in->has_address) { // address provided -> regular output
		if (needs_confirm) {
			layoutConfirmOutput(coin, in);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
				return -1;
			}
		}
	} else { // does not have address_n neither address
		return 0;
	}

	memset(out, 0, sizeof(TxOutputBinType));
	out->amount = in->amount;

	if (in->script_type == OutputScriptType_PAYTOADDRESS) {
		out->script_pubkey.bytes[0] = 0x76; // OP_DUP
		out->script_pubkey.bytes[1] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[2] = 0x14; // pushing 20 bytes
		uint8_t decoded[21];
		if (!ecdsa_address_decode(in->address, decoded)) {
			return 0;
		}
		if (decoded[0] != coin->address_type) {
			return 0;
		}
		memcpy(out->script_pubkey.bytes + 3, decoded + 1, 20);
		out->script_pubkey.bytes[23] = 0x88; // OP_EQUALVERIFY
		out->script_pubkey.bytes[24] = 0xAC; // OP_CHECKSIG
		out->script_pubkey.size = 25;
		return 25;
	}

	if (in->script_type == OutputScriptType_PAYTOSCRIPTHASH) {
		out->script_pubkey.bytes[0] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[1] = 0x14; // pushing 20 bytes
		uint8_t decoded[21];
		if (!ecdsa_address_decode(in->address, decoded)) {
			return 0;
		}
		if (decoded[0] != 0x05) { // 0x05 is P2SH
			return 0;
		}
		memcpy(out->script_pubkey.bytes + 2, decoded + 1, 20);
		out->script_pubkey.bytes[22] = 0x87; // OP_EQUAL
		out->script_pubkey.size = 23;
		return 23;
	}

	return 0;
}

uint32_t compile_script_sig(uint8_t address_type, const uint8_t *pubkeyhash, uint8_t *out)
{
	if (coinByAddressType(address_type)) { // valid coin type
		out[0] = 0x76; // OP_DUP
		out[1] = 0xA9; // OP_HASH_160
		out[2] = 0x14; // pushing 20 bytes
		memcpy(out + 3, pubkeyhash, 20);
		out[23] = 0x88; // OP_EQUALVERIFY
		out[24] = 0xAC; // OP_CHECKSIG
		return 25;
	} else {
		return 0; // unsupported
	}
}

// if out == NULL just compute the length
uint32_t compile_script_multisig(const MultisigRedeemScriptType *multisig, uint8_t *out)
{
	if (!multisig->has_m) return 0;
	uint32_t m = multisig->m;
	uint32_t n = multisig->pubkeys_count;
	if (m < 2 || m > 3) return 0;
	if (n < 2 || n > 3) return 0;
	uint32_t i, r = 0;
	if (out) {
		out[r] = 0x50 + m; r++;
		for (i = 0; i < n; i++) {
			r += op_push(multisig->pubkeys[i].size, out + r);
			memcpy(out + r, multisig->pubkeys[i].bytes, multisig->pubkeys[i].size); r += multisig->pubkeys[i].size;
		}
		out[r] = 0x50 + n; r++;
		out[r] = 0xAE; r++; // OP_CHECKMULTISIG
	} else {
		r++;
		for (i = 0; i < n; i++) {
			uint8_t dummy[8];
			r += op_push(multisig->pubkeys[i].size, dummy);
			r += multisig->pubkeys[i].size;
		}
		r++;
		r++;
	}
	return r;
}

uint32_t serialize_script_sig(const uint8_t *signature, uint32_t signature_len, const uint8_t *pubkey, uint32_t pubkey_len, uint8_t *out)
{
	uint32_t r = 0;
	r += op_push(signature_len + 1, out + r);
	memcpy(out + r, signature, signature_len); r += signature_len;
	out[r] = 0x01; r++;
	r += op_push(pubkey_len, out + r);
	memcpy(out + r, pubkey, pubkey_len); r += pubkey_len;
	return r;
}

uint32_t serialize_script_multisig(const MultisigRedeemScriptType *multisig, uint8_t *out)
{
	uint32_t i, r = 0;
	out[r] = 0x00; r++;
	for (i = 0; i < multisig->signatures_count; i++) {
		if (multisig->signatures[i].size == 0) {
			continue;
		}
		r += op_push(multisig->signatures[i].size + 1, out + r);
		memcpy(out + r, multisig->signatures[i].bytes, multisig->signatures[i].size); r += multisig->signatures[i].size;
		out[r] = 0x01; r++;
	}
	uint32_t script_len = compile_script_multisig(multisig, 0);
	r += op_push(script_len, out + r);
	r += compile_script_multisig(multisig, out + r);
	return r;
}

// tx methods

uint32_t tx_serialize_header(TxStruct *tx, uint8_t *out)
{
	memcpy(out, &(tx->version), 4);
	return 4 + ser_length(tx->inputs_len, out + 4);
}

uint32_t tx_serialize_input(TxStruct *tx, uint8_t *prev_hash, uint32_t prev_index, uint8_t *script_sig, uint32_t script_sig_len, uint32_t sequence, uint8_t *out)
{
	int i;
	if (tx->have_inputs >= tx->inputs_len) {
		// already got all inputs
		return 0;
	}
	uint32_t r = 0;
	if (tx->have_inputs == 0) {
		r += tx_serialize_header(tx, out + r);
	}
	for (i = 0; i < 32; i++) {
		*(out + r + i) = prev_hash[31 - i];
	}
	r += 32;
	memcpy(out + r, &prev_index, 4); r += 4;
	r += ser_length(script_sig_len, out + r);
	memcpy(out + r, script_sig, script_sig_len); r+= script_sig_len;
	memcpy(out + r, &sequence, 4); r += 4;

	tx->have_inputs++;
	tx->size += r;

	return r;
}

uint32_t tx_serialize_middle(TxStruct *tx, uint8_t *out)
{
	return ser_length(tx->outputs_len, out);
}

uint32_t tx_serialize_footer(TxStruct *tx, uint8_t *out)
{
	memcpy(out, &(tx->lock_time), 4);
	if (tx->add_hash_type) {
		uint32_t ht = 1;
		memcpy(out + 4, &ht, 4);
		return 8;
	} else {
		return 4;
	}
}

uint32_t tx_serialize_output(TxStruct *tx, uint64_t amount, uint8_t *script_pubkey, uint32_t script_pubkey_len, uint8_t *out)
{
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
	memcpy(out + r, &amount, 8); r += 8;
	r += ser_length(script_pubkey_len, out + r);
	memcpy(out + r, script_pubkey, script_pubkey_len); r+= script_pubkey_len;
	tx->have_outputs++;
	if (tx->have_outputs == tx->outputs_len) {
		r += tx_serialize_footer(tx, out + r);
	}
	tx->size += r;
	return r;
}

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len, uint32_t version, uint32_t lock_time, bool add_hash_type)
{
	tx->inputs_len = inputs_len;
	tx->outputs_len = outputs_len;
	tx->version = version;
	tx->lock_time = lock_time;
	tx->add_hash_type = add_hash_type;
	tx->have_inputs = 0;
	tx->have_outputs = 0;
	tx->size = 0;
	sha256_Init(&(tx->ctx));
}

bool tx_hash_input(TxStruct *t, TxInputType *input)
{
	uint8_t buf[1024];
	uint32_t r = tx_serialize_input(t, input->prev_hash.bytes, input->prev_index, input->script_sig.bytes, input->script_sig.size, input->sequence, buf);
	if (!r) return false;
	sha256_Update(&(t->ctx), buf, r);
	return true;
}

bool tx_hash_output(TxStruct *t, TxOutputBinType *output)
{
	uint8_t buf[1024];
	uint32_t r = tx_serialize_output(t, output->amount, output->script_pubkey.bytes, output->script_pubkey.size, buf);
	if (!r) return false;
	sha256_Update(&(t->ctx), buf, r);
	return true;
}

void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse)
{
	sha256_Final(hash, &(t->ctx));
	sha256_Raw(hash, 32, hash);
	if (!reverse) return;
	uint8_t i, k;
	for (i = 0; i < 16; i++) {
		k = hash[31 - i];
		hash[31 - i] = hash[i];
		hash[i] = k;
	}
}

uint32_t transactionEstimateSize(uint32_t inputs, uint32_t outputs)
{
	return 10 + inputs * 149 + outputs * 35;
}

uint32_t transactionEstimateSizeKb(uint32_t inputs, uint32_t outputs)
{
	return (transactionEstimateSize(inputs, outputs) + 999) / 1000;
}
