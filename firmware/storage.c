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
#include "curves.h"
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

/*
 storage layout:

 offset | type/length |  description
--------+-------------+-------------------------------
 0x0000 |   4 bytes   |  magic = 'stor'
 0x0004 |  12 bytes   |  uuid
 0x0010 |  ?          |  Storage structure
 0x4000 |   4 kbytes  |  area for pin failures
 0x5000 |  12 kbytes  |  reserved

The area for pin failures looks like this:
0 ... 0 pinfail 0xffffffff .. 0xffffffff
The pinfail is a binary number of the form 1...10...0,
the number of zeros is the number of pin failures.
This layout is used because we can only clear bits without 
erasing the flash.

 */

#define FLASH_STORAGE_PINAREA     (FLASH_META_START + 0x4000)
#define FLASH_STORAGE_PINAREA_LEN (0x1000)
#define FLASH_STORAGE_REALLEN (4 + sizeof(storage_uuid) + sizeof(Storage))
_Static_assert(FLASH_STORAGE_START + FLASH_STORAGE_REALLEN <= FLASH_STORAGE_PINAREA, "Storage struct is too large for TREZOR flash");
_Static_assert((sizeof(storage_uuid) & 3) == 0, "storage uuid unaligned");
_Static_assert((sizeof(storage) & 3) == 0, "storage unaligned");

static bool sessionSeedCached, sessionSeedUsesPassphrase;

static uint8_t sessionSeed[64];

static bool sessionPinCached;

static bool sessionPassphraseCached;
static char sessionPassphrase[51];

#define STORAGE_VERSION 6

void storage_check_flash_errors(void)
{
	// flash operation failed
	if (FLASH_SR & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR | FLASH_SR_WRPERR)) {
		layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Storage failure", "detected.", NULL, "Please unplug", "the device.", NULL);
		for (;;) { }
	}
}

bool storage_from_flash(void)
{
	if (memcmp((void *)FLASH_STORAGE_START, "stor", 4) != 0) {
		// wrong magic
		return false;
	}

	uint32_t version = ((Storage *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid)))->version;
	// version 1: since 1.0.0
	// version 2: since 1.2.1
	// version 3: since 1.3.1
	// version 4: since 1.3.2
	// version 5: since 1.3.3
	// version 6: since 1.3.6
	if (version > STORAGE_VERSION) {
		// downgrade -> clear storage
		return false;
	}

	// load uuid
	memcpy(storage_uuid, (void *)(FLASH_STORAGE_START + 4), sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);
	// copy storage
	memcpy(&storage, (void *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid)), sizeof(Storage));
	if (version <= 5) {
		// convert PIN failure counter from version 5 format
		uint32_t pinctr = storage.has_pin_failed_attempts
			? storage.pin_failed_attempts : 0;
		if (pinctr > 31)
			pinctr = 31;
		flash_clear_status_flags();
		flash_unlock();
		// erase extra storage sector
		flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
		flash_program_word(FLASH_STORAGE_PINAREA, 0xffffffff << pinctr);
		flash_lock();
		storage_check_flash_errors();
		storage.has_pin_failed_attempts = false;
		storage.pin_failed_attempts = 0;
	}
	// upgrade storage version
	if (version != STORAGE_VERSION) {
		storage.version = STORAGE_VERSION;
		storage_commit();
	}
	return true;
}

void storage_init(void)
{
	if (!storage_from_flash()) {
		storage_reset();
		storage_reset_uuid();
		storage_commit();
		storage_clearPinArea();
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
	session_clear(true); // clear PIN as well
}

void session_clear(bool clear_pin)
{
	sessionSeedCached = false;
	memset(&sessionSeed, 0, sizeof(sessionSeed));
	sessionPassphraseCached = false;
	memset(&sessionPassphrase, 0, sizeof(sessionPassphrase));
	if (clear_pin) {
		sessionPinCached = false;
	}
}

static uint32_t storage_flash_words(uint32_t addr, uint32_t *src, int nwords) {
	int i;
	for (i = 0; i < nwords; i++) {
		flash_program_word(addr, *src++);
		addr += 4;
	}
	return addr;
}

void storage_commit(void)
{
	uint8_t meta_backup[FLASH_META_DESC_LEN];

	// backup meta
	memcpy(meta_backup, (uint8_t*)FLASH_META_START, FLASH_META_DESC_LEN);

	flash_clear_status_flags();
	flash_unlock();
	// erase storage
	flash_erase_sector(FLASH_META_SECTOR_FIRST, FLASH_CR_PROGRAM_X32);
	// copy meta
	uint32_t flash = FLASH_META_START;
	flash = storage_flash_words(flash, (uint32_t *)meta_backup, FLASH_META_DESC_LEN/4);
	// copy storage
	flash_program_word(flash, *(uint32_t *) "stor");
	flash += 4;
	flash = storage_flash_words(flash, (uint32_t *)&storage_uuid, sizeof(storage_uuid)/4);
	flash = storage_flash_words(flash, (uint32_t *)&storage, sizeof(storage)/4);
	// fill remainder with zero for future extensions
	while (flash < FLASH_STORAGE_PINAREA) {
		flash_program_word(flash, 0);
		flash += 4;
	}
	flash_lock();
	storage_check_flash_errors();
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
		sessionSeedCached = false;
		memset(&sessionSeed, 0, sizeof(sessionSeed));
	} else if (msg->has_mnemonic) {
		storage.has_mnemonic = true;
		storage.has_node = false;
		strlcpy(storage.mnemonic, msg->mnemonic, sizeof(storage.mnemonic));
		sessionSeedCached = false;
		memset(&sessionSeed, 0, sizeof(sessionSeed));
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
	sessionSeedCached = false;
	sessionPassphraseCached = false;

	storage.has_passphrase_protection = true;
	storage.passphrase_protection = passphrase_protection;
}

void storage_setHomescreen(const uint8_t *data, uint32_t size)
{
	if (data && size == 1024) {
		storage.has_homescreen = true;
		memcpy(storage.homescreen.bytes, data, size);
		storage.homescreen.size = size;
	} else {
		storage.has_homescreen = false;
		memset(storage.homescreen.bytes, 0, sizeof(storage.homescreen.bytes));
		storage.homescreen.size = 0;
	}
}

void get_root_node_callback(uint32_t iter, uint32_t total)
{
	layoutProgress("Waking up", 1000 * iter / total);
}

const uint8_t *storage_getSeed(bool usePassphrase)
{
	// root node is properly cached
	if (usePassphrase == sessionSeedUsesPassphrase
		&& sessionSeedCached) {
		return sessionSeed;
	}

	// if storage has mnemonic, convert it to node and use it
	if (storage.has_mnemonic) {
		if (usePassphrase && !protectPassphrase()) {
			return NULL;
		}
		mnemonic_to_seed(storage.mnemonic, usePassphrase ? sessionPassphrase : "", sessionSeed, get_root_node_callback); // BIP-0039
		sessionSeedCached = true;
		sessionSeedUsesPassphrase = usePassphrase;
		return sessionSeed;
	}

	return NULL;
}

bool storage_getRootNode(HDNode *node, const char *curve, bool usePassphrase)
{
	// if storage has node, decrypt and use it
	if (storage.has_node && strcmp(curve, SECP256K1_NAME) == 0) {
		if (!protectPassphrase()) {
			return false;
		}
		if (hdnode_from_xprv(storage.node.depth, storage.node.fingerprint, storage.node.child_num, storage.node.chain_code.bytes, storage.node.private_key.bytes, curve, node) == 0) {
			return false;
		}
		if (storage.has_passphrase_protection && storage.passphrase_protection && sessionPassphraseCached && strlen(sessionPassphrase) > 0) {
			// decrypt hd node
			uint8_t secret[64];
			PBKDF2_HMAC_SHA512_CTX pctx;
			pbkdf2_hmac_sha512_Init(&pctx, (const uint8_t *)sessionPassphrase, strlen(sessionPassphrase), (const uint8_t *)"TREZORHD", 8);
			get_root_node_callback(0, BIP39_PBKDF2_ROUNDS);
			for (int i = 0; i < 8; i++) {
				pbkdf2_hmac_sha512_Update(&pctx, BIP39_PBKDF2_ROUNDS / 8);
				get_root_node_callback((i + 1) * BIP39_PBKDF2_ROUNDS / 8, BIP39_PBKDF2_ROUNDS);
			}
			pbkdf2_hmac_sha512_Final(&pctx, secret);
			aes_decrypt_ctx ctx;
			aes_decrypt_key256(secret, &ctx);
			aes_cbc_decrypt(node->chain_code, node->chain_code, 32, secret + 32, &ctx);
			aes_cbc_decrypt(node->private_key, node->private_key, 32, secret + 32, &ctx);
		}
		return true;
	}

	const uint8_t *seed = storage_getSeed(usePassphrase);
	if (seed == NULL) {
		return false;
	}
	
	return hdnode_from_seed(seed, 64, curve, node);
}

const char *storage_getLabel(void)
{
	return storage.has_label ? storage.label : 0;
}

const char *storage_getLanguage(void)
{
	return storage.has_language ? storage.language : 0;
}

const uint8_t *storage_getHomescreen(void)
{
	return (storage.has_homescreen && storage.homescreen.size == 1024) ? storage.homescreen.bytes : 0;
}

/* Check whether pin matches storage.  The pin must be a null-terminated
 * string with at most 9 characters.
 */
bool storage_isPinCorrect(const char *pin)
{
	/* The execution time of the following code only depends on the
	 * (public) input.  This avoids timing attacks.
	 */
	char diff = 0;
	uint32_t i = 0;
	while (pin[i]) {
		diff |= storage.pin[i] - pin[i];
		i++;
	}
	diff |= storage.pin[i];
	return diff == 0;
}

bool storage_hasPin(void)
{
	return storage.has_pin && storage.pin[0] != 0;
}

void storage_setPin(const char *pin)
{
	if (pin && pin[0]) {
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

void session_cachePin(void)
{
	sessionPinCached = true;
}

bool session_isPinCached(void)
{
	return sessionPinCached;
}

void storage_clearPinArea()
{
	flash_clear_status_flags();
	flash_unlock();
	flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
	flash_lock();
	storage_check_flash_errors();
}

void storage_resetPinFails(uint32_t *pinfailsptr)
{
	flash_clear_status_flags();
	flash_unlock();
	if ((uint32_t) (pinfailsptr + 1) - FLASH_STORAGE_PINAREA
		>= FLASH_STORAGE_PINAREA_LEN) {
		// erase extra storage sector
		flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
	} else {
		flash_program_word((uint32_t) pinfailsptr, 0);
	}
	flash_lock();
	storage_check_flash_errors();
}

bool storage_increasePinFails(uint32_t *pinfailsptr)
{
	uint32_t newctr = *pinfailsptr << 1;
	// counter already at maximum, we do not increase it any more
	// return success so that a good pin is accepted
	if (!newctr)
		return true;

	flash_clear_status_flags();
	flash_unlock();
	flash_program_word((uint32_t) pinfailsptr, newctr);
	flash_lock();
	storage_check_flash_errors();

	return *pinfailsptr == newctr;
}

uint32_t *storage_getPinFailsPtr(void)
{
	uint32_t *pinfailsptr = (uint32_t *) FLASH_STORAGE_PINAREA;
	while (*pinfailsptr == 0)
		pinfailsptr++;
	return pinfailsptr;
}

bool storage_isInitialized(void)
{
	return storage.has_node || storage.has_mnemonic;
}

uint32_t storage_nextU2FCounter(void)
{
	if(!storage.has_u2f_counter) {
		storage.has_u2f_counter = true;
		storage.u2f_counter = 1;
	} else {
		storage.u2f_counter++;
	}
	storage_commit();
	return storage.u2f_counter;
}
