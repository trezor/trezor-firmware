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
#include "ripemd160.h"
#include "base58.h"
#include "address.h"
#include "messages.pb.h"
#include "types.pb.h"

static const uint8_t segwit_header[2] = {0,1};

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
	memset(out, 0, sizeof(TxOutputBinType));
	out->amount = in->amount;
	uint8_t addr_raw[MAX_ADDR_RAW_SIZE];
	int addr_raw_len;

	if (in->has_address) { // address provided -> regular output
		addr_raw_len = base58_decode_check(in->address, addr_raw, MAX_ADDR_RAW_SIZE);
		if (in->script_type != OutputScriptType_PAYTOADDRESS) {
			// allow for p2sh (backward compatibility only)
			if (in->script_type != OutputScriptType_PAYTOSCRIPTHASH
				|| addr_raw_len != 21
				|| addr_raw[0] != coin->address_type_p2sh) {
				return 0;
			}
		}

		if (addr_raw_len == 21 &&
			addr_raw[0] == coin->address_type) { // p2pkh

			out->script_pubkey.bytes[0] = 0x76; // OP_DUP
			out->script_pubkey.bytes[1] = 0xA9; // OP_HASH_160
			out->script_pubkey.bytes[2] = 0x14; // pushing 20 bytes
			memcpy(out->script_pubkey.bytes + 3, addr_raw + 1, 20);
			out->script_pubkey.bytes[23] = 0x88; // OP_EQUALVERIFY
			out->script_pubkey.bytes[24] = 0xAC; // OP_CHECKSIG
			out->script_pubkey.size = 25;
		} else if (addr_raw_len == 21
				   && addr_raw[0] == coin->address_type_p2sh) { // p2sh
			out->script_pubkey.bytes[0] = 0xA9; // OP_HASH_160
			out->script_pubkey.bytes[1] = 0x14; // pushing 20 bytes
			memcpy(out->script_pubkey.bytes + 2, addr_raw + 1, 20);
			out->script_pubkey.bytes[22] = 0x87; // OP_EQUAL
			out->script_pubkey.size = 23;
		} else if (addr_raw_len == 23
				   && addr_raw[0] == coin->address_type_p2wpkh
				   && addr_raw[1] == 0 && addr_raw[2] == 0) { // p2wpkh v0
			out->script_pubkey.bytes[0] = 0x00; // version 0
			out->script_pubkey.bytes[1] = 0x14; // pushing 20 bytes
			memcpy(out->script_pubkey.bytes + 2, addr_raw + 3, 20);
			out->script_pubkey.size = 22;
		} else if (addr_raw_len == 35
				   && addr_raw[0] == coin->address_type_p2wsh
				   && addr_raw[1] == 0 && addr_raw[2] == 0) { // p2wsh v0
			out->script_pubkey.bytes[0] = 0x00; // version 0
			out->script_pubkey.bytes[1] = 0x20; // pushing 32 bytes
			memcpy(out->script_pubkey.bytes + 2, addr_raw + 3, 32);
			out->script_pubkey.size = 34;
		} else {
			return 0;
		}

		if (needs_confirm) {
			layoutConfirmOutput(coin, in);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
				return -1;
			}
		}

		return out->script_pubkey.size;
	}

	if (in->script_type == OutputScriptType_PAYTOADDRESS) {
		// address_n provided-> change address -> calculate from address_n
		if (in->script_type == OutputScriptType_PAYTOADDRESS &&
			in->address_n_count > 0) {
			HDNode node;
			memcpy(&node, root, sizeof(HDNode));
			if (hdnode_private_ckd_cached(&node, in->address_n, in->address_n_count) == 0) {
				return 0;
			}
			layoutProgressUpdate(true);
			hdnode_get_address_raw(&node, coin->address_type, addr_raw);
		} else { // does not have address_n neither address -> error
			return 0;
		}

		out->script_pubkey.bytes[0] = 0x76; // OP_DUP
		out->script_pubkey.bytes[1] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[2] = 0x14; // pushing 20 bytes
		memcpy(out->script_pubkey.bytes + 3, addr_raw + address_prefix_bytes_len(coin->address_type), 20);
		out->script_pubkey.bytes[23] = 0x88; // OP_EQUALVERIFY
		out->script_pubkey.bytes[24] = 0xAC; // OP_CHECKSIG
		out->script_pubkey.size = 25;
		return 25;
	}

	if (in->script_type == OutputScriptType_PAYTOMULTISIG) {
		uint8_t buf[32];
		size_t prefix_bytes = address_prefix_bytes_len(coin->address_type_p2sh);
		if (!in->has_multisig) {
			return 0;
		}
		if (compile_script_multisig_hash(&(in->multisig), buf) == 0) {
			return 0;
		}
		address_write_prefix_bytes(coin->address_type_p2sh, addr_raw);
		ripemd160(buf, 32, addr_raw + prefix_bytes);
		if (needs_confirm) {
			base58_encode_check(addr_raw, prefix_bytes + 20, in->address, sizeof(in->address));
			layoutConfirmOutput(coin, in);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
				return -1;
			}
		}
		out->script_pubkey.bytes[0] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[1] = 0x14; // pushing 20 bytes
		memcpy(out->script_pubkey.bytes + 2, addr_raw + prefix_bytes, 20);
		out->script_pubkey.bytes[22] = 0x87; // OP_EQUAL
		out->script_pubkey.size = 23;
		return 23;
	}

	if (in->script_type == OutputScriptType_PAYTOOPRETURN) {
		if (in->amount != 0) return 0; // only 0 satoshi allowed for OP_RETURN
		uint32_t r = 0;
		out->script_pubkey.bytes[0] = 0x6A; r++; // OP_RETURN
		r += op_push(in->op_return_data.size, out->script_pubkey.bytes + r);
		memcpy(out->script_pubkey.bytes + r, in->op_return_data.bytes, in->op_return_data.size); r += in->op_return_data.size;
		out->script_pubkey.size = r;
		return r;
	}

	return 0;
}

uint32_t compile_script_sig(uint32_t address_type, const uint8_t *pubkeyhash, uint8_t *out)
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
	const uint32_t m = multisig->m;
	const uint32_t n = multisig->pubkeys_count;
	if (m < 1 || m > 15) return 0;
	if (n < 1 || n > 15) return 0;
	uint32_t i, r = 0;
	if (out) {
		out[r] = 0x50 + m; r++;
		for (i = 0; i < n; i++) {
			out[r] = 33; r++; // OP_PUSH 33
			const uint8_t *pubkey = cryptoHDNodePathToPubkey(&(multisig->pubkeys[i]));
			if (!pubkey) return 0;
			memcpy(out + r, pubkey, 33); r += 33;
		}
		out[r] = 0x50 + n; r++;
		out[r] = 0xAE; r++; // OP_CHECKMULTISIG
	} else {
		r = 1 + 34 * n + 2;
	}
	return r;
}

uint32_t compile_script_multisig_hash(const MultisigRedeemScriptType *multisig, uint8_t *hash)
{
	if (!multisig->has_m) return 0;
	const uint32_t m = multisig->m;
	const uint32_t n = multisig->pubkeys_count;
	if (m < 1 || m > 15) return 0;
	if (n < 1 || n > 15) return 0;

	SHA256_CTX ctx;
	sha256_Init(&ctx);

	uint8_t d[2];
	d[0] = 0x50 + m; sha256_Update(&ctx, d, 1);
	uint32_t i;
	for (i = 0; i < n; i++) {
		d[0] = 33; sha256_Update(&ctx, d, 1); // OP_PUSH 33
		const uint8_t *pubkey = cryptoHDNodePathToPubkey(&(multisig->pubkeys[i]));
		if (!pubkey) return 0;
		sha256_Update(&ctx, pubkey, 33);
	}
	d[0] = 0x50 + n;
	d[1] = 0xAE;
	sha256_Update(&ctx, d, 2);

	sha256_Final(&ctx, hash);

	return 1;
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
	if (script_len == 0) {
		return 0;
	}
	r += op_push(script_len, out + r);
	r += compile_script_multisig(multisig, out + r);
	return r;
}

// tx methods

uint32_t tx_prevout_hash(SHA256_CTX *ctx, const TxInputType *input)
{
	int i;
	for (i = 0; i < 32; i++) {
		sha256_Update(ctx, &(input->prev_hash.bytes[31 - i]), 1);
	}
	sha256_Update(ctx, (const uint8_t *)&input->prev_index, 4);
	return 36;
}

uint32_t tx_script_hash(SHA256_CTX *ctx, uint32_t size, const uint8_t *data)
{
	int r = ser_length_hash(ctx, size);
	sha256_Update(ctx, data, size);
	return r + size;
}

uint32_t tx_sequence_hash(SHA256_CTX *ctx, const TxInputType *input)
{
	sha256_Update(ctx, (const uint8_t *)&input->sequence, 4);
	return 4;
}

uint32_t tx_output_hash(SHA256_CTX *ctx, const TxOutputBinType *output)
{
	uint32_t r = 0;
	sha256_Update(ctx, (const uint8_t *)&output->amount, 8); r += 8;
	r += tx_script_hash(ctx, output->script_pubkey.size, output->script_pubkey.bytes);
	return r;
}

uint32_t tx_serialize_script(uint32_t size, const uint8_t *data, uint8_t *out)
{
	int r = ser_length(size, out);
	memcpy(out + r, data, size);
	return r + size;
}

uint32_t tx_serialize_header(TxStruct *tx, uint8_t *out)
{
	int r = 4;
	memcpy(out, &(tx->version), 4);
	if (tx->is_segwit) {
		memcpy(out + r, segwit_header, 2);
		r += 2;
	}
	return r + ser_length(tx->inputs_len, out + r);
}

uint32_t tx_serialize_header_hash(TxStruct *tx)
{
	int r = 4;
	sha256_Update(&(tx->ctx), (const uint8_t *)&(tx->version), 4);
	if (tx->is_segwit) {
		sha256_Update(&(tx->ctx), segwit_header, 2);
		r += 2;
	}
	return r + ser_length_hash(&(tx->ctx), tx->inputs_len);
}

uint32_t tx_serialize_input(TxStruct *tx, const TxInputType *input, uint8_t *out)
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
		*(out + r + i) = input->prev_hash.bytes[31 - i];
	}
	r += 32;
	memcpy(out + r, &input->prev_index, 4); r += 4;
	r += tx_serialize_script(input->script_sig.size, input->script_sig.bytes, out + r);
	memcpy(out + r, &input->sequence, 4); r += 4;

	tx->have_inputs++;
	tx->size += r;

	return r;
}

uint32_t tx_serialize_input_hash(TxStruct *tx, const TxInputType *input)
{
	if (tx->have_inputs >= tx->inputs_len) {
		// already got all inputs
		return 0;
	}
	uint32_t r = 0;
	if (tx->have_inputs == 0) {
		r += tx_serialize_header_hash(tx);
	}
	r += tx_prevout_hash(&(tx->ctx), input);
	r += tx_script_hash(&(tx->ctx), input->script_sig.size, input->script_sig.bytes);
	r += tx_sequence_hash(&(tx->ctx), input);

	tx->have_inputs++;
	tx->size += r;

	return r;
}

uint32_t tx_serialize_middle(TxStruct *tx, uint8_t *out)
{
	return ser_length(tx->outputs_len, out);
}

uint32_t tx_serialize_middle_hash(TxStruct *tx)
{
	return ser_length_hash(&(tx->ctx), tx->outputs_len);
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

uint32_t tx_serialize_footer_hash(TxStruct *tx)
{
	sha256_Update(&(tx->ctx), (const uint8_t *)&(tx->lock_time), 4);
	if (tx->add_hash_type) {
		uint32_t ht = 1;
		sha256_Update(&(tx->ctx), (const uint8_t *)&ht, 4);
		return 8;
	} else {
		return 4;
	}
}

uint32_t tx_serialize_output(TxStruct *tx, const TxOutputBinType *output, uint8_t *out)
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
	memcpy(out + r, &output->amount, 8); r += 8;
	r += tx_serialize_script(output->script_pubkey.size, output->script_pubkey.bytes, out + r);
	tx->have_outputs++;
	if (tx->have_outputs == tx->outputs_len) {
		r += tx_serialize_footer(tx, out + r);
	}
	tx->size += r;
	return r;
}

uint32_t tx_serialize_output_hash(TxStruct *tx, const TxOutputBinType *output)
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
		r += tx_serialize_middle_hash(tx);
	}
	r += tx_output_hash(&(tx->ctx), output);
	tx->have_outputs++;
	if (tx->have_outputs == tx->outputs_len) {
		r += tx_serialize_footer_hash(tx);
	}
	tx->size += r;
	return r;
}

uint32_t tx_serialize_extra_data_hash(TxStruct *tx, const uint8_t *data, uint32_t datalen)
{
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
	sha256_Update(&(tx->ctx), data, datalen);
	tx->extra_data_received += datalen;
	tx->size += datalen;
	return datalen;
}

void tx_init(TxStruct *tx, uint32_t inputs_len, uint32_t outputs_len, uint32_t version, uint32_t lock_time, uint32_t extra_data_len, bool add_hash_type)
{
	tx->inputs_len = inputs_len;
	tx->outputs_len = outputs_len;
	tx->version = version;
	tx->lock_time = lock_time;
	tx->add_hash_type = add_hash_type;
	tx->have_inputs = 0;
	tx->have_outputs = 0;
	tx->extra_data_len = extra_data_len;
	tx->extra_data_received = 0;
	tx->size = 0;
	sha256_Init(&(tx->ctx));
}

void tx_hash_final(TxStruct *t, uint8_t *hash, bool reverse)
{
	sha256_Final(&(t->ctx), hash);
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
