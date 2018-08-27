/*
 * This file is part of the TREZOR project, https://trezor.io/
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
#include "address.h"
#include "util.h"
#include "gettext.h"
#include "ethereum_tokens.h"
#include "ethereum_networks.h"
#include "memzero.h"
#include "messages.pb.h"

/* maximum supported chain id.  v must fit in an uint32_t. */
#define MAX_CHAIN_ID 2147483629

static bool ethereum_signing = false;
static uint32_t data_total, data_left;
static EthereumTxRequest msg_tx_request;
static CONFIDENTIAL uint8_t privkey[32];
static uint32_t chain_id;
static uint32_t tx_type;
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
 * Push an RLP encoded number to the hash buffer.
 * Ethereum yellow paper says to convert to big endian and strip leading zeros.
 */
static void hash_rlp_number(uint32_t number)
{
	if (!number) {
		return;
	}
	uint8_t data[4];
	data[0] = (number >> 24) & 0xff;
	data[1] = (number >> 16) & 0xff;
	data[2] = (number >> 8) & 0xff;
	data[3] = (number) & 0xff;
	int offset = 0;
	while (!data[offset]) {
		offset++;
	}
	hash_rlp_field(data + offset, 4 - offset);
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
	layoutProgress(_("Signing"), progress);
	msg_tx_request.has_data_length = true;
	msg_tx_request.data_length = data_left <= 1024 ? data_left : 1024;
	msg_write(MessageType_MessageType_EthereumTxRequest, &msg_tx_request);
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
	layoutProgress(_("Signing"), 1000);

	/* eip-155 replay protection */
	if (chain_id) {
		/* hash v=chain_id, r=0, s=0 */
		hash_rlp_number(chain_id);
		hash_rlp_length(0, 0);
		hash_rlp_length(0, 0);
	}

	keccak_Final(&keccak_ctx, hash);
	if (ecdsa_sign_digest(&secp256k1, privkey, hash, sig, &v, ethereum_is_canonic) != 0) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
		ethereum_signing_abort();
		return;
	}

	memzero(privkey, sizeof(privkey));

	/* Send back the result */
	msg_tx_request.has_data_length = false;

	msg_tx_request.has_signature_v = true;
	if (chain_id > MAX_CHAIN_ID) {
		msg_tx_request.signature_v = v;
	} else if (chain_id) {
		msg_tx_request.signature_v = v + 2 * chain_id + 35;
	} else {
		msg_tx_request.signature_v = v + 27;
	}

	msg_tx_request.has_signature_r = true;
	msg_tx_request.signature_r.size = 32;
	memcpy(msg_tx_request.signature_r.bytes, sig, 32);

	msg_tx_request.has_signature_s = true;
	msg_tx_request.signature_s.size = 32;
	memcpy(msg_tx_request.signature_s.bytes, sig + 32, 32);

	msg_write(MessageType_MessageType_EthereumTxRequest, &msg_tx_request);

	ethereum_signing_abort();
}
/* Format a 256 bit number (amount in wei) into a human readable format
 * using standard ethereum units.
 * The buffer must be at least 25 bytes.
 */
static void ethereumFormatAmount(const bignum256 *amnt, const TokenType *token, char *buf, int buflen)
{
	bignum256 bn1e9;
	bn_read_uint32(1000000000, &bn1e9);
	const char *suffix = NULL;
	int decimals = 18;
	if (token == UnknownToken) {
		strlcpy(buf, "Unknown token value", buflen);
		return;
	} else
	if (token != NULL) {
		suffix = token->ticker;
		decimals = token->decimals;
	} else
	if (bn_is_less(amnt, &bn1e9)) {
		suffix = " Wei";
		decimals = 0;
	} else {
		if (tx_type == 1 || tx_type == 6) {
			suffix = " WAN";
		} else {
			ASSIGN_ETHEREUM_SUFFIX(suffix, chain_id);
		}
	}
	bn_format(amnt, NULL, suffix, decimals, 0, false, buf, buflen);
}

static void layoutEthereumConfirmTx(const uint8_t *to, uint32_t to_len, const uint8_t *value, uint32_t value_len, const TokenType *token)
{
	bignum256 val;
	uint8_t pad_val[32];
	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - value_len), value, value_len);
	bn_read_be(pad_val, &val);

	char amount[32];
	if (token == NULL) {
		if (bn_is_zero(&val)) {
			strcpy(amount, _("message"));
		} else {
			ethereumFormatAmount(&val, NULL, amount, sizeof(amount));
		}
	} else {
		ethereumFormatAmount(&val, token, amount, sizeof(amount));
	}

	char _to1[] = "to 0x__________";
	char _to2[] = "_______________";
	char _to3[] = "_______________?";

	if (to_len) {
		char to_str[41];

		bool rskip60 = false;
		// constants from trezor-common/defs/ethereum/networks.json
		switch (chain_id) {
			case 30: rskip60 = true; break;
			case 31: rskip60 = true; break;
		}

		ethereum_address_checksum(to, to_str, rskip60, chain_id);
		memcpy(_to1 + 5, to_str, 10);
		memcpy(_to2, to_str + 10, 15);
		memcpy(_to3, to_str + 25, 15);
	} else {
		strlcpy(_to1, _("to new contract?"), sizeof(_to1));
		strlcpy(_to2, "", sizeof(_to2));
		strlcpy(_to3, "", sizeof(_to3));
	}

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Send"),
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
	uint32_t printed = 0;
	for (int i = 0; i < 3; i++) {
		uint32_t linelen = len - printed;
		if (linelen > 8) {
			linelen = 8;
		}
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
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Transaction data:"),
		hexdata[0],
		hexdata[1],
		hexdata[2],
		summarystart,
		NULL
	);
}

static void layoutEthereumFee(const uint8_t *value, uint32_t value_len,
							  const uint8_t *gas_price, uint32_t gas_price_len,
							  const uint8_t *gas_limit, uint32_t gas_limit_len,
							  bool is_token)
{
	bignum256 val, gas;
	uint8_t pad_val[32];
	char tx_value[32];
	char gas_value[32];

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - gas_price_len), gas_price, gas_price_len);
	bn_read_be(pad_val, &val);

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - gas_limit_len), gas_limit, gas_limit_len);
	bn_read_be(pad_val, &gas);
	bn_multiply(&val, &gas, &secp256k1.prime);

	ethereumFormatAmount(&gas, NULL, gas_value, sizeof(gas_value));

	memset(pad_val, 0, sizeof(pad_val));
	memcpy(pad_val + (32 - value_len), value, value_len);
	bn_read_be(pad_val, &val);

	if (bn_is_zero(&val)) {
		strcpy(tx_value, is_token ? _("token") : _("message"));
	} else {
		ethereumFormatAmount(&val, NULL, tx_value, sizeof(tx_value));
	}

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Really send"),
		tx_value,
		_("paying up to"),
		gas_value,
		_("for gas?"),
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
	if (!msg->has_gas_price || !msg->has_gas_limit) {
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

	memset(&msg_tx_request, 0, sizeof(EthereumTxRequest));
	/* set fields to 0, to avoid conditions later */
	if (!msg->has_value)
		msg->value.size = 0;
	if (!msg->has_data_initial_chunk)
		msg->data_initial_chunk.size = 0;
	if (!msg->has_to)
		msg->to.size = 0;
	if (!msg->has_nonce)
		msg->nonce.size = 0;

	/* eip-155 chain id */
	if (msg->has_chain_id) {
		if (msg->chain_id < 1) {
			fsm_sendFailure(FailureType_Failure_DataError, _("Chain Id out of bounds"));
			ethereum_signing_abort();
			return;
		}
		chain_id = msg->chain_id;
	} else {
		chain_id = 0;
	}

	/* Wanchain txtype */
	if (msg->has_tx_type) {
		if (msg->tx_type == 1 || msg->tx_type == 6) {
			tx_type = msg->tx_type;
		} else {
			fsm_sendFailure(FailureType_Failure_DataError, _("Txtype out of bounds"));
			ethereum_signing_abort();
			return;
		}
	} else {
		tx_type = 0;
	}

	if (msg->has_data_length && msg->data_length > 0) {
		if (!msg->has_data_initial_chunk || msg->data_initial_chunk.size == 0) {
			fsm_sendFailure(FailureType_Failure_DataError, _("Data length provided, but no initial chunk"));
			ethereum_signing_abort();
			return;
		}
		/* Our encoding only supports transactions up to 2^24 bytes.  To
		 * prevent exceeding the limit we use a stricter limit on data length.
		 */
		if (msg->data_length > 16000000)  {
			fsm_sendFailure(FailureType_Failure_DataError, _("Data length exceeds limit"));
			ethereum_signing_abort();
			return;
		}
		data_total = msg->data_length;
	} else {
		data_total = 0;
	}
	if (msg->data_initial_chunk.size > data_total) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid size of initial chunk"));
		ethereum_signing_abort();
		return;
	}

	// safety checks
	if (!ethereum_signing_check(msg)) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Safety check failed"));
		ethereum_signing_abort();
		return;
	}

	const TokenType *token = NULL;

	// detect ERC-20 token
	if (msg->to.size == 20 && msg->value.size == 0 && data_total == 68 && msg->data_initial_chunk.size == 68
	    && memcmp(msg->data_initial_chunk.bytes, "\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 16) == 0) {
		token = tokenByChainAddress(chain_id, msg->to.bytes);
	}

	if (token != NULL) {
		layoutEthereumConfirmTx(msg->data_initial_chunk.bytes + 16, 20, msg->data_initial_chunk.bytes + 36, 32, token);
	} else {
		layoutEthereumConfirmTx(msg->to.bytes, msg->to.size, msg->value.bytes, msg->value.size, NULL);
	}

	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		ethereum_signing_abort();
		return;
	}

	if (token == NULL && data_total > 0) {
		layoutEthereumData(msg->data_initial_chunk.bytes, msg->data_initial_chunk.size, data_total);
		if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			ethereum_signing_abort();
			return;
		}
	}

	layoutEthereumFee(msg->value.bytes, msg->value.size,
					  msg->gas_price.bytes, msg->gas_price.size,
					  msg->gas_limit.bytes, msg->gas_limit.size, token != NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		ethereum_signing_abort();
		return;
	}
	
	/* Stage 1: Calculate total RLP length */
	uint32_t rlp_length = 0;

	layoutProgress(_("Signing"), 0);

	rlp_length += rlp_calculate_length(msg->nonce.size, msg->nonce.bytes[0]);
	rlp_length += rlp_calculate_length(msg->gas_price.size, msg->gas_price.bytes[0]);
	rlp_length += rlp_calculate_length(msg->gas_limit.size, msg->gas_limit.bytes[0]);
	rlp_length += rlp_calculate_length(msg->to.size, msg->to.bytes[0]);
	rlp_length += rlp_calculate_length(msg->value.size, msg->value.bytes[0]);
	rlp_length += rlp_calculate_length(data_total, msg->data_initial_chunk.bytes[0]);
	if (tx_type) {
		rlp_length += rlp_calculate_length(1, tx_type);
	}
	if (chain_id) {
		int length = chain_id < 0x100 ? 1: chain_id < 0x10000 ? 2: chain_id < 0x1000000 ? 3 : 4;
		rlp_length += rlp_calculate_length(length, chain_id);
		rlp_length += rlp_calculate_length(0, 0);
		rlp_length += rlp_calculate_length(0, 0);
	}

	/* Stage 2: Store header fields */
	hash_rlp_list_length(rlp_length);

	layoutProgress(_("Signing"), 100);

	if (tx_type) {
		hash_rlp_number(tx_type);
	}
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
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, _("Not in Ethereum signing mode"));
		layoutHome();
		return;
	}

	if (tx->data_chunk.size > data_left) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Too much data"));
		ethereum_signing_abort();
		return;
	}

	if (data_left > 0 && (!tx->has_data_chunk || tx->data_chunk.size == 0)) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Empty data chunk received"));
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
		memzero(privkey, sizeof(privkey));
		layoutHome();
		ethereum_signing = false;
	}
}

static void ethereum_message_hash(const uint8_t *message, size_t message_len, uint8_t hash[32])
{
	struct SHA3_CTX ctx;
	sha3_256_Init(&ctx);
	sha3_Update(&ctx, (const uint8_t *)"\x19" "Ethereum Signed Message:\n", 26);
	uint8_t c;
	if (message_len > 1000000000) { c = '0' + message_len / 1000000000 % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 100000000)  { c = '0' + message_len / 100000000  % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 10000000)   { c = '0' + message_len / 10000000   % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 1000000)    { c = '0' + message_len / 1000000    % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 100000)     { c = '0' + message_len / 100000     % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 10000)      { c = '0' + message_len / 10000      % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 1000)       { c = '0' + message_len / 1000       % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 100)        { c = '0' + message_len / 100        % 10; sha3_Update(&ctx, &c, 1); }
	if (message_len > 10)         { c = '0' + message_len / 10         % 10; sha3_Update(&ctx, &c, 1); }
	                                c = '0' + message_len              % 10; sha3_Update(&ctx, &c, 1);
	sha3_Update(&ctx, message, message_len);
	keccak_Final(&ctx, hash);
}

void ethereum_message_sign(EthereumSignMessage *msg, const HDNode *node, EthereumMessageSignature *resp)
{
	uint8_t hash[32];

	if (!hdnode_get_ethereum_pubkeyhash(node, resp->address.bytes)) {
		return;
	}
	resp->has_address = true;
	resp->address.size = 20;
	ethereum_message_hash(msg->message.bytes, msg->message.size, hash);

	uint8_t v;
	if (ecdsa_sign_digest(&secp256k1, node->private_key, hash, resp->signature.bytes, &v, ethereum_is_canonic) != 0) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
		return;
	}

	resp->has_signature = true;
	resp->signature.bytes[64] = 27 + v;
	resp->signature.size = 65;
	msg_write(MessageType_MessageType_EthereumMessageSignature, resp);
}

int ethereum_message_verify(EthereumVerifyMessage *msg)
{
	if (msg->signature.size != 65 || msg->address.size != 20) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Malformed data"));
		return 1;
	}

	uint8_t pubkey[65];
	uint8_t hash[32];

	ethereum_message_hash(msg->message.bytes, msg->message.size, hash);

	/* v should be 27, 28 but some implementations use 0,1.  We are
	 * compatible with both.
	 */
	uint8_t v = msg->signature.bytes[64];
	if (v >= 27) {
		v -= 27;
	}
	if (v >= 2 ||
		ecdsa_verify_digest_recover(&secp256k1, pubkey, msg->signature.bytes, hash, v) != 0) {
		return 2;
	}

	struct SHA3_CTX ctx;
	sha3_256_Init(&ctx);
	sha3_Update(&ctx, pubkey + 1, 64);
	keccak_Final(&ctx, hash);

	/* result are the least significant 160 bits */
	if (memcmp(msg->address.bytes, hash + 12, 20) != 0) {
		return 2;
	}
	return 0;
}
