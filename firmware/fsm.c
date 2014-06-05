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

#include "trezor.h"
#include "fsm.h"
#include "messages.h"
#include "bip32.h"
#include "storage.h"
#include "coins.h"
#include "debug.h"
#include "transaction.h"
#include "rng.h"
#include "storage.h"
#include "oled.h"
#include "protect.h"
#include "pinmatrix.h"
#include "layout2.h"
#include "ecdsa.h"
#include "reset.h"
#include "recovery.h"
#include "memory.h"
#include "usb.h"
#include "util.h"
#include "signing.h"

// message methods

static uint8_t msg_resp[MSG_OUT_SIZE];

#define RESP_INIT(TYPE) TYPE *resp = (TYPE *)msg_resp; memset(resp, 0, sizeof(TYPE));

void fsm_sendSuccess(const char *text)
{
	RESP_INIT(Success);
	if (text) {
		resp->has_message = true;
		strlcpy(resp->message, text, sizeof(resp->message));
	}
	msg_write(MessageType_MessageType_Success, resp);
}

void fsm_sendFailure(FailureType code, const char *text)
{
	if (protectAbortedByInitialize) {
		fsm_msgInitialize((Initialize *)0);
		protectAbortedByInitialize = false;
		return;
	}
	RESP_INIT(Failure);
	resp->has_code = true;
	resp->code = code;
	if (text) {
		resp->has_message = true;
		strlcpy(resp->message, text, sizeof(resp->message));
	}
	msg_write(MessageType_MessageType_Failure, resp);
}

HDNode *fsm_getRootNode(void)
{
	static HDNode node;
	if (!storage_getRootNode(&node)) {
		layoutHome();
		fsm_sendFailure(FailureType_Failure_NotInitialized, "Device not initialized or passphrase request cancelled");
		return 0;
	}
	return &node;
}

void fsm_deriveKey(HDNode *node, uint32_t *address_n, size_t address_n_count)
{
	size_t i;
	if (address_n_count > 3) {
		layoutProgressSwipe("Preparing keys", 0, 0);
	}
	for (i = 0; i < address_n_count; i++) {
		hdnode_private_ckd(node, address_n[i]);
		if (address_n_count > 3) {
			layoutProgress("Preparing keys", 1000 * i / address_n_count, i);
		}
	}
}

void fsm_msgInitialize(Initialize *msg)
{
	(void)msg;
	recovery_abort();
	signing_abort();
	RESP_INIT(Features);
	resp->has_vendor = true;         strlcpy(resp->vendor, "bitcointrezor.com", sizeof(resp->vendor));
	resp->has_major_version = true;  resp->major_version = VERSION_MAJOR;
	resp->has_minor_version = true;  resp->minor_version = VERSION_MINOR;
	resp->has_patch_version = true;  resp->patch_version = VERSION_PATCH;
	resp->has_device_id = true;      strlcpy(resp->device_id, storage_uuid_str, sizeof(resp->device_id));
	resp->has_pin_protection = true; resp->pin_protection = storage.has_pin;
	resp->has_passphrase_protection = true; resp->passphrase_protection = storage.has_passphrase_protection && storage.passphrase_protection;
#ifdef SCM_REVISION
	resp->has_revision = true; memcpy(resp->revision.bytes, SCM_REVISION, sizeof(resp->revision)); resp->revision.size = SCM_REVISION_LEN;
#endif
	resp->has_bootloader_hash = true; resp->bootloader_hash.size = memory_bootloader_hash(resp->bootloader_hash.bytes);
	if (storage.has_language) {
		resp->has_language = true;
		strlcpy(resp->language, storage.language, sizeof(resp->language));
	}
	if (storage.has_label) {
		resp->has_label = true;
		strlcpy(resp->label, storage.label, sizeof(resp->label));
	}
	resp->coins_count = COINS_COUNT;
	memcpy(resp->coins, coins, COINS_COUNT * sizeof(CoinType));
	resp->has_initialized = true; resp->initialized = storage_isInitialized();
	resp->has_imported = true; resp->imported = storage.has_imported && storage.imported;
	msg_write(MessageType_MessageType_Features, resp);
}

void fsm_msgPing(Ping *msg)
{
	RESP_INIT(Success);

	if (msg->has_button_protection && msg->button_protection) {
		layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "answer to ping?", NULL, NULL, NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "Ping cancelled");
			layoutHome();
			return;
		}
	}

	if (msg->has_pin_protection && msg->pin_protection) {
		if (!protectPin(true)) {
			layoutHome();
			return;
		}
	}

	if (msg->has_passphrase_protection && msg->passphrase_protection) {
		if (!protectPassphrase()) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "Ping cancelled");
			return;
		}
	}

	if (msg->has_message) {
		resp->has_message = true;
		memcpy(&(resp->message), &(msg->message), sizeof(resp->message));
	}
	msg_write(MessageType_MessageType_Success, resp);
	layoutHome();
}

void fsm_msgChangePin(ChangePin *msg)
{
	bool removal = msg->has_remove && msg->remove;
	if (removal) {
		if (storage_hasPin()) {
			layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "remove current PIN?", NULL, NULL, NULL, NULL);
		} else {
			fsm_sendSuccess("PIN removed");
			return;
		}
	} else {
		if (storage_hasPin()) {
			layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "change current PIN?", NULL, NULL, NULL, NULL);
		} else {
			layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "set new PIN?", NULL, NULL, NULL, NULL);
		}
	}
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, removal ? "PIN removal cancelled" : "PIN change cancelled");
		layoutHome();
		return;
	}
	if (!protectPin(false)) {
		layoutHome();
		return;
	}
	if (removal) {
		storage_setPin(0);
		fsm_sendSuccess("PIN removed");
	} else {
		if (protectChangePin()) {
			fsm_sendSuccess("PIN changed");
		} else {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, "PIN change failed");
		}
	}
	layoutHome();
}

void fsm_msgWipeDevice(WipeDevice *msg)
{
	(void)msg;
	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "wipe the device?", NULL, "All data will be lost.", NULL, NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_WipeDevice, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Wipe cancelled");
		layoutHome();
		return;
	}
	storage_reset();
	storage_reset_uuid();
	storage_commit();
	// the following does not work on Mac anyway :-/ Linux/Windows are fine, so it is not needed
	// usbReconnect(); // force re-enumeration because of the serial number change
	fsm_sendSuccess("Device wiped");
	layoutHome();
}

void fsm_msgFirmwareErase(FirmwareErase *msg)
{
	(void)msg;
	fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in bootloader mode");
}

void fsm_msgFirmwareUpload(FirmwareUpload *msg)
{
	(void)msg;
	fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in bootloader mode");
}

void fsm_msgGetEntropy(GetEntropy *msg)
{
	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "send entropy?", NULL, NULL, NULL, NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Entropy cancelled");
		layoutHome();
		return;
	}
	RESP_INIT(Entropy);
	uint32_t len = msg->size;
	if (len > 1024) {
		len = 1024;
	}
	resp->entropy.size = len;
	random_buffer(resp->entropy.bytes, len);
	msg_write(MessageType_MessageType_Entropy, resp);
	layoutHome();
}

void fsm_msgGetPublicKey(GetPublicKey *msg)
{
	RESP_INIT(PublicKey);

	HDNode *node = fsm_getRootNode();
	if (!node) return;

	fsm_deriveKey(node, msg->address_n, msg->address_n_count);

	resp->node.depth = node->depth;
	resp->node.fingerprint = node->fingerprint;
	resp->node.child_num = node->child_num;
	resp->node.chain_code.size = 32;
	memcpy(resp->node.chain_code.bytes, node->chain_code, 32);
	resp->node.has_private_key = false;
	resp->node.has_public_key = true;
	resp->node.public_key.size = 33;
	memcpy(resp->node.public_key.bytes, node->public_key, 33);

	msg_write(MessageType_MessageType_PublicKey, resp);
	layoutHome();
}

void fsm_msgLoadDevice(LoadDevice *msg)
{
	if (storage_isInitialized()) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Device is already initialized. Use Wipe first.");
		return;
	}

	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "I take the risk", NULL, "Loading private seed", "is not recommended.", "Continue only if you", "know what you are", "doing!", NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Load cancelled");
		layoutHome();
		return;
	}

	storage_loadDevice(msg);
	storage_commit();
	fsm_sendSuccess("Device loaded");
	layoutHome();
}

void fsm_msgResetDevice(ResetDevice *msg)
{
	if (storage_isInitialized()) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Device is already initialized. Use Wipe first.");
		return;
	}

	reset_init(
		msg->has_display_random && msg->display_random,
		msg->has_strength ? msg->strength : 128,
		msg->has_passphrase_protection && msg->passphrase_protection,
		msg->has_pin_protection && msg->pin_protection,
		msg->has_language ? msg->language : 0,
		msg->has_label ? msg->label : 0
	);
}

void fsm_msgSignTx(SignTx *msg)
{
	if (msg->inputs_count < 1) {
		fsm_sendFailure(FailureType_Failure_Other, "Transaction must have at least one input");
		layoutHome();
		return;
	}

	if (msg->outputs_count < 1) {
		fsm_sendFailure(FailureType_Failure_Other, "Transaction must have at least one output");
		layoutHome();
		return;
	}

	if (!protectPin(true)) {
		layoutHome();
		return;
	}

	HDNode *node = fsm_getRootNode();
	if (!node) return;
	const CoinType *coin = coinByName(msg->coin_name);
	if (!coin) {
		fsm_sendFailure(FailureType_Failure_Other, "Invalid coin name");
		layoutHome();
		return;
	}

	signing_init(msg->inputs_count, msg->outputs_count, coin, node);
}

void fsm_msgCancel(Cancel *msg)
{
	(void)msg;
	recovery_abort();
	signing_abort();
}

void fsm_msgTxAck(TxAck *msg)
{
	if (msg->has_tx) {
		signing_txack(&(msg->tx));
	} else {
		fsm_sendFailure(FailureType_Failure_SyntaxError, "No transaction provided");
	}
}

void fsm_msgApplySettings(ApplySettings *msg)
{
	if (msg->has_label && msg->has_language) {
		layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "change label to", msg->label, "and language to", msg->language, "?");
	} else
	if (msg->has_label) {
		layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "change label to", msg->label, "?", NULL, NULL);
	} else
	if (msg->has_language) {
		layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL, "Do you really want to", "change language to", msg->language, "?", NULL, NULL);
	} else {
		fsm_sendFailure(FailureType_Failure_SyntaxError, "No setting provided");
		return;
	}
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Apply settings cancelled");
		layoutHome();
		return;
	}
	if (!protectPin(true)) {
		layoutHome();
		return;
	}
	if (msg->has_label) {
		storage_setLabel(msg->label);
	}
	if (msg->has_language) {
		storage_setLanguage(msg->language);
	}
	storage_commit();
	fsm_sendSuccess("Settings applied");
	layoutHome();
}

void fsm_msgGetAddress(GetAddress *msg)
{
	RESP_INIT(Address);

	HDNode *node = fsm_getRootNode();
	if (!node) return;
	const CoinType *coin = coinByName(msg->coin_name);
	if (!coin) {
		fsm_sendFailure(FailureType_Failure_Other, "Invalid coin name");
		layoutHome();
		return;
	}

	fsm_deriveKey(node, msg->address_n, msg->address_n_count);

	ecdsa_get_address(node->public_key, coin->address_type, resp->address);

	msg_write(MessageType_MessageType_Address, resp);
	layoutHome();
}

void fsm_msgEntropyAck(EntropyAck *msg)
{
	if (msg->has_entropy) {
		reset_entropy(msg->entropy.bytes, msg->entropy.size);
	} else {
		reset_entropy(0, 0);
	}
}

void fsm_msgSignMessage(SignMessage *msg)
{
	RESP_INIT(MessageSignature);

	layoutSignMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "Sign message cancelled");
		layoutHome();
		return;
	}

	if (!protectPin(true)) {
		layoutHome();
		return;
	}

	HDNode *node = fsm_getRootNode();
	if (!node) return;
	const CoinType *coin = coinByName(msg->coin_name);
	if (!coin) {
		fsm_sendFailure(FailureType_Failure_Other, "Invalid coin name");
		layoutHome();
		return;
	}

	fsm_deriveKey(node, msg->address_n, msg->address_n_count);

	ecdsa_get_address(node->public_key, coin->address_type, resp->address);
	if (transactionMessageSign(msg->message.bytes, msg->message.size, node->private_key, resp->address, resp->signature.bytes)) {
		resp->has_address = true;
		resp->has_signature = true;
		resp->signature.size = 65;
		msg_write(MessageType_MessageType_MessageSignature, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_Other, "Error signing message");
	}
	layoutHome();
}

void fsm_msgVerifyMessage(VerifyMessage *msg)
{
	const char *address = msg->has_address ? msg->address : 0;
	if (msg->signature.size == 65 && transactionMessageVerify(msg->message.bytes, msg->message.size, msg->signature.bytes, address)) {
		layoutVerifyMessage(msg->message.bytes, msg->message.size);
		protectButton(ButtonRequestType_ButtonRequest_Other, true);
		fsm_sendSuccess("Message verified");
	} else {
		fsm_sendFailure(FailureType_Failure_InvalidSignature, "Invalid signature");
	}
	layoutHome();
}

void fsm_msgEstimateTxSize(EstimateTxSize *msg)
{
	RESP_INIT(TxSize);
	resp->has_tx_size = true;
	resp->tx_size = transactionEstimateSize(msg->inputs_count, msg->outputs_count);
	msg_write(MessageType_MessageType_TxSize, resp);
}

void fsm_msgRecoveryDevice(RecoveryDevice *msg)
{
	if (storage_isInitialized()) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Device is already initialized. Use Wipe first.");
		return;
	}
	recovery_init(
		msg->has_word_count ? msg->word_count : 12,
		msg->has_passphrase_protection && msg->passphrase_protection,
		msg->has_pin_protection && msg->pin_protection,
		msg->has_language ? msg->language : 0,
		msg->has_label ? msg->label : 0,
		msg->has_enforce_wordlist ? msg->enforce_wordlist : false
	);
}

void fsm_msgWordAck(WordAck *msg)
{
	recovery_word(msg->word);
}

#if DEBUG_LINK

void fsm_msgDebugLinkGetState(DebugLinkGetState *msg)
{
	(void)msg;
	RESP_INIT(DebugLinkState);

	resp->has_layout = true;
	resp->layout.size = OLED_BUFSIZE;
	memcpy(resp->layout.bytes, oledGetBuffer(), OLED_BUFSIZE);

	if (storage.has_pin) {
		resp->has_pin = true;
		strlcpy(resp->pin, storage.pin, sizeof(resp->pin));
	}

	resp->has_matrix = true;
	strlcpy(resp->matrix, pinmatrix_get(), sizeof(resp->matrix));

	resp->has_reset_entropy = true;
	resp->reset_entropy.size = reset_get_int_entropy(resp->reset_entropy.bytes);

	resp->has_reset_word = true;
	strlcpy(resp->reset_word, reset_get_word(), sizeof(resp->reset_word));

	resp->has_recovery_fake_word = true;
	strlcpy(resp->recovery_fake_word, recovery_get_fake_word(), sizeof(resp->recovery_fake_word));

	resp->has_recovery_word_pos = true;
	resp->recovery_word_pos = recovery_get_word_pos();

	if (storage.has_mnemonic) {
		resp->has_mnemonic = true;
		strlcpy(resp->mnemonic, storage.mnemonic, sizeof(resp->mnemonic));
	}

	if (storage.has_node) {
		resp->has_node = true;
		memcpy(&(resp->node), &(storage.node), sizeof(HDNode));
	}

	resp->has_passphrase_protection = true;
	resp->passphrase_protection = storage.has_passphrase_protection && storage.passphrase_protection;

	msg_debug_write(MessageType_MessageType_DebugLinkState, resp);
}

void fsm_msgDebugLinkStop(DebugLinkStop *msg)
{
	(void)msg;
}

#endif
