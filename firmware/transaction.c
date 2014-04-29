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
#include "messages.pb.h"

// aux methods

uint32_t ser_length(uint32_t len, uint8_t *out) {
	if (len < 253) {
		out[0] = len & 0xFF;
		return 1;
	}
	if (len < 0x10000) {
		out[0] = 253;
		out[1] = len & 0xFF;
		out[2] = (len >> 8) & 0xFF;
		return 3;
	}
	out[0] = 254;
	out[1] = len & 0xFF;
	out[2] = (len >> 8) & 0xFF;
	out[3] = (len >> 16) & 0xFF;
	out[4] = (len >> 24) & 0xFF;
	return 5;
}

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

	if (in->script_type == ScriptType_PAYTOADDRESS) {
		out->script_pubkey.bytes[0] = 0x76; // OP_DUP
		out->script_pubkey.bytes[1] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[2] = 0x14; // pushing 20 bytes
		uint8_t decoded[21];
		if (!ecdsa_address_decode(in->address, decoded)) {
			return 0;
		}
		memcpy(out->script_pubkey.bytes + 3, decoded + 1, 20);
		out->script_pubkey.bytes[23] = 0x88; // OP_EQUALVERIFY
		out->script_pubkey.bytes[24] = 0xAC; // OP_CHECKSIG
		out->script_pubkey.size = 25;
		return 25;
	}

	if (in->script_type == ScriptType_PAYTOSCRIPTHASH) {
		out->script_pubkey.bytes[0] = 0xA9; // OP_HASH_160
		out->script_pubkey.bytes[1] = 0x14; // pushing 20 bytes
		uint8_t decoded[21];
		if (!ecdsa_address_decode(in->address, decoded)) {
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

int serialize_script_sig(uint8_t *signature, uint32_t signature_len, uint8_t *pubkey, uint32_t pubkey_len, uint8_t *out)
{
	uint32_t r = 0;
	r += op_push(signature_len + 1, out + r);
	memcpy(out + r, signature, signature_len); r += signature_len;
	out[r] = 0x01; r++;
	r += op_push(pubkey_len, out + r);
	memcpy(out + r, pubkey, pubkey_len); r += pubkey_len;
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
	uint8_t buf[512];
	uint32_t r = tx_serialize_input(t, input->prev_hash.bytes, input->prev_index, input->script_sig.bytes, input->script_sig.size, input->sequence, buf);
	if (!r) return false;
	sha256_Update(&(t->ctx), buf, r);
	return true;
}

bool tx_hash_output(TxStruct *t, TxOutputBinType *output)
{
	uint8_t buf[512];
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

bool transactionHash(TransactionType *tx, uint8_t *hash)
{
	TxStruct t;
	uint32_t i;
	tx_init(&t, tx->inputs_count, tx->bin_outputs_count, tx->version, tx->lock_time, false);
	for (i = 0; i < tx->inputs_count; i++) {
		if (!tx_hash_input(&t, &(tx->inputs[i]))) return false;
	}
	for (i = 0; i < tx->bin_outputs_count; i++) {
		if (!tx_hash_output(&t, &(tx->bin_outputs[i]))) return false;
	}
	tx_hash_final(&t, hash, true);
	return true;
}

int transactionSimpleSign(const CoinType *coin, HDNode *root, TxInputType *inputs, uint32_t inputs_count, TxOutputType *outputs, uint32_t outputs_count, uint32_t version, uint32_t lock_time, uint8_t *out)
{
	uint32_t idx, i, k, r = 0;
	TxStruct ti, to;
	uint8_t buf[512];
	TxInputType input;
	TxOutputBinType output;
	HDNode node;
	uint8_t privkey[32], pubkey[33], hash[32], sig[64];

	layoutProgressSwipe("Signing", 0, 0);
	tx_init(&to, inputs_count, outputs_count, version, lock_time, false);
	for (idx = 0; idx < inputs_count; idx++) {
		// compute inner transaction
		memcpy(&input, &(inputs[idx]), sizeof(TxInputType));
		tx_init(&ti, inputs_count, outputs_count, version, lock_time, true);
		memset(privkey, 0, 32);
		memset(pubkey, 0, 33);
		for (i = 0; i < inputs_count; i++) {
			if (i == idx) {
				memcpy(&node, root, sizeof(HDNode));
				for (k = 0; k < inputs[i].address_n_count; k++) {
					hdnode_private_ckd(&node, inputs[i].address_n[k]);
				}
				ecdsa_get_pubkeyhash(node.public_key, hash);
				inputs[i].script_sig.size = compile_script_sig(coin->address_type, hash, inputs[i].script_sig.bytes);
				if (inputs[i].script_sig.size == 0) {
					return 0;
				}
				memcpy(privkey, node.private_key, 32);
				memcpy(pubkey, node.public_key, 33);
			} else {
				inputs[i].script_sig.size = 0;
			}
			if (!tx_hash_input(&ti, &(inputs[i]))) return 0;
		}
		for (i = 0; i < outputs_count; i++) {
			int co = compile_output(coin, root, &(outputs[i]), &output, idx == 0);
			if (co <= 0) {
				return co;
			}
			if (!tx_hash_output(&ti, &output)) return 0;
		}
		tx_hash_final(&ti, hash, false);
		ecdsa_sign_digest(privkey, hash, sig);
		int der_len = ecdsa_sig_to_der(sig, buf);
		input.script_sig.size = serialize_script_sig(buf, der_len, pubkey, 33, input.script_sig.bytes);
		r += tx_serialize_input(&to, input.prev_hash.bytes, input.prev_index, input.script_sig.bytes, input.script_sig.size, input.sequence, out + r);
		layoutProgress("Signing", 1000 * idx / inputs_count, idx);
	}
	for (i = 0; i < outputs_count; i++) {
		if (compile_output(coin, root, &(outputs[i]), &output, false) <= 0) {
			return 0;
		}
		r += tx_serialize_output(&to, output.amount, output.script_pubkey.bytes, output.script_pubkey.size, out + r);
	}
	return r;
}

uint32_t transactionEstimateSize(uint32_t inputs, uint32_t outputs)
{
	return 10 + inputs * 149 + outputs * 35;
}

uint32_t transactionEstimateSizeKb(uint32_t inputs, uint32_t outputs)
{
	return (transactionEstimateSize(inputs, outputs) + 999) / 1000;
}

bool transactionMessageSign(uint8_t *message, uint32_t message_len, uint8_t *privkey, const char *address, uint8_t *signature)
{
	if (message_len >= 256) {
		return false;
	}

	SHA256_CTX ctx;
	uint8_t i, hash[32];

	sha256_Init(&ctx);
	sha256_Update(&ctx, (const uint8_t *)"\x18" "Bitcoin Signed Message:" "\n", 25);
	i = message_len;
	sha256_Update(&ctx, &i, 1);
	sha256_Update(&ctx, message, message_len);
	sha256_Final(hash, &ctx);
	sha256_Raw(hash, 32, hash);

	ecdsa_sign_digest(privkey, hash, signature + 1);
	for (i = 27 + 4; i < 27 + 4 + 4; i++) {
		signature[0] = i;
		if (transactionMessageVerify(message, message_len, signature, address)) {
			return true;
		}
	}

	return false;
}

bool transactionMessageVerify(uint8_t *message, uint32_t message_len, uint8_t *signature, const char *address)
{
	if (message_len >= 256) {
		return false;
	}

	bool compressed;
	uint8_t nV = signature[0];
	bignum256 r, s, e;
	curve_point cp, cp2;
	SHA256_CTX ctx;
	uint8_t i, pubkey[65], decoded[21], hash[32];
	char addr[35];

	if (nV < 27 || nV >= 35) {
		return false;
	}
	compressed = (nV >= 31);
	if (compressed) {
		nV -= 4;
	}
	uint8_t recid = nV - 27;
	// read r and s
	bn_read_be(signature + 1, &r);
	bn_read_be(signature + 33, &s);
	// x = r + (recid / 2) * order
	bn_zero(&cp.x);
	for (i = 0; i < recid / 2; i++) {
		bn_addmod(&cp.x, &order256k1, &prime256k1);
	}
	bn_addmod(&cp.x, &r, &prime256k1);
	// compute y from x
	uncompress_coords(recid % 2, &cp.x, &cp.y);
	// calculate hash
	sha256_Init(&ctx);
	sha256_Update(&ctx, (const uint8_t *)"\x18" "Bitcoin Signed Message:" "\n", 25);
	i = message_len;
	sha256_Update(&ctx, &i, 1);
	sha256_Update(&ctx, message, message_len);
	sha256_Final(hash, &ctx);
	sha256_Raw(hash, 32, hash);
	// e = -hash
	bn_read_be(hash, &e);
	bn_substract_noprime(&order256k1, &e, &e);
	// r = r^-1
	bn_inverse(&r, &order256k1);
	point_multiply(&s, &cp, &cp);
	scalar_multiply(&e, &cp2);
	point_add(&cp2, &cp);
	point_multiply(&r, &cp, &cp);
	pubkey[0] = 0x04;
	bn_write_be(&cp.x, pubkey + 1);
	bn_write_be(&cp.y, pubkey + 33);
	// check if the address is correct when provided
	if (address) {
		ecdsa_address_decode(address, decoded);
		if (compressed) {
			pubkey[0] = 0x02 | (cp.y.val[0] & 0x01);
		}
		ecdsa_get_address(pubkey, decoded[0], addr);
		if (strcmp(addr, address) != 0) {
			return false;
		}
	}
	// check if signature verifies the digest
	if (ecdsa_verify_digest(pubkey, signature + 1, hash) != 0) {
		return false;
	}
	return true;
}
