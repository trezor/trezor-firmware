/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2016 Alex Beregszaszi <alex@rtfs.hu>
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

#include "ethereum.h"
#include "fsm.h"
#include "layout2.h"
#include "messages.h"
#include "transaction.h"
#include "ecdsa.h"
#include "protect.h"
#include "crypto.h"
#include "secp256k1.h"
#include "sha3.h"

static bool signing = false;
static size_t data_left;
static EthereumTxRequest resp;
static uint8_t hash[32], sig[64], privkey[32];
// FIXME: this is currently 400 bytes. Could be probably improved.
struct SHA3_CTX keccak_ctx;

/*
 * Encode length according to RLP.
 * FIXME: improve
 */
static int rlp_encode_length(uint8_t *buf, int length, uint8_t firstbyte, bool list)
{
	if (!list && (length == 1 && firstbyte <= 0x7f)) {
		buf[0] = firstbyte;
		return 1;
	} else if (length <= 55) {
		buf[0] = (list ? 0xc0 : 0x80) + length;
		return 1;
	} else if (length <= 0xff) {
		buf[0] = (list ? 0xf7 : 0xb7) + 1;
		buf[1] = length;
		return 2;
	} else if (length <= 0xffff) {
		buf[0] = (list ? 0xf7 : 0xb7) + 2;
		buf[1] = length >> 8;
		buf[2] = length & 0xff;
		return 3;
	} else {
		buf[0] = (list ? 0xf7 : 0xb7) + 3;
		buf[1] = length >> 16;
		buf[2] = length >> 8;
		buf[3] = length & 0xff;
		return 4;
	}
}

/*
 * Calculate the number of bytes needed for an RLP length header.
 * NOTE: supports up to 16MB of data (how unlikely...)
 * FIXME: improve
 */
static int rlp_calculate_length(int length, uint8_t firstbyte) {
	if (length == 1 && firstbyte <= 0x7f) {
		return 1;
	} else if (length <= 55) {
		return 1 + length;
	} else if (length <= 0xff) {
		return 2 + length;
	} else if (length <= 0xffff) {
		return 3 + length;
	} else
		return 4 + length;
}

static inline void hash_data(const uint8_t *buf, size_t size)
{
	sha3_Update(&keccak_ctx, buf, size);
}

/*
 * Push an RLP encoded length to the hash buffer.
 */
static void hash_rlp_length(int length, uint8_t firstbyte)
{
	uint8_t buf[4];
	size_t size = rlp_encode_length(buf, length, firstbyte, false);
	hash_data(buf, size);
}

/*
 * Push an RLP encoded list length to the hash buffer.
 */
static void hash_rlp_list_length(int length)
{
	uint8_t buf[4];
	size_t size = rlp_encode_length(buf, length, 0, true);
	hash_data(buf, size);
}

/*
 * Push an RLP encoded length field and data to the hash buffer.
 */
static void hash_rlp_field(const uint8_t *buf, size_t size)
{
	hash_rlp_length(size, buf[0]);
	/* FIXME: this special case should be handled more nicely */
	if (!(size == 1 && buf[0] <= 0x7f))
		hash_data(buf, size);
}

static void send_request_chunk(size_t length)
{
	resp.data_length = length <= 1024 ? length : 1024;
	msg_write(MessageType_MessageType_EthereumTxRequest, &resp);
}

static void send_signature(void)
{
	keccak_Final(&keccak_ctx, hash);
	uint8_t v;
	if (ecdsa_sign_digest(&secp256k1, privkey, hash, sig, &v) != 0) {
		fsm_sendFailure(FailureType_Failure_Other, "Signing failed");
		ethereum_signing_abort();
		return;
	}

	memset(privkey, 0, sizeof(privkey));

	/* Send back the result */
	resp.has_data_length = false;

	resp.has_signature_v = true;
	resp.signature_v = v + 27;

	resp.has_signature_r = true;
	resp.signature_r.size = 32;
	memcpy(resp.signature_r.bytes, sig, 32);

	resp.has_signature_s = true;
	resp.signature_s.size = 32;
	memcpy(resp.signature_s.bytes, sig + 32, 32);

	msg_write(MessageType_MessageType_EthereumTxRequest, &resp);

	ethereum_signing_abort();
}

/*
 * RLP fields:
 * - nonce (0 .. 32)
 * - gas_price (0 .. 32)
 * - gas_limit (0 .. 32)
 * - to (0, 20)
 * - value (0 .. 32)
 * - data (0 ..)
 */

void ethereum_signing_init(EthereumSignTx *msg, const HDNode *node)
{
	signing = true;
	sha3_256_Init(&keccak_ctx);

	memset(&resp, 0, sizeof(EthereumTxRequest));
	/* NOTE: in the first stage we'll always request more data */
	resp.has_data_length = true;

	/* Stage 1: Calculate total RLP length */
	int total_rlp_length = 0;

	layoutProgress("Signing Eth", 1);

	if (msg->has_nonce)
		total_rlp_length += rlp_calculate_length(msg->nonce.size, msg->nonce.bytes[0]);
	else
		total_rlp_length++;

	layoutProgress("Signing Eth", 2);

	if (msg->has_gas_price)
		total_rlp_length += rlp_calculate_length(msg->gas_price.size, msg->gas_price.bytes[0]);
	else
		total_rlp_length++;

	layoutProgress("Signing Eth", 3);

	if (msg->has_gas_limit)
		total_rlp_length += rlp_calculate_length(msg->gas_limit.size, msg->gas_limit.bytes[0]);
	else
		total_rlp_length++;

	layoutProgress("Signing Eth", 4);

	if (msg->has_to)
		total_rlp_length += rlp_calculate_length(msg->to.size, msg->to.bytes[0]);
	else
		total_rlp_length++;

	layoutProgress("Signing Eth", 5);

	if (msg->has_value)
		total_rlp_length += rlp_calculate_length(msg->value.size, msg->value.bytes[0]);
	else
		total_rlp_length++;

	layoutProgress("Signing Eth", 6);

	if (msg->has_data_initial_chunk) {
		if (msg->has_data_length)
			total_rlp_length += rlp_calculate_length(msg->data_initial_chunk.size + msg->data_length, msg->data_initial_chunk.bytes[0]);
		else
			total_rlp_length += rlp_calculate_length(msg->data_initial_chunk.size, msg->data_initial_chunk.bytes[0]);
	} else
		total_rlp_length++;

	layoutProgress("Signing Eth", 7);

	/* Stage 2: Store header fields */
	hash_rlp_list_length(total_rlp_length);

	layoutProgress("Signing Eth", 8);

	if (msg->has_nonce)
		hash_rlp_field(msg->nonce.bytes, msg->nonce.size);
	else
		hash_rlp_length(1, 0);

	if (msg->has_gas_price)
		hash_rlp_field(msg->gas_price.bytes, msg->gas_price.size);
	else
		hash_rlp_length(1, 0);

	if (msg->has_gas_limit)
		hash_rlp_field(msg->gas_limit.bytes, msg->gas_limit.size);
	else
		hash_rlp_length(1, 0);

	if (msg->has_to)
		hash_rlp_field(msg->to.bytes, msg->to.size);
	else
		hash_rlp_length(1, 0);

	if (msg->has_value)
		hash_rlp_field(msg->value.bytes, msg->value.size);
	else
		hash_rlp_length(1, 0);

	if (msg->has_data_initial_chunk)
		hash_rlp_field(msg->data_initial_chunk.bytes, msg->data_initial_chunk.size);
	else
		hash_rlp_length(1, 0);

	layoutProgress("Signing Eth", 9);

	/* FIXME: probably this shouldn't be done here, but at a later stage */
	memcpy(privkey, node->private_key, 32);

	if (msg->has_data_length && msg->data_length > 0) {
		layoutProgress("Signing Eth", 20);
		data_left = msg->data_length;
		send_request_chunk(msg->data_length);
	} else {
		layoutProgress("Signing Eth", 50);
		send_signature();
	}
}

void ethereum_signing_txack(EthereumTxAck *tx)
{
	if (!signing) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Signing mode");
		layoutHome();
		return;
	}

	if (data_left > 0 && (!tx->has_data_chunk || tx->data_chunk.size == 0)) {
		fsm_sendFailure(FailureType_Failure_Other, "Empty data chunk received");
		ethereum_signing_abort();
		return;
	}

	hash_data(tx->data_chunk.bytes, tx->data_chunk.size);

	data_left -= tx->data_chunk.size;

	if (data_left > 0) {
		send_request_chunk(data_left);
	} else {
		send_signature();
	}
}

void ethereum_signing_abort(void)
{
	if (signing) {
		memset(privkey, 0, sizeof(privkey));
		layoutHome();
		signing = false;
	}
}
