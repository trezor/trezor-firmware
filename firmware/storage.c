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
#include <stdint.h>

#include <libopencm3/stm32/flash.h>

#include "messages.pb.h"
#include "storage.pb.h"

#include "trezor.h"
#include "sha2.h"
#include "aes.h"
#include "pbkdf2.h"
#include "bip32.h"
#include "bip39.h"
#include "util.h"
#include "memory.h"
#include "rng.h"
#include "storage.h"
#include "debug.h"
#include "protect.h"
#include "layout2.h"

Storage storage;

uint8_t storage_uuid[12];
char    storage_uuid_str[25];

static bool   sessionRootNodeCached;
static HDNode sessionRootNode;

static bool sessionPinCached;
static char sessionPin[17];

static bool sessionPassphraseCached;
static char sessionPassphrase[51];

/*
 storage layout:

 offset | type/length |  description
--------+-------------+-------------------------------
 0x0000 |  4 bytes    |  magic = 'stor'
 0x0004 |  12 bytes   |  uuid
 0x0010 |  ?          |  Storage structure
 */

#define STORAGE_VERSION 2

void storage_from_flash(uint32_t version)
{
	switch (version) {
		case 1: // copy
			memcpy(&storage, (void *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid)), sizeof(Storage));
			break;
		case 2: // copy
			memcpy(&storage, (void *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid)), sizeof(Storage));
			break;
	}
	storage.version = STORAGE_VERSION;
}

void storage_init(void)
{
	storage_reset();
	// if magic is ok
	if (memcmp((void *)FLASH_STORAGE_START, "stor", 4) == 0) {
		// load uuid
		memcpy(storage_uuid, (void *)(FLASH_STORAGE_START + 4), sizeof(storage_uuid));
		data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);
		// load storage struct
		uint32_t version = ((Storage *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid)))->version;
		if (version && version <= STORAGE_VERSION) {
			storage_from_flash(version);
		}
		if (version != STORAGE_VERSION) {
			storage_commit();
		}
	} else {
		storage_reset_uuid();
		storage_commit();
	}
}

void storage_reset_uuid(void)
{
	// set random uuid
	random_buffer(storage_uuid, sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);
}

void storage_reset(void)
{
	// reset storage struct
	memset(&storage, 0, sizeof(storage));
	storage.version = STORAGE_VERSION;
	session_clear();
}

void session_clear(void)
{
	sessionRootNodeCached = false;   memset(&sessionRootNode, 0, sizeof(sessionRootNode));
	sessionPassphraseCached = false; memset(&sessionPassphrase, 0, sizeof(sessionPassphrase));
	sessionPinCached = false;        memset(&sessionPin, 0, sizeof(sessionPin));
}

static uint8_t meta_backup[FLASH_META_LEN];

void storage_commit(void)
{
	int i;
	uint32_t *w;
	// backup meta
	memcpy(meta_backup, (void *)FLASH_META_START, FLASH_META_LEN);
	flash_clear_status_flags();
	flash_unlock();
	// erase storage
	for (i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
		flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
	}
	// modify storage
	memcpy(meta_backup + FLASH_META_DESC_LEN, "stor", 4);
	memcpy(meta_backup + FLASH_META_DESC_LEN + 4, storage_uuid, sizeof(storage_uuid));
	memcpy(meta_backup + FLASH_META_DESC_LEN + 4 + sizeof(storage_uuid), &storage, sizeof(Storage));
	// copy it back
	for (i = 0; i < FLASH_META_LEN / 4; i++) {
		w = (uint32_t *)(meta_backup + i * 4);
		flash_program_word(FLASH_META_START + i * 4, *w);
	}
	flash_lock();
	// flash operation failed
	if (FLASH_SR & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR | FLASH_SR_WRPERR)) {
		layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Storage failure", "detected.", NULL, "Please unplug", "the device.", NULL);
		for (;;) { }
	}
}

void storage_loadDevice(LoadDevice *msg)
{
	storage_reset();

	storage.has_imported = true;
	storage.imported = true;

	if (msg->has_pin > 0) {
		storage_setPin(msg->pin);
	}

	if (msg->has_passphrase_protection) {
		storage.has_passphrase_protection = true;
		storage.passphrase_protection = msg->passphrase_protection;
	} else {
		storage.has_passphrase_protection = false;
	}

	if (msg->has_node) {
		storage.has_node = true;
		storage.has_mnemonic = false;
		memcpy(&storage.node, &(msg->node), sizeof(HDNodeType));
		sessionRootNodeCached = false;
		memset(&sessionRootNode, 0, sizeof(sessionRootNode));
	} else if (msg->has_mnemonic) {
		storage.has_mnemonic = true;
		storage.has_node = false;
		strlcpy(storage.mnemonic, msg->mnemonic, sizeof(storage.mnemonic));
		sessionRootNodeCached = false;
		memset(&sessionRootNode, 0, sizeof(sessionRootNode));
	}

	if (msg->has_language) {
		storage_setLanguage(msg->language);
	}

	if (msg->has_label) {
		storage_setLabel(msg->label);
	}
}

void storage_setLabel(const char *label)
{
	if (!label) return;
	storage.has_label = true;
	strlcpy(storage.label, label, sizeof(storage.label));
}

void storage_setLanguage(const char *lang)
{
	if (!lang) return;
	// sanity check
	if (strcmp(lang, "english") == 0) {
		storage.has_language = true;
		strlcpy(storage.language, lang, sizeof(storage.language));
	}
}

void storage_setPassphraseProtection(bool passphrase_protection)
{
	sessionRootNodeCached = false;
	sessionPassphraseCached = false;

	storage.has_passphrase_protection = true;
	storage.passphrase_protection = passphrase_protection;
}

void get_root_node_callback(uint32_t iter, uint32_t total)
{
	layoutProgress("Waking up", 1000 * iter / total);
}

bool storage_getRootNode(HDNode *node)
{
	// root node is properly cached
	if (sessionRootNodeCached) {
		memcpy(node, &sessionRootNode, sizeof(HDNode));
		return true;
	}

	// if storage has node, decrypt and use it
	if (storage.has_node) {
		if (!protectPassphrase()) {
			return false;
		}
		if (hdnode_from_xprv(storage.node.depth, storage.node.fingerprint, storage.node.child_num, storage.node.chain_code.bytes, storage.node.private_key.bytes, &sessionRootNode) == 0) {
			return false;
		}
		if (storage.has_passphrase_protection && storage.passphrase_protection && strlen(sessionPassphrase)) {
			// decrypt hd node
			uint8_t secret[64];
			layoutProgressSwipe("Waking up", 0);
			pbkdf2_hmac_sha512((const uint8_t *)sessionPassphrase, strlen(sessionPassphrase), (uint8_t *)"TREZORHD", 8, BIP39_PBKDF2_ROUNDS, secret, 64, get_root_node_callback);
			aes_decrypt_ctx ctx;
			aes_decrypt_key256(secret, &ctx);
			aes_cbc_decrypt(sessionRootNode.chain_code, sessionRootNode.chain_code, 32, secret + 32, &ctx);
			aes_cbc_decrypt(sessionRootNode.private_key, sessionRootNode.private_key, 32, secret + 32, &ctx);
		}
		memcpy(node, &sessionRootNode, sizeof(HDNode));
		sessionRootNodeCached = true;
		return true;
	}

	// if storage has mnemonic, convert it to node and use it
	if (storage.has_mnemonic) {
		if (!protectPassphrase()) {
			return false;
		}
		uint8_t seed[64];
		layoutProgressSwipe("Waking up", 0);
		mnemonic_to_seed(storage.mnemonic, sessionPassphrase, seed, get_root_node_callback); // BIP-0039
		if (hdnode_from_seed(seed, sizeof(seed), &sessionRootNode) == 0) {
			return false;
		}
		memcpy(node, &sessionRootNode, sizeof(HDNode));
		sessionRootNodeCached = true;
		return true;
	}

	return false;
}

const char *storage_getLabel(void)
{
	return storage.has_label ? storage.label : 0;
}

const char *storage_getLanguage(void)
{
	return storage.has_language ? storage.language : 0;
}

bool storage_isPinCorrect(const char *pin)
{
	return strcmp(storage.pin, pin) == 0;
}

bool storage_hasPin(void)
{
	return storage.has_pin && strlen(storage.pin) > 0;
}

void storage_setPin(const char *pin)
{
	if (pin && strlen(pin) > 0) {
		storage.has_pin = true;
		strlcpy(storage.pin, pin, sizeof(storage.pin));
	} else {
		storage.has_pin = false;
		storage.pin[0] = 0;
	}
	storage_commit();
	sessionPinCached = false;
}

void session_cachePassphrase(const char *passphrase)
{
	strlcpy(sessionPassphrase, passphrase, sizeof(sessionPassphrase));
	sessionPassphraseCached = true;
}

bool session_isPassphraseCached(void)
{
	return sessionPassphraseCached;
}

void session_cachePin(const char *pin)
{
	strlcpy(sessionPin, pin, sizeof(sessionPin));
	sessionPinCached = true;
}

bool session_isPinCached(void)
{
	return sessionPinCached && strcmp(sessionPin, storage.pin) == 0;
}

void storage_resetPinFails(void)
{
	storage.has_pin_failed_attempts = true;
	storage.pin_failed_attempts = 0;
	storage_commit();
}

void storage_increasePinFails(void)
{
	if (!storage.has_pin_failed_attempts) {
		storage.has_pin_failed_attempts = true;
		storage.pin_failed_attempts = 1;
	} else {
		storage.pin_failed_attempts++;
	}
	storage_commit();
}

uint32_t storage_getPinFails(void)
{
	storage_from_flash(STORAGE_VERSION); // reload from flash
	return storage.has_pin_failed_attempts ? storage.pin_failed_attempts : 0;
}

bool storage_isInitialized(void)
{
	return storage.has_node || storage.has_mnemonic;
}
