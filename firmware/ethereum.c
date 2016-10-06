/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2016 Alex Beregszaszi <alex@rtfs.hu>
 * Copyright (C) 2016 Pavol Rusnak <stick@satoshilabs.com>
 * Copyright (C) 2016 Jochen Hoenicke <hoenicke@gmail.com>
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
#include "util.h"

static bool ethereum_signing = false;
static uint32_t data_total, data_left;
static EthereumTxRequest resp;
static uint8_t privkey[32];
struct SHA3_CTX keccak_ctx;

static inline void hash_data(const uint8_t *buf, size_t size)
{
	sha3_Update(&keccak_ctx, buf, size);
}

/*
 * Push an RLP encoded length to the hash buffer.
 */
static void hash_rlp_length(uint32_t length, uint8_t firstbyte)
{
	uint8_t buf[4];
	if (length == 1 && firstbyte <= 0x7f) {
		/* empty length header */
	} else if (length <= 55) {
		buf[0] = 0x80 + length;
		hash_data(buf, 1);
	} else if (length <= 0xff) {
		buf[0] = 0xb7 + 1;
		buf[1] = length;
		hash_data(buf, 2);
	} else if (length <= 0xffff) {
		buf[0] = 0xb7 + 2;
		buf[1] = length >> 8;
		buf[2] = length & 0xff;
		hash_data(buf, 3);
	} else {
		buf[0] = 0xb7 + 3;
		buf[1] = length >> 16;
		buf[2] = length >> 8;
		buf[3] = length & 0xff;
		hash_data(buf, 4);
	}
}

/*
 * Push an RLP encoded list length to the hash buffer.
 */
static void hash_rlp_list_length(uint32_t length)
{
	uint8_t buf[4];
	if (length <= 55) {
		buf[0] = 0xc0 + length;
		hash_data(buf, 1);
	} else if (length <= 0xff) {
		buf[0] = 0xf7 + 1;
		buf[1] = length;
		hash_data(buf, 2);
	} else if (length <= 0xffff) {
		buf[0] = 0xf7 + 2;
		buf[1] = length >> 8;
		buf[2] = length & 0xff;
		hash_data(buf, 3);
	} else {
		buf[0] = 0xf7 + 3;
		buf[1] = length >> 16;
		buf[2] = length >> 8;
		buf[3] = length & 0xff;
		hash_data(buf, 4);
	}
}

/*
 * Push an RLP encoded length field and data to the hash buffer.
 */
static void hash_rlp_field(const uint8_t *buf, size_t size)
{
	hash_rlp_length(size, buf[0]);
	hash_data(buf, size);
}

/*
 * Calculate the number of bytes needed for an RLP length header.
 * NOTE: supports up to 16MB of data (how unlikely...)
 * FIXME: improve
 */
static int rlp_calculate_length(int length, uint8_t firstbyte)
{
	if (length == 1 && firstbyte <= 0x7f) {
		return 1;
	} else if (length <= 55) {
		return 1 + length;
	} else if (length <= 0xff) {
		return 2 + length;
	} else if (length <= 0xffff) {
		return 3 + length;
	} else {
		return 4 + length;
	}
}


static void send_request_chunk(void)
{
	int progress = 1000 - (data_total > 1000000
						   ? data_left / (data_total/800)
						   : data_left * 800 / data_total);
	layoutProgress("Signing", progress);
	resp.has_data_length = true;
	resp.data_length = data_left <= 1024 ? data_left : 1024;
	msg_write(MessageType_MessageType_EthereumTxRequest, &resp);
}

static int ethereum_is_canonic(uint8_t v, uint8_t signature[64])
{
	(void) signature;
	return (v & 2) == 0;
}

static void send_signature(void)
{
	uint8_t hash[32], sig[64];
	uint8_t v;
	layoutProgress("Signing", 1000);
	keccak_Final(&keccak_ctx, hash);
	if (ecdsa_sign_digest(&secp256k1, privkey, hash, sig, &v, ethereum_is_canonic) != 0) {
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

/* Format a 256 bit number (amount in wei) into a human readable format
 * using standard ethereum units.
 * The buffer must be at least 25 bytes.
 */
static void ethereumFormatAmount(bignum256 *val, char buffer[25])
{
	char value[25] = {0};
	char *value_ptr = value;

	// convert val into base 1000 for easy printing.
	uint16_t num[26];
	uint8_t last_used = 0;
	for (int i = 0; i < 26; i++) {
		uint32_t limb;
		bn_divmod1000(val, &limb);
		// limb is < 1000.
		num[i] = (uint16_t) limb;
		if (limb > 0) {
			last_used = i;
		}
	}
	
	if (last_used < 3) {
		// value is smaller than 1e9 wei => show value in wei
		for (int i = last_used; i >= 0; i--) {
			*value_ptr++ = '0' + (num[i] / 100) % 10;
			*value_ptr++ = '0' + (num[i] / 10) % 10;
			*value_ptr++ = '0' + (num[i]) % 10;
		}
		strcpy(value_ptr, " Wei");
		// value is at most 9 + 4 + 1 characters long
	} else if (last_used < 10) {
		// value is bigger than 1e9 wei and smaller than 1e12 ETH => show value in ETH
		int i = last_used;
		if (i < 6)
			i = 6;
		int end = i - 4;
		while (i >= end) {
			*value_ptr++ = '0' + (num[i] / 100) % 10;
			*value_ptr++ = '0' + (num[i] / 10) % 10;
			*value_ptr++ = '0' + (num[i]) % 10;
			if (i == 6)
				*value_ptr++ = '.';
			i--;
		}
		while (value_ptr[-1] == '0') // remove trailing zeros
			value_ptr--;
		// remove trailing dot.
		if (value_ptr[-1] == '.')
			value_ptr--;
		strcpy(value_ptr, " ETH");
		// value is at most 16 + 4 + 1 characters long
	} else {
		// value is bigger than 1e9 ETH => won't fit on display (probably won't happen unless you are Vitalik)
		strlcpy(value, "trillions of ETH", sizeof(value));
	}

	// skip leading zeroes
	value_ptr = value;
	while (*value_ptr == '0' && *(value_ptr + 1) >= '0' && *(value_ptr + 1) <= '9') {
		value_ptr++;
	}

	// copy to destination buffer
	strcpy(buffer, value_ptr);
}

static void layoutEthereumConfirmTx(const uint8_t *to, uint32_t to_len, const uint8_t *value, uint32_t value_len)
{
	bignum256 val;
	uint8_t pad_val[32];
	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - value_len), value, value_len);
	bn_read_be(pad_val, &val);

	char amount[25];
	if (bn_is_zero(&val)) {
		strcpy(amount, "message");
	} else {
		ethereumFormatAmount(&val, amount);
	}

	static char _to1[17] = {0};
	static char _to2[17] = {0};
	static char _to3[17] = {0};

	if (to_len) {
		strcpy(_to1, "to ");
		data2hex(to, 6, _to1 + 3);
		data2hex(to + 6, 7, _to2);
		data2hex(to + 13, 7, _to3);
		_to3[14] = '?'; _to3[15] = 0;
	} else {
		strlcpy(_to1, "to new contract?", sizeof(_to1));
		strlcpy(_to2, "", sizeof(_to2));
		strlcpy(_to3, "", sizeof(_to3));
	}

	layoutDialogSwipe(&bmp_icon_question,
		"Cancel",
		"Confirm",
		NULL,
		"Send",
		amount,
		_to1,
		_to2,
		_to3,
		NULL
	);
}

static void layoutEthereumData(const uint8_t *data, uint32_t len, uint32_t total_len)
{
	char hexdata[3][17];
	char summary[20];
	int i;
	uint32_t printed = 0;
	for (i = 0; i < 3; i++) {
		uint32_t linelen = len - printed;
		if (linelen > 8)
			linelen = 8;
		data2hex(data, linelen, hexdata[i]);
		data += linelen;
		printed += linelen;
	}

	strcpy(summary, "...          bytes");
	char *p = summary + 11;
	uint32_t number = total_len;
	while (number > 0) {
		*p-- = '0' + number % 10;
		number = number / 10;
	}
	char *summarystart = summary;
	if (total_len == printed)
		summarystart = summary + 4;

	layoutDialogSwipe(&bmp_icon_question,
		"Cancel",
		"Confirm",
		NULL,
		"Transaction data:",
		hexdata[0],
		hexdata[1],
		hexdata[2],
		summarystart,
		NULL
	);
}

static void layoutEthereumFee(const uint8_t *value, uint32_t value_len,
							  const uint8_t *gas_price, uint32_t gas_price_len,
							  const uint8_t *gas_limit, uint32_t gas_limit_len)
{
	bignum256 val, gas;
	uint8_t pad_val[32];
	char tx_value[25];
	char gas_value[25];

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - gas_price_len), gas_price, gas_price_len);
	bn_read_be(pad_val, &val);

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - gas_limit_len), gas_limit, gas_limit_len);
	bn_read_be(pad_val, &gas);
	bn_multiply(&val, &gas, &secp256k1.prime);

	ethereumFormatAmount(&gas, gas_value);

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - value_len), value, value_len);
	bn_read_be(pad_val, &val);

	if (bn_is_zero(&val)) {
		strcpy(tx_value, "message");
	} else {
		ethereumFormatAmount(&val, tx_value);
	}

	layoutDialogSwipe(&bmp_icon_question,
		"Cancel",
		"Confirm",
		NULL,
		"Really send",
		tx_value,
		"paying up to",
		gas_value,
		"for gas?",
		NULL
	);
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

static bool ethereum_signing_check(EthereumSignTx *msg)
{
	if (!msg->has_nonce || !msg->has_gas_price || !msg->has_gas_limit) {
		return false;
	}
	
	if (msg->to.size != 20 && msg->to.size != 0) {
		/* Address has wrong length */
		return false;
	}

	// sending transaction to address 0 (contract creation) without a data field
	if (msg->to.size == 0 && (!msg->has_data_length || msg->data_length == 0)) {
		return false;
	}

	if (msg->gas_price.size + msg->gas_limit.size  > 30) {
		// sanity check that fee doesn't overflow
		return false;
	}

	return true;
}

void ethereum_signing_init(EthereumSignTx *msg, const HDNode *node)
{
	ethereum_signing = true;
	sha3_256_Init(&keccak_ctx);

	memset(&resp, 0, sizeof(EthereumTxRequest));
	/* set fields to 0, to avoid conditions later */
	if (!msg->has_value)
		msg->value.size = 0;
	if (!msg->has_data_initial_chunk)
		msg->data_initial_chunk.size = 0;
	if (!msg->has_to)
		msg->to.size = 0;

	if (msg->has_data_length) {
		if (msg->data_length == 0) {
			fsm_sendFailure(FailureType_Failure_Other, "Invalid data length provided");
			ethereum_signing_abort();
			return;
		}
		if (!msg->has_data_initial_chunk || msg->data_initial_chunk.size == 0) {
			fsm_sendFailure(FailureType_Failure_Other, "Data length provided, but no initial chunk");
			ethereum_signing_abort();
			return;
		}
		/* Our encoding only supports transactions up to 2^24 bytes.  To
		 * prevent exceeding the limit we use a stricter limit on data length.
		 */
		if (msg->data_length > 16000000)  {
			fsm_sendFailure(FailureType_Failure_Other, "Data length exceeds limit");
			ethereum_signing_abort();
			return;
		}
		data_total = msg->data_length;
	} else {
		data_total = 0;
	}
	if (msg->data_initial_chunk.size > data_total) {
		fsm_sendFailure(FailureType_Failure_Other, "Invalid size of initial chunk");
		ethereum_signing_abort();
		return;
	}

	// safety checks
	if (!ethereum_signing_check(msg)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing aborted (safety check failed)");
		ethereum_signing_abort();
		return;
	}

	layoutEthereumConfirmTx(msg->to.bytes, msg->to.size, msg->value.bytes, msg->value.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled by user");
		ethereum_signing_abort();
		return;
	}

	if (data_total > 0) {
		layoutEthereumData(msg->data_initial_chunk.bytes, msg->data_initial_chunk.size, data_total);
		if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled by user");
			ethereum_signing_abort();
			return;
		}
	}

	layoutEthereumFee(msg->value.bytes, msg->value.size,
					  msg->gas_price.bytes, msg->gas_price.size,
					  msg->gas_limit.bytes, msg->gas_limit.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled by user");
		ethereum_signing_abort();
		return;
	}
	
	/* Stage 1: Calculate total RLP length */
	uint32_t rlp_length = 0;

	layoutProgress("Signing", 0);

	rlp_length += rlp_calculate_length(msg->nonce.size, msg->nonce.bytes[0]);
	rlp_length += rlp_calculate_length(msg->gas_price.size, msg->gas_price.bytes[0]);
	rlp_length += rlp_calculate_length(msg->gas_limit.size, msg->gas_limit.bytes[0]);
	rlp_length += rlp_calculate_length(msg->to.size, msg->to.bytes[0]);
	rlp_length += rlp_calculate_length(msg->value.size, msg->value.bytes[0]);
	rlp_length += rlp_calculate_length(data_total, msg->data_initial_chunk.bytes[0]);

	/* Stage 2: Store header fields */
	hash_rlp_list_length(rlp_length);

	layoutProgress("Signing", 100);

	hash_rlp_field(msg->nonce.bytes, msg->nonce.size);
	hash_rlp_field(msg->gas_price.bytes, msg->gas_price.size);
	hash_rlp_field(msg->gas_limit.bytes, msg->gas_limit.size);
	hash_rlp_field(msg->to.bytes, msg->to.size);
	hash_rlp_field(msg->value.bytes, msg->value.size);
	hash_rlp_length(data_total, msg->data_initial_chunk.bytes[0]);
	hash_data(msg->data_initial_chunk.bytes, msg->data_initial_chunk.size);
	data_left = data_total - msg->data_initial_chunk.size;

	memcpy(privkey, node->private_key, 32);

	if (data_left > 0) {
		send_request_chunk();
	} else {
		send_signature();
	}
}

void ethereum_signing_txack(EthereumTxAck *tx)
{
	if (!ethereum_signing) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Signing mode");
		layoutHome();
		return;
	}

	if (tx->data_chunk.size > data_left) {
		fsm_sendFailure(FailureType_Failure_Other, "Too much data");
		ethereum_signing_abort();
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
		send_request_chunk();
	} else {
		send_signature();
	}
}

void ethereum_signing_abort(void)
{
	if (ethereum_signing) {
		memset(privkey, 0, sizeof(privkey));
		layoutHome();
		ethereum_signing = false;
	}
}
