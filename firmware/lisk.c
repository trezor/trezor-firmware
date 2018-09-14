/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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
#include <stdio.h>

#include "lisk.h"
#include "curves.h"
#include "layout2.h"
#include "bitmaps.h"
#include "util.h"
#include "gettext.h"
#include "crypto.h"
#include "protect.h"
#include "messages.pb.h"

int hdnode_get_lisk_address(HDNode *node, char *address) {
	if (node->curve != get_curve_by_name(ED25519_NAME)) {
		return 0;
	}
	hdnode_fill_public_key(node);
	lisk_get_address_from_public_key(&node->public_key[1], address);
	return 1;
}

void lisk_get_address_from_public_key(const uint8_t* public_key, char *address) {
	uint8_t digest[32];
	uint8_t address_bytes[8];

	sha256_Raw(public_key, 32, digest);

	uint8_t i;
	for (i = 0; i < 8; i++) {
		address_bytes[i] = digest[ 7 - i];
	}

	uint64_t encodedAddress = 0;
	for (i = 0; i < 8; i++ ) {
		encodedAddress = encodedAddress << 8;
		encodedAddress += address_bytes[i];
	}

	bn_format_uint64(encodedAddress, NULL, "L", 0, 0, false, address, 23);
}

void lisk_message_hash(const uint8_t *message, size_t message_len, uint8_t hash[32]) {
	SHA256_CTX ctx;
	sha256_Init(&ctx);
	sha256_Update(&ctx, (const uint8_t *)"\x15" "Lisk Signed Message:\n", 22);
	uint8_t varint[5];
	uint32_t l = ser_length(message_len, varint);
	sha256_Update(&ctx, varint, l);
	sha256_Update(&ctx, message, message_len);
	sha256_Final(&ctx, hash);
	sha256_Raw(hash, 32, hash);
}

void lisk_sign_message(HDNode *node, LiskSignMessage *msg, LiskMessageSignature *resp)
{
	layoutSignMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	layoutProgressSwipe(_("Signing"), 0);

	uint8_t signature[64];
	uint8_t hash[32];
	lisk_message_hash(msg->message.bytes, msg->message.size, hash);

    ed25519_sign(hash, 32, node->private_key, &node->public_key[1], signature);

    memcpy(resp->signature.bytes, signature, sizeof(signature));
	memcpy(resp->public_key.bytes, &node->public_key[1], 32);

	resp->has_signature = true;
	resp->signature.size = 64;
	resp->has_public_key = true;
	resp->public_key.size = 32;
}

bool lisk_verify_message(LiskVerifyMessage *msg)
{
	uint8_t hash[32];
	lisk_message_hash(msg->message.bytes, msg->message.size, hash);

    return ed25519_sign_open(
        hash,
        32,
        msg->public_key.bytes,
        msg->signature.bytes
        ) == 0;
}

void lisk_update_raw_tx(HDNode *node, LiskSignTx *msg)
{
	if(!msg->transaction.has_sender_public_key) {
		memcpy(msg->transaction.sender_public_key.bytes, &node->public_key[1], 32);
	}

	// For CastVotes transactions, recipientId should be equal to transaction creator address.
	if(msg->transaction.type == LiskTransactionType_CastVotes && !msg->transaction.has_recipient_id) {
		char address[23];
		lisk_get_address_from_public_key(&node->public_key[1], address);
		memcpy(msg->transaction.recipient_id, address, sizeof(address));
		msg->transaction.has_recipient_id = true;
	}
}

void lisk_hashupdate_uint32(SHA256_CTX* ctx, uint32_t value)
{
	uint8_t data[4];
	write_le(data, value);
	sha256_Update(ctx, data, sizeof(data));
}

void lisk_hashupdate_uint64(SHA256_CTX* ctx, uint64_t value, bool i)
{
	uint8_t data[8];
	// i = true ? big-endian : little-endian
	data[i ? 0 : 7] = (value >> 56);
	data[i ? 1 : 6] = (value >> 48);
	data[i ? 2 : 5] = (value >> 40);
	data[i ? 3 : 4] = (value >> 32);
	data[i ? 4 : 3] = (value >> 24);
	data[i ? 5 : 2] = (value >> 16);
	data[i ? 6 : 1] = (value >> 8);
	data[i ? 7 : 0] = value;
	sha256_Update(ctx, data, sizeof(data));
}

void lisk_hashupdate_asset(SHA256_CTX* ctx, LiskTransactionType type, LiskTransactionAsset *asset)
{
	switch (type) {
		case LiskTransactionType_Transfer:
			if (asset->has_data) {
				sha256_Update(ctx, (const uint8_t *)asset->data, strlen(asset->data));
			}
		break;
		case LiskTransactionType_RegisterDelegate:
			if (asset->has_delegate && asset->delegate.has_username) {
				sha256_Update(ctx, (const uint8_t *)asset->delegate.username, strlen(asset->delegate.username));
			}
		break;
		case LiskTransactionType_CastVotes: {
			char str[asset->votes_count * 66];
			strlcpy(str, asset->votes[0], sizeof(str));
			for (int i = 1; i < asset->votes_count; i++) {
				strlcat(str, asset->votes[i], sizeof(str));
			};
			sha256_Update(ctx, (const uint8_t *)str, strlen(str));
		break;
		}
		case LiskTransactionType_RegisterSecondPassphrase:
			if (asset->has_signature && asset->signature.has_public_key) {
				sha256_Update(ctx, asset->signature.public_key.bytes, asset->signature.public_key.size);
			}
		break;
		case LiskTransactionType_RegisterMultisignatureAccount: {
			if (asset->has_multisignature) {
				char str[asset->multisignature.keys_group_count * 66 + 4 + 4];
				uint8_t min[4];
				uint8_t life_time[4];

				// convert uint32_t to uint8_t
				write_le(min, asset->multisignature.min);
				write_le(life_time, asset->multisignature.life_time);

				// calculate sha from min + life_time + keys_group
				strlcpy(str, (const char *)min, sizeof(str));
				strlcat(str, (const char *)life_time, sizeof(str));
				for (int i = 0; i < asset->multisignature.keys_group_count; i++) {
					strlcat(str, asset->multisignature.keys_group[i], sizeof(str));
				};

				sha256_Update(ctx, (const uint8_t *)str, strlen(str));
			}
		break;
		}
		default:
			fsm_sendFailure(FailureType_Failure_DataError, _("Invalid transaction type"));
		break;
	}
}

void lisk_format_value(uint64_t value, char *formated_value)
{
	bn_format_uint64(value, NULL, " LSK", 8, 0, false, formated_value, 20);
}

void liks_get_vote_txt(char *prefix, int num, char *txt, size_t size)
{
	char buffer[4];
	sprintf(buffer, "%d", num);

	strlcpy(txt, prefix, size);
	strlcat(txt, buffer, size);
	strlcat(txt, (num != 1) ? " votes" : " vote", size);
}

void lisk_sign_tx(HDNode *node, LiskSignTx *msg, LiskSignedTx *resp)
{
	lisk_update_raw_tx(node, msg);

	if(msg->has_transaction) {
		SHA256_CTX ctx;
		sha256_Init(&ctx);

		switch (msg->transaction.type) {
			case LiskTransactionType_Transfer:
				layoutRequireConfirmTx(msg->transaction.recipient_id, msg->transaction.amount);
			break;
			case LiskTransactionType_RegisterDelegate:
				layoutRequireConfirmDelegateRegistration(&msg->transaction.asset);
			break;
			case LiskTransactionType_CastVotes:
				layoutRequireConfirmCastVotes(&msg->transaction.asset);
			break;
			case LiskTransactionType_RegisterSecondPassphrase:
				layoutLiskPublicKey(msg->transaction.asset.signature.public_key.bytes );
			break;
			case LiskTransactionType_RegisterMultisignatureAccount:
				layoutRequireConfirmMultisig(&msg->transaction.asset);
			break;
			default:
				fsm_sendFailure(FailureType_Failure_DataError, _("Invalid transaction type"));
				layoutHome();
			break;
		}
		if (!protectButton((
			msg->transaction.type == LiskTransactionType_RegisterSecondPassphrase ?
				ButtonRequestType_ButtonRequest_PublicKey :
				ButtonRequestType_ButtonRequest_SignTx),
			false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing Canceled");
			layoutHome();
			return;
		}

		layoutRequireConfirmFee(msg->transaction.fee, msg->transaction.amount);
		if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing Canceled");
			layoutHome();
			return;
		}
		layoutProgressSwipe(_("Signing transaction"), 0);

		sha256_Update(&ctx, (const uint8_t *)&msg->transaction.type, 1);

		lisk_hashupdate_uint32(&ctx, msg->transaction.timestamp);

		sha256_Update(&ctx, msg->transaction.sender_public_key.bytes, 32);

		if (msg->transaction.has_requester_public_key) {
			sha256_Update(&ctx, msg->transaction.requester_public_key.bytes, msg->transaction.requester_public_key.size);
		}

		uint64_t recipient_id = 0;
		if (msg->transaction.has_recipient_id) {
			// parse integer from lisk address (string -> number)
			sscanf(msg->transaction.recipient_id, "%llu", (long long unsigned int *)&recipient_id );
		}
		lisk_hashupdate_uint64(&ctx, recipient_id, true);
		lisk_hashupdate_uint64(&ctx, msg->transaction.amount, false);

		lisk_hashupdate_asset(&ctx, msg->transaction.type, &msg->transaction.asset);

		// if signature exist calculate second signature
		if (msg->transaction.has_signature) {
			sha256_Update(&ctx, msg->transaction.signature.bytes, msg->transaction.signature.size);
		}

		uint8_t signature[64];
		uint8_t hash[32];

		sha256_Final(&ctx, hash);
    	ed25519_sign(hash, 32, node->private_key, &node->public_key[1], signature);

	    memcpy(resp->signature.bytes, signature, sizeof(signature));
		resp->has_signature = true;
		resp->signature.size = 64;
	}
}

// Layouts
void layoutLiskPublicKey(const uint8_t *pubkey)
{
	char hex[32 * 2 + 1], desc[13];
	strlcpy(desc, "Public Key:", sizeof(desc));
	data2hex(pubkey, 32, hex);
	const char **str = split_message((const uint8_t *)hex, 32 * 2, 16);
	layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
		desc, str[0], str[1], str[2], str[3], NULL);
}

void layoutLiskVerifyAddress(const char *address)
{
	const char **str = split_message((const uint8_t *)address, strlen(address), 10);
	layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
		_("Confirm address?"),
		_("Message signed by:"),
		str[0], str[1], NULL, NULL, NULL);
}

void layoutRequireConfirmTx(char *recipient_id, uint64_t amount)
{
	char formated_amount[20];
	const char **str = split_message((const uint8_t *)recipient_id, strlen(recipient_id), 16);
	lisk_format_value(amount, formated_amount);
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		NULL,
		_("Confirm sending"),
		formated_amount,
		_("to:"),
		str[0],
		str[1],
		NULL
	);
}

void layoutRequireConfirmFee(uint64_t fee, uint64_t amount)
{
	char formated_amount[20];
	char formated_fee[20];
	lisk_format_value(amount, formated_amount);
	lisk_format_value(fee, formated_fee);
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		NULL,
		_("Confirm transaction"),
		formated_amount,
		_("fee:"),
		formated_fee,
		NULL,
		NULL
	);
}

void layoutRequireConfirmDelegateRegistration(LiskTransactionAsset *asset)
{
	if (asset->has_delegate && asset->delegate.has_username) {
		const char **str = split_message((const uint8_t *)asset->delegate.username, strlen(asset->delegate.username), 20);
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
			NULL,
			_("Confirm transaction"),
			_("Do you really want to"),
			_("register a delegate?"),
			str[0],
			str[1],
			NULL
		);
	}
}

void layoutRequireConfirmCastVotes(LiskTransactionAsset *asset)
{
	uint8_t plus = 0;
	uint8_t minus = 0;
	char add_votes_txt[13];
	char remove_votes_txt[16];

	for (int i = 0; i < asset->votes_count; i++) {
		if (strncmp(asset->votes[i], "+", 1) == 0) {
			plus += 1;
		} else {
			minus += 1;
		}
	}

	liks_get_vote_txt("Add ", plus, add_votes_txt, sizeof(add_votes_txt));
	liks_get_vote_txt("Remove ", minus, remove_votes_txt, sizeof(remove_votes_txt));

	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		NULL,
		_("Confirm transaction"),
		add_votes_txt,
		remove_votes_txt,
		NULL,
		NULL,
		NULL
	);
}

void layoutRequireConfirmMultisig(LiskTransactionAsset *asset)
{
	char keys_group_str[22];
	char life_time_str[14];
	char min_str[8];
	char buffer[8];

	strlcpy(keys_group_str, "Keys group length: ", sizeof(keys_group_str));
	strlcpy(life_time_str, "Life time: ", sizeof(life_time_str));
	strlcpy(min_str, "Min: ", sizeof(min_str));

	sprintf(buffer, "%u", (unsigned int)asset->multisignature.keys_group_count);
	strlcat(keys_group_str, buffer, sizeof(keys_group_str));

	sprintf(buffer, "%u", (unsigned int)asset->multisignature.life_time);
	strlcat(life_time_str, buffer, sizeof(life_time_str));

	sprintf(buffer, "%u", (unsigned int)asset->multisignature.min);
	strlcat(min_str, buffer, sizeof(min_str));

	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		NULL,
		_("Confirm transaction"),
		keys_group_str,
		life_time_str,
		min_str,
		NULL,
		NULL
	);
}