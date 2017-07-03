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
#include "address.h"
#include "base58.h"
#include "ecdsa.h"
#include "reset.h"
#include "recovery.h"
#include "memory.h"
#include "usb.h"
#include "util.h"
#include "signing.h"
#include "aes.h"
#include "hmac.h"
#include "crypto.h"
#include "base58.h"
#include "bip39.h"
#include "ripemd160.h"
#include "curves.h"
#include "secp256k1.h"
#include <libopencm3/stm32/flash.h>
#include "ethereum.h"
#include "gettext.h"

// message methods

static uint8_t msg_resp[MSG_OUT_SIZE] __attribute__ ((aligned));

#define RESP_INIT(TYPE) \
			TYPE *resp = (TYPE *) (void *) msg_resp; \
			_Static_assert(sizeof(msg_resp) >= sizeof(TYPE), #TYPE " is too large"); \
			memset(resp, 0, sizeof(TYPE));

#define CHECK_INITIALIZED \
	if (!storage_isInitialized()) { \
		fsm_sendFailure(FailureType_Failure_NotInitialized, NULL); \
		return; \
	}

#define CHECK_NOT_INITIALIZED \
	if (storage_isInitialized()) { \
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, _("Device is already initialized. Use Wipe first.")); \
		return; \
	}

#define CHECK_PIN \
	if (!protectPin(true)) { \
		layoutHome(); \
		return; \
	}

#define CHECK_PIN_UNCACHED \
	if (!protectPin(false)) { \
		layoutHome(); \
		return; \
	}

#define CHECK_PARAM(cond, errormsg) \
	if (!(cond)) { \
		fsm_sendFailure(FailureType_Failure_DataError, (errormsg)); \
		layoutHome(); \
		return; \
	}

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
	if (!text) {
		switch (code) {
			case FailureType_Failure_UnexpectedMessage:
				text = _("Unexpected message");
				break;
			case FailureType_Failure_ButtonExpected:
				text = _("Button expected");
				break;
			case FailureType_Failure_DataError:
				text = _("Data error");
				break;
			case FailureType_Failure_ActionCancelled:
				text = _("Action cancelled by user");
				break;
			case FailureType_Failure_PinExpected:
				text = _("PIN expected");
				break;
			case FailureType_Failure_PinCancelled:
				text = _("PIN cancelled");
				break;
			case FailureType_Failure_PinInvalid:
				text = _("PIN invalid");
				break;
			case FailureType_Failure_InvalidSignature:
				text = _("Invalid signature");
				break;
			case FailureType_Failure_ProcessError:
				text = _("Process error");
				break;
			case FailureType_Failure_NotEnoughFunds:
				text = _("Not enough funds");
				break;
			case FailureType_Failure_NotInitialized:
				text = _("Device not initialized");
				break;
			case FailureType_Failure_FirmwareError:
				text = _("Firmware error");
				break;
		}
	}
	if (text) {
		resp->has_message = true;
		strlcpy(resp->message, text, sizeof(resp->message));
	}
	msg_write(MessageType_MessageType_Failure, resp);
}

const CoinType *fsm_getCoin(bool has_name, const char *name)
{
	const CoinType *coin;
	if (has_name) {
		coin = coinByName(name);
	} else {
		coin = coinByName("Bitcoin");
	}
	if (!coin) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid coin name"));
		layoutHome();
		return 0;
	}
	return coin;
}

HDNode *fsm_getDerivedNode(const char *curve, uint32_t *address_n, size_t address_n_count)
{
	static HDNode node;
	if (!storage_getRootNode(&node, curve, true)) {
		fsm_sendFailure(FailureType_Failure_NotInitialized, _("Device not initialized or passphrase request cancelled or unsupported curve"));
		layoutHome();
		return 0;
	}
	if (!address_n || address_n_count == 0) {
		return &node;
	}
	if (hdnode_private_ckd_cached(&node, address_n, address_n_count, NULL) == 0) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to derive private key"));
		layoutHome();
		return 0;
	}
	return &node;
}

void fsm_msgInitialize(Initialize *msg)
{
	(void)msg;
	recovery_abort();
	signing_abort();
	session_clear(false); // do not clear PIN
	layoutHome();
	fsm_msgGetFeatures(0);
}

void fsm_msgGetFeatures(GetFeatures *msg)
{
	(void)msg;
	RESP_INIT(Features);
	resp->has_vendor = true;         strlcpy(resp->vendor, "bitcointrezor.com", sizeof(resp->vendor));
	resp->has_major_version = true;  resp->major_version = VERSION_MAJOR;
	resp->has_minor_version = true;  resp->minor_version = VERSION_MINOR;
	resp->has_patch_version = true;  resp->patch_version = VERSION_PATCH;
	resp->has_device_id = true;      strlcpy(resp->device_id, storage_uuid_str, sizeof(resp->device_id));
	resp->has_pin_protection = true; resp->pin_protection = storage.has_pin;
	resp->has_passphrase_protection = true; resp->passphrase_protection = storage.has_passphrase_protection && storage.passphrase_protection;
#ifdef SCM_REVISION
	int len = sizeof(SCM_REVISION) - 1;
	resp->has_revision = true; memcpy(resp->revision.bytes, SCM_REVISION, len); resp->revision.size = len;
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
	resp->has_pin_cached = true; resp->pin_cached = session_isPinCached();
	resp->has_passphrase_cached = true; resp->passphrase_cached = session_isPassphraseCached();
	resp->has_needs_backup = true; resp->needs_backup = storage_needsBackup();
	msg_write(MessageType_MessageType_Features, resp);
}

void fsm_msgPing(Ping *msg)
{
	RESP_INIT(Success);

	if (msg->has_button_protection && msg->button_protection) {
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("answer to ping?"), NULL, NULL, NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	if (msg->has_pin_protection && msg->pin_protection) {
		CHECK_PIN
	}

	if (msg->has_passphrase_protection && msg->passphrase_protection) {
		if (!protectPassphrase()) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
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
			layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("remove current PIN?"), NULL, NULL, NULL, NULL);
		} else {
			fsm_sendSuccess(_("PIN removed"));
			return;
		}
	} else {
		if (storage_hasPin()) {
			layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("change current PIN?"), NULL, NULL, NULL, NULL);
		} else {
			layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("set new PIN?"), NULL, NULL, NULL, NULL);
		}
	}
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN_UNCACHED

	if (removal) {
		storage_setPin(0);
		fsm_sendSuccess(_("PIN removed"));
	} else {
		if (protectChangePin()) {
			fsm_sendSuccess(_("PIN changed"));
		} else {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		}
	}
	layoutHome();
}

void fsm_msgWipeDevice(WipeDevice *msg)
{
	(void)msg;
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("wipe the device?"), NULL, _("All data will be lost."), NULL, NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_WipeDevice, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	storage_reset();
	storage_reset_uuid();
	storage_commit();
	storage_clearPinArea();
	// the following does not work on Mac anyway :-/ Linux/Windows are fine, so it is not needed
	// usbReconnect(); // force re-enumeration because of the serial number change
	fsm_sendSuccess(_("Device wiped"));
	layoutHome();
}

void fsm_msgGetEntropy(GetEntropy *msg)
{
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("send entropy?"), NULL, NULL, NULL, NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
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

	CHECK_INITIALIZED

	CHECK_PIN

	const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
	if (!coin) return;

	const char *curve = SECP256K1_NAME;
	if (msg->has_ecdsa_curve_name) {
		curve = msg->ecdsa_curve_name;
	}
	uint32_t fingerprint;
	HDNode *node;
	if (msg->address_n_count == 0) {
		/* get master node */
		fingerprint = 0;
		node = fsm_getDerivedNode(curve, msg->address_n, 0);
	} else {
		/* get parent node */
		node = fsm_getDerivedNode(curve, msg->address_n, msg->address_n_count - 1);
		if (!node) return;
		fingerprint = hdnode_fingerprint(node);
		/* get child */
		hdnode_private_ckd(node, msg->address_n[msg->address_n_count - 1]);
	}
	hdnode_fill_public_key(node);

	if (msg->has_show_display && msg->show_display) {
		layoutPublicKey(node->public_key);
		if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	resp->node.depth = node->depth;
	resp->node.fingerprint = fingerprint;
	resp->node.child_num = node->child_num;
	resp->node.chain_code.size = 32;
	memcpy(resp->node.chain_code.bytes, node->chain_code, 32);
	resp->node.has_private_key = false;
	resp->node.has_public_key = true;
	resp->node.public_key.size = 33;
	memcpy(resp->node.public_key.bytes, node->public_key, 33);
	if (node->public_key[0] == 1) {
		/* ed25519 public key */
		resp->node.public_key.bytes[0] = 0;
	}
	resp->has_xpub = true;
	hdnode_serialize_public(node, fingerprint, coin->xpub_magic, resp->xpub, sizeof(resp->xpub));
	msg_write(MessageType_MessageType_PublicKey, resp);
	layoutHome();
}

void fsm_msgLoadDevice(LoadDevice *msg)
{
	CHECK_NOT_INITIALIZED

	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("I take the risk"), NULL, _("Loading private seed"), _("is not recommended."), _("Continue only if you"), _("know what you are"), _("doing!"), NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	if (msg->has_mnemonic && !(msg->has_skip_checksum && msg->skip_checksum) ) {
		if (!mnemonic_check(msg->mnemonic)) {
			fsm_sendFailure(FailureType_Failure_DataError, _("Mnemonic with wrong checksum provided"));
			layoutHome();
			return;
		}
	}

	storage_loadDevice(msg);
	storage_commit();
	fsm_sendSuccess(_("Device loaded"));
	layoutHome();
}

void fsm_msgResetDevice(ResetDevice *msg)
{
	CHECK_NOT_INITIALIZED

	CHECK_PARAM(!msg->has_strength || msg->strength == 128 || msg->strength == 192 || msg->strength == 256, _("Invalid seed strength"));

	reset_init(
		msg->has_display_random && msg->display_random,
		msg->has_strength ? msg->strength : 128,
		msg->has_passphrase_protection && msg->passphrase_protection,
		msg->has_pin_protection && msg->pin_protection,
		msg->has_language ? msg->language : 0,
		msg->has_label ? msg->label : 0,
		msg->has_u2f_counter ? msg->u2f_counter : 0,
		msg->has_skip_backup ? msg->skip_backup : false
	);
}

void fsm_msgBackupDevice(BackupDevice *msg)
{
	CHECK_INITIALIZED

	(void)msg;
	reset_backup(true);
}

void fsm_msgSignTx(SignTx *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->inputs_count > 0, _("Transaction must have at least one input"));
	CHECK_PARAM(msg->outputs_count > 0, _("Transaction must have at least one output"));

	CHECK_PIN

	const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
	if (!coin) return;
	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, 0, 0);
	if (!node) return;

	signing_init(msg->inputs_count, msg->outputs_count, coin, node, msg->version, msg->lock_time);
}

void fsm_msgTxAck(TxAck *msg)
{
	CHECK_PARAM(msg->has_tx, _("No transaction provided"));

	signing_txack(&(msg->tx));
}

void fsm_msgCancel(Cancel *msg)
{
	(void)msg;
	recovery_abort();
	signing_abort();
	ethereum_signing_abort();
	fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
}

void fsm_msgEthereumSignTx(EthereumSignTx *msg)
{
	CHECK_INITIALIZED

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;

	ethereum_signing_init(msg, node);
}

void fsm_msgEthereumTxAck(EthereumTxAck *msg)
{
	ethereum_signing_txack(msg);
}

void fsm_msgCipherKeyValue(CipherKeyValue *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_key, _("No key provided"));
	CHECK_PARAM(msg->has_value, _("No value provided"));
	CHECK_PARAM(msg->value.size % 16 == 0, _("Value length must be a multiple of 16"));

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;

	bool encrypt = msg->has_encrypt && msg->encrypt;
	bool ask_on_encrypt = msg->has_ask_on_encrypt && msg->ask_on_encrypt;
	bool ask_on_decrypt = msg->has_ask_on_decrypt && msg->ask_on_decrypt;
	if ((encrypt && ask_on_encrypt) || (!encrypt && ask_on_decrypt)) {
		layoutCipherKeyValue(encrypt, msg->key);
		if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	uint8_t data[256 + 4];
	strlcpy((char *)data, msg->key, sizeof(data));
	strlcat((char *)data, ask_on_encrypt ? "E1" : "E0", sizeof(data));
	strlcat((char *)data, ask_on_decrypt ? "D1" : "D0", sizeof(data));

	hmac_sha512(node->private_key, 32, data, strlen((char *)data), data);

	RESP_INIT(CipheredKeyValue);
	if (encrypt) {
		aes_encrypt_ctx ctx;
		aes_encrypt_key256(data, &ctx);
		aes_cbc_encrypt(msg->value.bytes, resp->value.bytes, msg->value.size, ((msg->iv.size == 16) ? (msg->iv.bytes) : (data + 32)), &ctx);
	} else {
		aes_decrypt_ctx ctx;
		aes_decrypt_key256(data, &ctx);
		aes_cbc_decrypt(msg->value.bytes, resp->value.bytes, msg->value.size, ((msg->iv.size == 16) ? (msg->iv.bytes) : (data + 32)), &ctx);
	}
	resp->has_value = true;
	resp->value.size = msg->value.size;
	msg_write(MessageType_MessageType_CipheredKeyValue, resp);
	layoutHome();
}

void fsm_msgClearSession(ClearSession *msg)
{
	(void)msg;
	session_clear(true); // clear PIN as well
	layoutScreensaver();
	fsm_sendSuccess(_("Session cleared"));
}

void fsm_msgApplySettings(ApplySettings *msg)
{
	CHECK_PARAM(msg->has_label || msg->has_language || msg->has_use_passphrase || msg->has_homescreen, _("No setting provided"));

	CHECK_PIN

	if (msg->has_label) {
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("change label to"), msg->label, "?", NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}
	if (msg->has_language) {
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("change language to"), msg->language, "?", NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}
	if (msg->has_use_passphrase) {
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), msg->use_passphrase ? _("enable passphrase") : _("disable passphrase"), _("encryption?"), NULL, NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}
	if (msg->has_homescreen) {
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you really want to"), _("change the home"), _("screen?"), NULL, NULL, NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	if (msg->has_label) {
		storage_setLabel(msg->label);
	}
	if (msg->has_language) {
		storage_setLanguage(msg->language);
	}
	if (msg->has_use_passphrase) {
		storage_setPassphraseProtection(msg->use_passphrase);
	}
	if (msg->has_homescreen) {
		storage_setHomescreen(msg->homescreen.bytes, msg->homescreen.size);
	}
	storage_commit();
	fsm_sendSuccess(_("Settings applied"));
	layoutHome();
}

void fsm_msgGetAddress(GetAddress *msg)
{
	RESP_INIT(Address);

	CHECK_INITIALIZED

	CHECK_PIN

	const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
	if (!coin) return;
	HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;
	hdnode_fill_public_key(node);

	layoutProgress(_("Computing address"), 0);
	if (!compute_address(coin, msg->script_type, node, msg->has_multisig, &msg->multisig, resp->address)) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Can't encode address"));
		layoutHome();
		return;
	}

	if (msg->has_show_display && msg->show_display) {
		char desc[16];
		if (msg->has_multisig) {
			strlcpy(desc, "Msig __ of __:", sizeof(desc));
			const uint32_t m = msg->multisig.m;
			const uint32_t n = msg->multisig.pubkeys_count;
			desc[5] = (m < 10) ? ' ': ('0' + (m / 10));
			desc[6] = '0' + (m % 10);
			desc[11] = (n < 10) ? ' ': ('0' + (n / 10));
			desc[12] = '0' + (n % 10);
		} else {
			strlcpy(desc, _("Address:"), sizeof(desc));
		}
		layoutAddress(resp->address, desc);
		if (!protectButton(ButtonRequestType_ButtonRequest_Address, true)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	msg_write(MessageType_MessageType_Address, resp);
	layoutHome();
}

void fsm_msgEthereumGetAddress(EthereumGetAddress *msg)
{
	RESP_INIT(EthereumAddress);

	CHECK_INITIALIZED

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;

	resp->address.size = 20;

	if (!hdnode_get_ethereum_pubkeyhash(node, resp->address.bytes))
		return;

	if (msg->has_show_display && msg->show_display) {
		char desc[16];
		strlcpy(desc, "Address:", sizeof(desc));

		char address[41];
		data2hex(resp->address.bytes, 20, address);

		layoutAddress(address, desc);
		if (!protectButton(ButtonRequestType_ButtonRequest_Address, true)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	msg_write(MessageType_MessageType_EthereumAddress, resp);
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

	CHECK_INITIALIZED

	layoutSignMessage(msg->message.bytes, msg->message.size);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
	if (!coin) return;
	HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;

	layoutProgressSwipe(_("Signing"), 0);
	if (cryptoMessageSign(coin, node, msg->message.bytes, msg->message.size, resp->signature.bytes) == 0) {
		resp->has_address = true;
		hdnode_get_address(node, coin->address_type, resp->address, sizeof(resp->address));
		resp->has_signature = true;
		resp->signature.size = 65;
		msg_write(MessageType_MessageType_MessageSignature, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error signing message"));
	}
	layoutHome();
}

void fsm_msgVerifyMessage(VerifyMessage *msg)
{
	CHECK_PARAM(msg->has_address, _("No address provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));

	const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
	if (!coin) return;
	uint8_t addr_raw[MAX_ADDR_RAW_SIZE];
	uint32_t address_type;
	if (!coinExtractAddressType(coin, msg->address, &address_type) || !ecdsa_address_decode(msg->address, address_type, addr_raw)) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid address"));
		return;
	}
	layoutProgressSwipe(_("Verifying"), 0);
	if (msg->signature.size == 65 && cryptoMessageVerify(coin, msg->message.bytes, msg->message.size, address_type, addr_raw, msg->signature.bytes) == 0) {
		layoutVerifyAddress(msg->address);
		if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
		layoutVerifyMessage(msg->message.bytes, msg->message.size);
		if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
		fsm_sendSuccess(_("Message verified"));
	} else {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
	}
	layoutHome();
}

void fsm_msgSignIdentity(SignIdentity *msg)
{
	RESP_INIT(SignedIdentity);

	CHECK_INITIALIZED

	layoutSignIdentity(&(msg->identity), msg->has_challenge_visual ? msg->challenge_visual : 0);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	uint8_t hash[32];
	if (!msg->has_identity || cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
		layoutHome();
		return;
	}

	uint32_t address_n[5];
	address_n[0] = 0x80000000 | 13;
	address_n[1] = 0x80000000 | hash[ 0] | (hash[ 1] << 8) | (hash[ 2] << 16) | (hash[ 3] << 24);
	address_n[2] = 0x80000000 | hash[ 4] | (hash[ 5] << 8) | (hash[ 6] << 16) | (hash[ 7] << 24);
	address_n[3] = 0x80000000 | hash[ 8] | (hash[ 9] << 8) | (hash[10] << 16) | (hash[11] << 24);
	address_n[4] = 0x80000000 | hash[12] | (hash[13] << 8) | (hash[14] << 16) | (hash[15] << 24);

	const char *curve = SECP256K1_NAME;
	if (msg->has_ecdsa_curve_name) {
		curve = msg->ecdsa_curve_name;
	}
	HDNode *node = fsm_getDerivedNode(curve, address_n, 5);
	if (!node) return;

	bool sign_ssh = msg->identity.has_proto && (strcmp(msg->identity.proto, "ssh") == 0);
	bool sign_gpg = msg->identity.has_proto && (strcmp(msg->identity.proto, "gpg") == 0);

	int result = 0;
	layoutProgressSwipe(_("Signing"), 0);
	if (sign_ssh) { // SSH does not sign visual challenge
		result = sshMessageSign(node, msg->challenge_hidden.bytes, msg->challenge_hidden.size, resp->signature.bytes);
	} else if (sign_gpg) { // GPG should sign a message digest
		result = gpgMessageSign(node, msg->challenge_hidden.bytes, msg->challenge_hidden.size, resp->signature.bytes);
	} else {
		uint8_t digest[64];
		sha256_Raw(msg->challenge_hidden.bytes, msg->challenge_hidden.size, digest);
		sha256_Raw((const uint8_t *)msg->challenge_visual, strlen(msg->challenge_visual), digest + 32);
		result = cryptoMessageSign(&(coins[0]), node, digest, 64, resp->signature.bytes);
	}

	if (result == 0) {
		hdnode_fill_public_key(node);
		if (strcmp(curve, SECP256K1_NAME) != 0) {
			resp->has_address = false;
		} else {
			resp->has_address = true;
			hdnode_get_address(node, 0x00, resp->address, sizeof(resp->address)); // hardcoded Bitcoin address type
		}
		resp->has_public_key = true;
		resp->public_key.size = 33;
		memcpy(resp->public_key.bytes, node->public_key, 33);
		if (node->public_key[0] == 1) {
			/* ed25519 public key */
			resp->public_key.bytes[0] = 0;
		}
		resp->has_signature = true;
		resp->signature.size = 65;
		msg_write(MessageType_MessageType_SignedIdentity, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error signing identity"));
	}
	layoutHome();
}

void fsm_msgGetECDHSessionKey(GetECDHSessionKey *msg)
{
	RESP_INIT(ECDHSessionKey);

	CHECK_INITIALIZED

	layoutDecryptIdentity(&msg->identity);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}

	CHECK_PIN

	uint8_t hash[32];
	if (!msg->has_identity || cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
		fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
		layoutHome();
		return;
	}

	uint32_t address_n[5];
	address_n[0] = 0x80000000 | 17;
	address_n[1] = 0x80000000 | hash[ 0] | (hash[ 1] << 8) | (hash[ 2] << 16) | (hash[ 3] << 24);
	address_n[2] = 0x80000000 | hash[ 4] | (hash[ 5] << 8) | (hash[ 6] << 16) | (hash[ 7] << 24);
	address_n[3] = 0x80000000 | hash[ 8] | (hash[ 9] << 8) | (hash[10] << 16) | (hash[11] << 24);
	address_n[4] = 0x80000000 | hash[12] | (hash[13] << 8) | (hash[14] << 16) | (hash[15] << 24);

	const char *curve = SECP256K1_NAME;
	if (msg->has_ecdsa_curve_name) {
		curve = msg->ecdsa_curve_name;
	}

	const HDNode *node = fsm_getDerivedNode(curve, address_n, 5);
	if (!node) return;

	int result_size = 0;
	if (hdnode_get_shared_key(node, msg->peer_public_key.bytes, resp->session_key.bytes, &result_size) == 0) {
		resp->has_session_key = true;
		resp->session_key.size = result_size;
		msg_write(MessageType_MessageType_ECDHSessionKey, resp);
	} else {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error getting ECDH session key"));
	}
	layoutHome();
}

/* ECIES disabled
void fsm_msgEncryptMessage(EncryptMessage *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_pubkey, _("No public key provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));
	CHECK_PARAM(msg->pubkey.size == 33, _("Invalid public key provided"));
	curve_point pubkey;
	CHECK_PARAM(ecdsa_read_pubkey(&secp256k1, msg->pubkey.bytes, &pubkey) == 1, _("Invalid public key provided"));

	bool display_only = msg->has_display_only && msg->display_only;
	bool signing = msg->address_n_count > 0;
	RESP_INIT(EncryptedMessage);
	const HDNode *node = 0;
	uint8_t address_raw[MAX_ADDR_RAW_SIZE];
	if (signing) {
		const CoinType *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
		if (!coin) return;

		CHECK_PIN

		node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
		if (!node) return;
		hdnode_get_address_raw(node, coin->address_type, address_raw);
	}
	layoutEncryptMessage(msg->message.bytes, msg->message.size, signing);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	layoutProgressSwipe(_("Encrypting"), 0);
	if (cryptoMessageEncrypt(&pubkey, msg->message.bytes, msg->message.size, display_only, resp->nonce.bytes, &(resp->nonce.size), resp->message.bytes, &(resp->message.size), resp->hmac.bytes, &(resp->hmac.size), signing ? node->private_key : 0, signing ? address_raw : 0) != 0) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Error encrypting message"));
		layoutHome();
		return;
	}
	resp->has_nonce = true;
	resp->has_message = true;
	resp->has_hmac = true;
	msg_write(MessageType_MessageType_EncryptedMessage, resp);
	layoutHome();
}

void fsm_msgDecryptMessage(DecryptMessage *msg)
{
	CHECK_INITIALIZED

	CHECK_PARAM(msg->has_nonce, _("No nonce provided"));
	CHECK_PARAM(msg->has_message, _("No message provided"));
	CHECK_PARAM(msg->has_hmac, _("No message hmac provided"));

	CHECK_PARAM(msg->nonce.size == 33, _("Invalid nonce key provided"));
	curve_point nonce_pubkey;
	CHECK_PARAM(ecdsa_read_pubkey(&secp256k1, msg->nonce.bytes, &nonce_pubkey) == 1, _("Invalid nonce provided"));

	CHECK_PIN

	const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n, msg->address_n_count);
	if (!node) return;

	layoutProgressSwipe(_("Decrypting"), 0);
	RESP_INIT(DecryptedMessage);
	bool display_only = false;
	bool signing = false;
	uint8_t address_raw[MAX_ADDR_RAW_SIZE];
	if (cryptoMessageDecrypt(&nonce_pubkey, msg->message.bytes, msg->message.size, msg->hmac.bytes, msg->hmac.size, node->private_key, resp->message.bytes, &(resp->message.size), &display_only, &signing, address_raw) != 0) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	if (signing) {
		base58_encode_check(address_raw, 21, resp->address, sizeof(resp->address));
	}
	layoutDecryptMessage(resp->message.bytes, resp->message.size, signing ? resp->address : 0);
	protectButton(ButtonRequestType_ButtonRequest_Other, true);
	if (display_only) {
		resp->has_address = false;
		resp->has_message = false;
		memset(resp->address, 0, sizeof(resp->address));
		memset(&(resp->message), 0, sizeof(resp->message));
	} else {
		resp->has_address = signing;
		resp->has_message = true;
	}
	msg_write(MessageType_MessageType_DecryptedMessage, resp);
	layoutHome();
}
*/

void fsm_msgRecoveryDevice(RecoveryDevice *msg)
{
	const bool dry_run = msg->has_dry_run ? msg->dry_run : false;
	if (dry_run) {
		CHECK_PIN
	} else {
		CHECK_NOT_INITIALIZED
	}

	CHECK_PARAM(!msg->has_word_count || msg->word_count == 12 || msg->word_count == 18 || msg->word_count == 24, _("Invalid word count"));

	recovery_init(
		msg->has_word_count ? msg->word_count : 12,
		msg->has_passphrase_protection && msg->passphrase_protection,
		msg->has_pin_protection && msg->pin_protection,
		msg->has_language ? msg->language : 0,
		msg->has_label ? msg->label : 0,
		msg->has_enforce_wordlist && msg->enforce_wordlist,
		msg->has_type ? msg->type : 0,
		msg->has_u2f_counter ? msg->u2f_counter : 0,
		dry_run
	);
}

void fsm_msgWordAck(WordAck *msg)
{
	recovery_word(msg->word);
}

void fsm_msgSetU2FCounter(SetU2FCounter *msg)
{
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL, _("Do you want to set"), _("the U2F counter?"), NULL, NULL, NULL, NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
		layoutHome();
		return;
	}
	storage_setU2FCounter(msg->u2f_counter);
	fsm_sendSuccess(_("U2F counter set"));
	layoutHome();
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

void fsm_msgDebugLinkMemoryRead(DebugLinkMemoryRead *msg)
{
	RESP_INIT(DebugLinkMemory);

	uint32_t length = 1024;
	if (msg->has_length && msg->length < length)
		length = msg->length;
	resp->has_memory = true;
	memcpy(resp->memory.bytes, (void*) msg->address, length);
	resp->memory.size = length;
	msg_debug_write(MessageType_MessageType_DebugLinkMemory, resp);
}

void fsm_msgDebugLinkMemoryWrite(DebugLinkMemoryWrite *msg)
{
	uint32_t length = msg->memory.size;
	if (msg->flash) {
		flash_clear_status_flags();
		flash_unlock();
		for (unsigned int i = 0; i < length; i += 4) {
			uint32_t word;
			memcpy(&word, msg->memory.bytes + i, 4);
			flash_program_word(msg->address + i, word);
		}
		flash_lock();
	} else {
		memcpy((void *) msg->address, msg->memory.bytes, length);
	}
}

void fsm_msgDebugLinkFlashErase(DebugLinkFlashErase *msg)
{
	flash_clear_status_flags();
	flash_unlock();
	flash_erase_sector(msg->sector, FLASH_CR_PROGRAM_X32);
	flash_lock();
}
#endif
