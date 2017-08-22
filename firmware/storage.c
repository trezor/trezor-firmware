/*
 * This file is part of the TREZOR project, https://trezor.io/
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
#include "usb.h"
#include "gettext.h"

uint32_t storage_uuid[12/sizeof(uint32_t)];
char    storage_uuid_str[25];

Storage CONFIDENTIAL storageRam;
const Storage *storageRom = (const Storage *)(FLASH_STORAGE_START + 4 + sizeof(storage_uuid));

/*
 storage layout:

 offset |  type/length |  description
--------+--------------+-------------------------------
 0x0000 |     4 bytes  |  magic = 'stor'
 0x0004 |    12 bytes  |  uuid
 0x0010 |     ? bytes  |  Storage structure
--------+--------------+-------------------------------
 0x4000 |     4 kbytes |  area for pin failures
 0x5000 |   256 bytes  |  area for u2f counter updates
 0x5100 | 11.75 kbytes |  reserved

The area for pin failures looks like this:
0 ... 0 pinfail 0xffffffff .. 0xffffffff
The pinfail is a binary number of the form 1...10...0,
the number of zeros is the number of pin failures.
This layout is used because we can only clear bits without 
erasing the flash.

The area for u2f counter updates is just a sequence of zero-bits
followed by a sequence of one-bits.  The bits in a byte are numbered
from LSB to MSB.  The number of zero bits is the offset that should
be added to the storage u2f_counter to get the real counter value.

 */

#define FLASH_STORAGE_PINAREA     (FLASH_META_START + 0x4000)
#define FLASH_STORAGE_PINAREA_LEN (0x1000)
#define FLASH_STORAGE_U2FAREA     (FLASH_STORAGE_PINAREA + FLASH_STORAGE_PINAREA_LEN)
#define FLASH_STORAGE_U2FAREA_LEN (0x100)
#define FLASH_STORAGE_REALLEN (4 + sizeof(storage_uuid) + sizeof(Storage))

_Static_assert(FLASH_STORAGE_START + FLASH_STORAGE_REALLEN <= FLASH_STORAGE_PINAREA, "Storage struct is too large for TREZOR flash");
_Static_assert((sizeof(storage_uuid) & 3) == 0, "storage uuid unaligned");
_Static_assert((sizeof(storageRam) & 3) == 0, "storage unaligned");

/* Current u2f offset, i.e. u2f counter is
 * storage.u2f_counter + storage_u2f_offset.
 * This corresponds to the number of cleared bits in the U2FAREA.
 */
static uint32_t storage_u2f_offset;

/* magic constant to check validity of storage block */
static const uint32_t storage_magic = 0x726f7473;   // 'stor' as uint32_t

static bool sessionSeedCached, sessionSeedUsesPassphrase;

static uint8_t CONFIDENTIAL sessionSeed[64];

static bool sessionPinCached;

static bool sessionPassphraseCached;
static char CONFIDENTIAL sessionPassphrase[51];

#define STORAGE_VERSION 8

void storage_show_error(void)
{
	layoutDialog(&bmp_icon_error, NULL, NULL, NULL, _("Storage failure"), _("detected."), NULL, _("Please unplug"), _("the device."), NULL);
	system_halt();
}

void storage_check_flash_errors(void)
{
	// flash operation failed
	if (FLASH_SR & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR | FLASH_SR_WRPERR)) {
		storage_show_error();
	}
}

bool storage_from_flash(void)
{
	if (memcmp((void *)FLASH_STORAGE_START, &storage_magic, 4) != 0) {
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
	// version 7: since 1.5.1
	// version 8: since 1.5.2
	if (version > STORAGE_VERSION) {
		// downgrade -> clear storage
		return false;
	}

	// load uuid
	memcpy(storage_uuid, (void *)(FLASH_STORAGE_START + 4), sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);

	// copy storage
	size_t old_storage_size = 0;

	if (version == 1 || version == 2) {
		old_storage_size = 460;
	} else
	if (version == 3 || version == 4 || version == 5) {
		old_storage_size = 1488;
	} else
	if (version == 6 || version == 7) {
		old_storage_size = 1496;
	} else
	if (version == 8) {
		old_storage_size = 1504;
	}

	memset(&storageRam, 0, sizeof(Storage));
	memcpy(&storageRam, storageRom, old_storage_size);

	if (version <= 5) {
		// convert PIN failure counter from version 5 format
		uint32_t pinctr = storageRom->has_pin_failed_attempts ? storageRom->pin_failed_attempts : 0;
		if (pinctr > 31) {
			pinctr = 31;
		}
		flash_clear_status_flags();
		flash_unlock();
		// erase extra storage sector
		flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
		flash_program_word(FLASH_STORAGE_PINAREA, 0xffffffff << pinctr);
		flash_lock();
		storage_check_flash_errors();
		storageRam.has_pin_failed_attempts = false;
		storageRam.pin_failed_attempts = 0;
	}
	uint32_t *u2fptr = (uint32_t*) FLASH_STORAGE_U2FAREA;
	while (*u2fptr == 0) {
		u2fptr++;
	}
	storage_u2f_offset = 32 * (u2fptr - (uint32_t*) FLASH_STORAGE_U2FAREA);
	uint32_t u2fword = *u2fptr;
	while ((u2fword & 1) == 0) {
		storage_u2f_offset++;
		u2fword >>= 1;
	}
	// upgrade storage version
	if (version != STORAGE_VERSION) {
		storageRam.version = STORAGE_VERSION;
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
	random_buffer((uint8_t *)storage_uuid, sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);
}

void storage_reset(void)
{
	// reset storage struct
	memset(&storageRam, 0, sizeof(storageRam));
	storageRam.version = STORAGE_VERSION;
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
	for (int i = 0; i < nwords; i++) {
		flash_program_word(addr, *src++);
		addr += 4;
	}
	return addr;
}

static void storage_commit_locked(void)
{
	uint32_t meta_backup[FLASH_META_DESC_LEN/4];

	// backup meta
	memcpy(meta_backup, (uint8_t*)FLASH_META_START, FLASH_META_DESC_LEN);

	// erase storage
	flash_erase_sector(FLASH_META_SECTOR_FIRST, FLASH_CR_PROGRAM_X32);
	// copy meta
	uint32_t flash = FLASH_META_START;
	flash = storage_flash_words(flash, meta_backup, FLASH_META_DESC_LEN/4);
	// copy storage
	flash_program_word(flash, storage_magic);
	flash += 4;
	flash = storage_flash_words(flash, storage_uuid, sizeof(storage_uuid)/4);
	flash = storage_flash_words(flash, (uint32_t *)&storageRam, sizeof(storageRam)/4);
	// fill remainder with zero for future extensions
	while (flash < FLASH_STORAGE_PINAREA) {
		flash_program_word(flash, 0);
		flash += 4;
	}
}

void storage_commit(void)
{
	flash_clear_status_flags();
	flash_unlock();
	storage_commit_locked();
	flash_lock();
	storage_check_flash_errors();
}

void storage_loadDevice(LoadDevice *msg)
{
	storage_reset();

	storageRam.has_imported = true;
	storageRam.imported = true;

	if (msg->has_pin > 0) {
		storage_setPin(msg->pin);
	}

	if (msg->has_passphrase_protection) {
		storageRam.has_passphrase_protection = true;
		storageRam.passphrase_protection = msg->passphrase_protection;
	} else {
		storageRam.has_passphrase_protection = false;
	}

	if (msg->has_node) {
		storageRam.has_node = true;
		storageRam.has_mnemonic = false;
		memcpy(&storageRam.node, &(msg->node), sizeof(HDNodeType));
		sessionSeedCached = false;
		memset(&sessionSeed, 0, sizeof(sessionSeed));
	} else if (msg->has_mnemonic) {
		storageRam.has_mnemonic = true;
		storageRam.has_node = false;
		strlcpy(storageRam.mnemonic, msg->mnemonic, sizeof(storageRam.mnemonic));
		sessionSeedCached = false;
		memset(&sessionSeed, 0, sizeof(sessionSeed));
	}

	if (msg->has_language) {
		storage_setLanguage(msg->language);
	}

	if (msg->has_label) {
		storage_setLabel(msg->label);
	}

	if (msg->has_u2f_counter) {
		storage_setU2FCounter(msg->u2f_counter);
	}
}

void storage_setLabel(const char *label)
{
	if (!label) return;
	storageRam.has_label = true;
	strlcpy(storageRam.label, label, sizeof(storageRam.label));
}

void storage_setLanguage(const char *lang)
{
	if (!lang) return;
	// sanity check
	if (strcmp(lang, "english") == 0) {
		storageRam.has_language = true;
		strlcpy(storageRam.language, lang, sizeof(storageRam.language));
	}
}

void storage_setPassphraseProtection(bool passphrase_protection)
{
	sessionSeedCached = false;
	sessionPassphraseCached = false;

	storageRam.has_passphrase_protection = true;
	storageRam.passphrase_protection = passphrase_protection;
}

bool storage_hasPassphraseProtection(void)
{
	return storageRom->has_passphrase_protection && storageRom->passphrase_protection;
}

void storage_setHomescreen(const uint8_t *data, uint32_t size)
{
	if (data && size == 1024) {
		storageRam.has_homescreen = true;
		memcpy(storageRam.homescreen.bytes, data, size);
		storageRam.homescreen.size = size;
	} else {
		storageRam.has_homescreen = false;
		memset(storageRam.homescreen.bytes, 0, sizeof(storageRam.homescreen.bytes));
		storageRam.homescreen.size = 0;
	}
}

void get_root_node_callback(uint32_t iter, uint32_t total)
{
	usbSleep(1);
	layoutProgress(_("Waking up"), 1000 * iter / total);
}

const uint8_t *storage_getSeed(bool usePassphrase)
{
	// root node is properly cached
	if (usePassphrase == sessionSeedUsesPassphrase
		&& sessionSeedCached) {
		return sessionSeed;
	}

	// if storage has mnemonic, convert it to node and use it
	if (storageRom->has_mnemonic) {
		if (usePassphrase && !protectPassphrase()) {
			return NULL;
		}
		// if storage was not imported (i.e. it was properly generated or recovered)
		if (!storageRom->has_imported || !storageRom->imported) {
			// test whether mnemonic is a valid BIP-0039 mnemonic
			if (!mnemonic_check(storageRom->mnemonic)) {
				// and if not then halt the device
				storage_show_error();
			}
		}
		char oldTiny = usbTiny(1);
		mnemonic_to_seed(storageRom->mnemonic, usePassphrase ? sessionPassphrase : "", sessionSeed, get_root_node_callback); // BIP-0039
		usbTiny(oldTiny);
		sessionSeedCached = true;
		sessionSeedUsesPassphrase = usePassphrase;
		return sessionSeed;
	}

	return NULL;
}

bool storage_getRootNode(HDNode *node, const char *curve, bool usePassphrase)
{
	// if storage has node, decrypt and use it
	if (storageRom->has_node && strcmp(curve, SECP256K1_NAME) == 0) {
		if (!protectPassphrase()) {
			return false;
		}
		if (hdnode_from_xprv(storageRom->node.depth, storageRom->node.child_num, storageRom->node.chain_code.bytes, storageRom->node.private_key.bytes, curve, node) == 0) {
			return false;
		}
		if (storageRom->has_passphrase_protection && storageRom->passphrase_protection && sessionPassphraseCached && strlen(sessionPassphrase) > 0) {
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
	return storageRom->has_label ? storageRom->label : 0;
}

const char *storage_getLanguage(void)
{
	return storageRom->has_language ? storageRom->language : 0;
}

const uint8_t *storage_getHomescreen(void)
{
	return (storageRom->has_homescreen && storageRom->homescreen.size == 1024) ? storageRom->homescreen.bytes : 0;
}

void storage_setMnemonic(const char *mnemonic)
{
	storageRam.has_mnemonic = true;
	strlcpy(storageRam.mnemonic, mnemonic, sizeof(storageRam.mnemonic));
}

bool storage_hasNode(void)
{
	return storageRom->has_node;
}

const HDNode *storage_getNode(void)
{
	return storageRom->has_node ? (const HDNode *)&storageRom->node : 0;
}

bool storage_hasMnemonic(void)
{
	return storageRom->has_mnemonic;
}

const char *storage_getMnemonic(void)
{
	return storageRom->has_mnemonic ? storageRom->mnemonic : 0;
}

/* Check whether mnemonic matches storage. The mnemonic must be
 * a null-terminated string.
 */
bool storage_containsMnemonic(const char *mnemonic) {
	/* The execution time of the following code only depends on the
	 * (public) input.  This avoids timing attacks.
	 */
	char diff = 0;
	uint32_t i = 0;
	for (; mnemonic[i]; i++) {
		diff |= (storageRom->mnemonic[i] - mnemonic[i]);
	}
	diff |= storageRom->mnemonic[i];
	return diff == 0;
}

/* Check whether pin matches storage.  The pin must be
 * a null-terminated string with at most 9 characters.
 */
bool storage_containsPin(const char *pin)
{
	/* The execution time of the following code only depends on the
	 * (public) input.  This avoids timing attacks.
	 */
	char diff = 0;
	uint32_t i = 0;
	while (pin[i]) {
		diff |= storageRom->pin[i] - pin[i];
		i++;
	}
	diff |= storageRom->pin[i];
	return diff == 0;
}

bool storage_hasPin(void)
{
	return storageRom->has_pin && storageRom->pin[0] != 0;
}

void storage_setPin(const char *pin)
{
	if (pin && pin[0]) {
		storageRam.has_pin = true;
		strlcpy(storageRam.pin, pin, sizeof(storageRam.pin));
	} else {
		storageRam.has_pin = false;
		storageRam.pin[0] = 0;
	}
	storage_commit();
	sessionPinCached = false;
}

const char *storage_getPin(void)
{
	return storageRom->has_pin ? storageRom->pin : 0;
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

void storage_clearPinArea(void)
{
	flash_clear_status_flags();
	flash_unlock();
	flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
	flash_lock();
	storage_check_flash_errors();
	storage_u2f_offset = 0;
}

// called when u2f area or pin area overflows
static void storage_area_recycle(uint32_t new_pinfails)
{
	// first clear storage marker.  In case of a failure below it is better
	// to clear the storage than to allow restarting with zero PIN failures
	flash_program_word(FLASH_STORAGE_START, 0);
	if (*(uint32_t *)FLASH_STORAGE_START != 0) {
		storage_show_error();
	}

	// erase storage sector
	flash_erase_sector(FLASH_META_SECTOR_LAST, FLASH_CR_PROGRAM_X32);
	flash_program_word(FLASH_STORAGE_PINAREA, new_pinfails);
	if (*(uint32_t *)FLASH_STORAGE_PINAREA != new_pinfails) {
		storage_show_error();
	}

	if (storage_u2f_offset > 0) {
		storageRam.has_u2f_counter = true;
		storageRam.u2f_counter += storage_u2f_offset;
		storage_u2f_offset = 0;
	}
	storage_commit_locked();
}

void storage_resetPinFails(uint32_t *pinfailsptr)
{
	flash_clear_status_flags();
	flash_unlock();
	if ((uint32_t) (pinfailsptr + 1)
		>= FLASH_STORAGE_PINAREA + FLASH_STORAGE_PINAREA_LEN) {
		// recycle extra storage sector
		storage_area_recycle(0xffffffff);
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
	return storageRom->has_node || storageRom->has_mnemonic;
}

bool storage_isImported(void)
{
	return storageRom->has_imported && storageRom->imported;
}

void storage_setImported(bool imported)
{
	storageRam.has_imported = true;
	storageRam.imported = imported;
}

bool storage_needsBackup(void)
{
	return storageRom->has_needs_backup && storageRom->needs_backup;
}

void storage_setNeedsBackup(bool needs_backup)
{
	storageRam.has_needs_backup = true;
	storageRam.needs_backup = needs_backup;
}

void storage_applyFlags(uint32_t flags)
{
	if ((storageRom->flags | flags) == storageRom->flags) {
		return; // no new flags
	}
	storageRam.has_flags = true;
	storageRam.flags |= flags;
	storage_commit();
}

uint32_t storage_getFlags(void)
{
	return storageRom->has_flags ? storageRom->flags : 0;
}

uint32_t storage_nextU2FCounter(void)
{
	uint32_t *ptr = ((uint32_t *) FLASH_STORAGE_U2FAREA) + (storage_u2f_offset / 32);
	uint32_t newval = 0xfffffffe << (storage_u2f_offset & 31);

	flash_clear_status_flags();
	flash_unlock();
	flash_program_word((uint32_t) ptr, newval);
	storage_u2f_offset++;
	if (storage_u2f_offset >= 8 * FLASH_STORAGE_U2FAREA_LEN) {
		storage_area_recycle(*storage_getPinFailsPtr());
	}
	flash_lock();
	storage_check_flash_errors();
	return storageRom->u2f_counter + storage_u2f_offset;
}

void storage_setU2FCounter(uint32_t u2fcounter)
{
	storageRam.has_u2f_counter = true;
	storageRam.u2f_counter = u2fcounter - storage_u2f_offset;
	storage_commit();
}

void storage_wipe(void)
{
	storage_reset();
	storage_reset_uuid();
	storage_commit();
	storage_clearPinArea();
}
