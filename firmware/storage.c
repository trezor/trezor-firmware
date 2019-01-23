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

#include "trezor.h"
#include "sha2.h"
#include "aes/aes.h"
#include "pbkdf2.h"
#include "hmac.h"
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
#include "u2f.h"
#include "memzero.h"
#include "supervise.h"

/* magic constant to check validity of storage block */
static const uint32_t storage_magic = 0x726f7473;   // 'stor' as uint32_t

static uint32_t storage_uuid[12 / sizeof(uint32_t)];
_Static_assert(sizeof(storage_uuid) == 12, "storage_uuid has wrong size");

Storage CONFIDENTIAL storageUpdate __attribute__((aligned(4)));
_Static_assert((sizeof(storageUpdate) & 3) == 0, "storage unaligned");

#define FLASH_STORAGE (FLASH_STORAGE_START + sizeof(storage_magic) + sizeof(storage_uuid))
#define storageRom ((const Storage *) FLASH_PTR(FLASH_STORAGE))

char storage_uuid_str[25];

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
#define FLASH_STORAGE_REALLEN     (sizeof(storage_magic) + sizeof(storage_uuid) + sizeof(Storage))

#if !EMULATOR
// TODO: Fix this for emulator
_Static_assert(FLASH_STORAGE_START + FLASH_STORAGE_REALLEN <= FLASH_STORAGE_PINAREA, "Storage struct is too large for TREZOR flash");
#endif

/* Current u2f offset, i.e. u2f counter is
 * storage.u2f_counter + storage_u2f_offset.
 * This corresponds to the number of cleared bits in the U2FAREA.
 */
static uint32_t storage_u2f_offset;

static bool sessionSeedCached, sessionSeedUsesPassphrase;

static uint8_t CONFIDENTIAL sessionSeed[64];

static bool sessionPinCached = false;

static bool sessionPassphraseCached = false;
static char CONFIDENTIAL sessionPassphrase[51];

#define STORAGE_VERSION 10

void storage_show_error(void)
{
	layoutDialog(&bmp_icon_error, NULL, NULL, NULL, _("Storage failure"), _("detected."), NULL, _("Please unplug"), _("the device."), NULL);
	shutdown();
}

void storage_check_flash_errors(uint32_t status)
{
	// flash operation failed
	if (status & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR | FLASH_SR_WRPERR)) {
		storage_show_error();
	}
}

bool storage_from_flash(void)
{
	storage_clear_update();
	if (memcmp(FLASH_PTR(FLASH_STORAGE_START), &storage_magic, sizeof(storage_magic)) != 0) {
		// wrong magic
		return false;
	}

	const uint32_t version = storageRom->version;
	// version 1: since 1.0.0
	// version 2: since 1.2.1
	// version 3: since 1.3.1
	// version 4: since 1.3.2
	// version 5: since 1.3.3
	// version 6: since 1.3.6
	// version 7: since 1.5.1
	// version 8: since 1.5.2
	// version 9: since 1.6.1
	// version 10: since 1.7.2
	if (version > STORAGE_VERSION) {
		// downgrade -> clear storage
		return false;
	}

	// load uuid
	memcpy(storage_uuid, FLASH_PTR(FLASH_STORAGE_START + sizeof(storage_magic)), sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);

#define OLD_STORAGE_SIZE(last_member) (((offsetof(Storage, last_member) + pb_membersize(Storage, last_member)) + 3) & ~3)

	// copy storage
	size_t old_storage_size = 0;

	if (version == 0) {
	} else if (version <= 2) {
		old_storage_size = OLD_STORAGE_SIZE(imported);
	} else if (version <= 5) {
		// added homescreen
		old_storage_size = OLD_STORAGE_SIZE(homescreen);
	} else if (version <= 7) {
		// added u2fcounter
		old_storage_size = OLD_STORAGE_SIZE(u2f_counter);
	} else if (version <= 8) {
		// added flags and needsBackup
		old_storage_size = OLD_STORAGE_SIZE(flags);
	} else if (version <= 9) {
		// added u2froot, unfinished_backup and auto_lock_delay_ms
		old_storage_size = OLD_STORAGE_SIZE(auto_lock_delay_ms);
	} else if (version <= 10) {
		// added no_backup
		old_storage_size = OLD_STORAGE_SIZE(no_backup);
	}

	// erase newly added fields
	if (old_storage_size != sizeof(Storage)) {
		svc_flash_unlock();
		svc_flash_program(FLASH_CR_PROGRAM_X32);
		for (uint32_t offset = old_storage_size; offset < sizeof(Storage); offset += sizeof(uint32_t)) {
			flash_write32(FLASH_STORAGE_START + sizeof(storage_magic) + sizeof(storage_uuid) + offset, 0);
		}
		storage_check_flash_errors(svc_flash_lock());
	}

	if (version <= 5) {
		// convert PIN failure counter from version 5 format
		uint32_t pinctr = storageRom->has_pin_failed_attempts ? storageRom->pin_failed_attempts : 0;
		if (pinctr > 31) {
			pinctr = 31;
		}
		svc_flash_unlock();
		// erase extra storage sector
		svc_flash_erase_sector(FLASH_META_SECTOR_LAST);
		svc_flash_program(FLASH_CR_PROGRAM_X32);
		flash_write32(FLASH_STORAGE_PINAREA, 0xffffffff << pinctr);
		// storageRom.has_pin_failed_attempts and storageRom.pin_failed_attempts
		// are erased by storage_update below
		storage_check_flash_errors(svc_flash_lock());
	}
	const uint32_t *u2fptr = (const uint32_t*) FLASH_PTR(FLASH_STORAGE_U2FAREA);
	while (*u2fptr == 0) {
		u2fptr++;
	}
	storage_u2f_offset = 32 * (u2fptr - (const uint32_t*) FLASH_PTR(FLASH_STORAGE_U2FAREA));
	uint32_t u2fword = *u2fptr;
	while ((u2fword & 1) == 0) {
		storage_u2f_offset++;
		u2fword >>= 1;
	}
	// force recomputing u2f root for storage version < 9.
	// this is done by re-setting the mnemonic, which triggers the computation
	if (version < 9) {
		storageUpdate.has_mnemonic = storageRom->has_mnemonic;
		strlcpy(storageUpdate.mnemonic, storageRom->mnemonic, sizeof(storageUpdate.mnemonic));
	}
	// update storage version on flash
	if (version != STORAGE_VERSION) {
		storage_update();
	}
	return true;
}

void storage_init(void)
{
	if (!storage_from_flash()) {
		storage_wipe();
	}
}

void storage_generate_uuid(void)
{
	// set random uuid
	random_buffer((uint8_t *)storage_uuid, sizeof(storage_uuid));
	data2hex(storage_uuid, sizeof(storage_uuid), storage_uuid_str);
}

void session_clear(bool clear_pin)
{
	sessionSeedCached = false;
	memzero(&sessionSeed, sizeof(sessionSeed));
	sessionPassphraseCached = false;
	memzero(&sessionPassphrase, sizeof(sessionPassphrase));
	if (clear_pin) {
		session_uncachePin();
	}
}

static uint32_t storage_flash_words(uint32_t addr, const uint32_t *src, int nwords) {
	for (int i = 0; i < nwords; i++) {
		flash_write32(addr, *src++);
		addr += sizeof(uint32_t);
	}
	return addr;
}

static void get_u2froot_callback(uint32_t iter, uint32_t total)
{
	layoutProgress(_("Updating"), 1000 * iter / total);
}

static void storage_compute_u2froot(const char* mnemonic, StorageHDNode *u2froot) {
	static CONFIDENTIAL HDNode node;
	char oldTiny = usbTiny(1);
	mnemonic_to_seed(mnemonic, "", sessionSeed, get_u2froot_callback); // BIP-0039
	usbTiny(oldTiny);
	hdnode_from_seed(sessionSeed, 64, NIST256P1_NAME, &node);
	hdnode_private_ckd(&node, U2F_KEY_PATH);
	u2froot->depth = node.depth;
	u2froot->child_num = U2F_KEY_PATH;
	u2froot->chain_code.size = sizeof(node.chain_code);
	memcpy(u2froot->chain_code.bytes, node.chain_code, sizeof(node.chain_code));
	u2froot->has_private_key = true;
	u2froot->private_key.size = sizeof(node.private_key);
	memcpy(u2froot->private_key.bytes, node.private_key, sizeof(node.private_key));
	memzero(&node, sizeof(node));
	session_clear(false); // invalidate seed cache
}

// if storage is filled in - update fields that has has_field set to true
// if storage is NULL - do not backup original content - essentialy a wipe
static void storage_commit_locked(bool update)
{
	if (update) {
		if (storageUpdate.has_passphrase_protection) {
			sessionSeedCached = false;
			sessionPassphraseCached = false;
		}

		storageUpdate.version = STORAGE_VERSION;
		if (!storageUpdate.has_node && !storageUpdate.has_mnemonic) {
			storageUpdate.has_node = storageRom->has_node;
			memcpy(&storageUpdate.node, &storageRom->node, sizeof(StorageHDNode));
			storageUpdate.has_mnemonic = storageRom->has_mnemonic;
			strlcpy(storageUpdate.mnemonic, storageRom->mnemonic, sizeof(storageUpdate.mnemonic));
			storageUpdate.has_u2froot = storageRom->has_u2froot;
			memcpy(&storageUpdate.u2froot, &storageRom->u2froot, sizeof(StorageHDNode));
		} else if (storageUpdate.has_mnemonic) {
			storageUpdate.has_u2froot = true;
			storage_compute_u2froot(storageUpdate.mnemonic, &storageUpdate.u2froot);
		}
		if (!storageUpdate.has_passphrase_protection) {
			storageUpdate.has_passphrase_protection = storageRom->has_passphrase_protection;
			storageUpdate.passphrase_protection = storageRom->passphrase_protection;
		}
		if (!storageUpdate.has_pin) {
			storageUpdate.has_pin = storageRom->has_pin;
			strlcpy(storageUpdate.pin, storageRom->pin, sizeof(storageUpdate.pin));
		} else if (!storageUpdate.pin[0]) {
			storageUpdate.has_pin = false;
		}
		if (!storageUpdate.has_language) {
			storageUpdate.has_language = storageRom->has_language;
			strlcpy(storageUpdate.language, storageRom->language, sizeof(storageUpdate.language));
		}
		if (!storageUpdate.has_label) {
			storageUpdate.has_label = storageRom->has_label;
			strlcpy(storageUpdate.label, storageRom->label, sizeof(storageUpdate.label));
		} else if (!storageUpdate.label[0]) {
			storageUpdate.has_label = false;
		}
		if (!storageUpdate.has_imported) {
			storageUpdate.has_imported = storageRom->has_imported;
			storageUpdate.imported = storageRom->imported;
		}
		if (!storageUpdate.has_homescreen) {
			storageUpdate.has_homescreen = storageRom->has_homescreen;
			memcpy(&storageUpdate.homescreen, &storageRom->homescreen, sizeof(storageUpdate.homescreen));
		} else if (storageUpdate.homescreen.size == 0) {
			storageUpdate.has_homescreen = false;
		}
		if (!storageUpdate.has_u2f_counter) {
			storageUpdate.has_u2f_counter = storageRom->has_u2f_counter;
			storageUpdate.u2f_counter = storageRom->u2f_counter;
		}
		if (!storageUpdate.has_needs_backup) {
			storageUpdate.has_needs_backup = storageRom->has_needs_backup;
			storageUpdate.needs_backup = storageRom->needs_backup;
		}
		if (!storageUpdate.has_unfinished_backup) {
			storageUpdate.has_unfinished_backup = storageRom->has_unfinished_backup;
			storageUpdate.unfinished_backup = storageRom->unfinished_backup;
		}
		if (!storageUpdate.has_no_backup) {
			storageUpdate.has_no_backup = storageRom->has_no_backup;
			storageUpdate.no_backup = storageRom->no_backup;
		}
		if (!storageUpdate.has_flags) {
			storageUpdate.has_flags = storageRom->has_flags;
			storageUpdate.flags = storageRom->flags;
		}
	}

	// backup meta
	uint32_t meta_backup[FLASH_META_DESC_LEN / sizeof(uint32_t)];
	memcpy(meta_backup, FLASH_PTR(FLASH_META_START), FLASH_META_DESC_LEN);

	// erase storage
	svc_flash_erase_sector(FLASH_META_SECTOR_FIRST);
	svc_flash_program(FLASH_CR_PROGRAM_X32);

	// copy meta back
	uint32_t flash = FLASH_META_START;
	flash = storage_flash_words(flash, meta_backup, FLASH_META_DESC_LEN / sizeof(uint32_t));

	// copy storage
	flash = storage_flash_words(flash, &storage_magic, sizeof(storage_magic) / sizeof(uint32_t));
	flash = storage_flash_words(flash, storage_uuid, sizeof(storage_uuid) / sizeof(uint32_t));

	if (update) {
		flash = storage_flash_words(flash, (const uint32_t *)&storageUpdate, sizeof(storageUpdate) / sizeof(uint32_t));
	}
	storage_clear_update();

	// fill remainder with zero for future extensions
	while (flash < FLASH_STORAGE_PINAREA) {
		flash_write32(flash, 0);
		flash += sizeof(uint32_t);
	}
}

void storage_clear_update(void)
{
	memzero(&storageUpdate, sizeof(storageUpdate));
}

void storage_update(void)
{
	svc_flash_unlock();
	storage_commit_locked(true);
	storage_check_flash_errors(svc_flash_lock());
}

static void storage_setNode(const HDNodeType *node) {
	storageUpdate.node.depth = node->depth;
	storageUpdate.node.fingerprint = node->fingerprint;
	storageUpdate.node.child_num = node->child_num;

	storageUpdate.node.chain_code.size = 32;
	memcpy(storageUpdate.node.chain_code.bytes, node->chain_code.bytes, 32);

	if (node->has_private_key) {
		storageUpdate.node.has_private_key = true;
		storageUpdate.node.private_key.size = 32;
		memcpy(storageUpdate.node.private_key.bytes, node->private_key.bytes, 32);
	}
}

#if DEBUG_LINK
void storage_dumpNode(HDNodeType *node) {
	node->depth = storageRom->node.depth;
	node->fingerprint = storageRom->node.fingerprint;
	node->child_num = storageRom->node.child_num;

	node->chain_code.size = 32;
	memcpy(node->chain_code.bytes, storageRom->node.chain_code.bytes, 32);

	if (storageRom->node.has_private_key) {
		node->has_private_key = true;
		node->private_key.size = 32;
		memcpy(node->private_key.bytes, storageRom->node.private_key.bytes, 32);
	}
}
#endif

void storage_loadDevice(const LoadDevice *msg)
{
	session_clear(true);

	storageUpdate.has_imported = true;
	storageUpdate.imported = true;

	storage_setPin(msg->has_pin ? msg->pin : "");
	storage_setPassphraseProtection(msg->has_passphrase_protection && msg->passphrase_protection);

	if (msg->has_node) {
		storageUpdate.has_node = true;
		storageUpdate.has_mnemonic = false;
		storage_setNode(&(msg->node));
		sessionSeedCached = false;
		memzero(&sessionSeed, sizeof(sessionSeed));
	} else if (msg->has_mnemonic) {
		storageUpdate.has_mnemonic = true;
		storageUpdate.has_node = false;
		strlcpy(storageUpdate.mnemonic, msg->mnemonic, sizeof(storageUpdate.mnemonic));
		sessionSeedCached = false;
		memzero(&sessionSeed, sizeof(sessionSeed));
	}

	if (msg->has_language) {
		storageUpdate.has_language = true;
		strlcpy(storageUpdate.language, msg->language, sizeof(storageUpdate.language));
	}

	storage_setLabel(msg->has_label ? msg->label : "");

	if (msg->has_u2f_counter) {
		storageUpdate.has_u2f_counter = true;
		storageUpdate.u2f_counter = msg->u2f_counter - storage_u2f_offset;
	}

	storage_update();
}

void storage_setLabel(const char *label)
{
	storageUpdate.has_label = true;
	if (!label) return;
	strlcpy(storageUpdate.label, label, sizeof(storageUpdate.label));
}

void storage_setLanguage(const char *lang)
{
	if (!lang) return;
	// sanity check
	if (strcmp(lang, "english") == 0) {
		storageUpdate.has_language = true;
		strlcpy(storageUpdate.language, lang, sizeof(storageUpdate.language));
	}
}

void storage_setPassphraseProtection(bool passphrase_protection)
{
	sessionSeedCached = false;
	sessionPassphraseCached = false;

	storageUpdate.has_passphrase_protection = true;
	storageUpdate.passphrase_protection = passphrase_protection;
}

bool storage_hasPassphraseProtection(void)
{
	return storageRom->has_passphrase_protection && storageRom->passphrase_protection;
}

void storage_setHomescreen(const uint8_t *data, uint32_t size)
{
	storageUpdate.has_homescreen = true;
	if (data && size == 1024) {
		memcpy(storageUpdate.homescreen.bytes, data, size);
		storageUpdate.homescreen.size = size;
	} else {
		memzero(storageUpdate.homescreen.bytes, sizeof(storageUpdate.homescreen.bytes));
		storageUpdate.homescreen.size = 0;
	}
}

static void get_root_node_callback(uint32_t iter, uint32_t total)
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

static bool storage_loadNode(const StorageHDNode *node, const char *curve, HDNode *out) {
	return hdnode_from_xprv(node->depth, node->child_num, node->chain_code.bytes, node->private_key.bytes, curve, out);
}

bool storage_getU2FRoot(HDNode *node)
{
	return storageRom->has_u2froot && storage_loadNode(&storageRom->u2froot, NIST256P1_NAME, node);
}

bool storage_getRootNode(HDNode *node, const char *curve, bool usePassphrase)
{
	// if storage has node, decrypt and use it
	if (storageRom->has_node && strcmp(curve, SECP256K1_NAME) == 0) {
		if (!protectPassphrase()) {
			return false;
		}
		if (!storage_loadNode(&storageRom->node, curve, node)) {
			return false;
		}
		if (storageRom->has_passphrase_protection && storageRom->passphrase_protection && sessionPassphraseCached && strlen(sessionPassphrase) > 0) {
			// decrypt hd node
			uint8_t secret[64];
			PBKDF2_HMAC_SHA512_CTX pctx;
			char oldTiny = usbTiny(1);
			pbkdf2_hmac_sha512_Init(&pctx, (const uint8_t *)sessionPassphrase, strlen(sessionPassphrase), (const uint8_t *)"TREZORHD", 8, 1);
			get_root_node_callback(0, BIP39_PBKDF2_ROUNDS);
			for (int i = 0; i < 8; i++) {
				pbkdf2_hmac_sha512_Update(&pctx, BIP39_PBKDF2_ROUNDS / 8);
				get_root_node_callback((i + 1) * BIP39_PBKDF2_ROUNDS / 8, BIP39_PBKDF2_ROUNDS);
			}
			pbkdf2_hmac_sha512_Final(&pctx, secret);
			usbTiny(oldTiny);
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
	storageUpdate.has_mnemonic = true;
	strlcpy(storageUpdate.mnemonic, mnemonic, sizeof(storageUpdate.mnemonic));
}

bool storage_hasNode(void)
{
	return storageRom->has_node;
}

bool storage_hasMnemonic(void)
{
	return storageRom->has_mnemonic;
}

const char *storage_getMnemonic(void)
{
	return storageUpdate.has_mnemonic ? storageUpdate.mnemonic
		: storageRom->has_mnemonic ? storageRom->mnemonic : 0;
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
	storageUpdate.has_pin = true;
	strlcpy(storageUpdate.pin, pin, sizeof(storageUpdate.pin));
	session_cachePin();
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

bool session_getState(const uint8_t *salt, uint8_t *state, const char *passphrase)
{
	if (!passphrase && !sessionPassphraseCached) {
		return false;
	} else {
		passphrase = sessionPassphrase;
	}
	if (!salt) {
		// if salt is not provided fill the first half of the state with random data
		random_buffer(state, 32);
	} else {
		// if salt is provided fill the first half of the state with salt
		memcpy(state, salt, 32);
	}
	// state[0:32] = salt
	// state[32:64] = HMAC(passphrase, salt || device_id)
	HMAC_SHA256_CTX ctx;
	hmac_sha256_Init(&ctx, (const uint8_t *)passphrase, strlen(passphrase));
	hmac_sha256_Update(&ctx, state, 32);
	hmac_sha256_Update(&ctx, (const uint8_t *)storage_uuid, sizeof(storage_uuid));
	hmac_sha256_Final(&ctx, state + 32);

	memzero(&ctx, sizeof(ctx));

	return true;
}

void session_cachePin(void)
{
	sessionPinCached = true;
}

void session_uncachePin(void)
{
	sessionPinCached = false;
}

bool session_isPinCached(void)
{
	return sessionPinCached;
}

void storage_clearPinArea(void)
{
	svc_flash_unlock();
	svc_flash_erase_sector(FLASH_META_SECTOR_LAST);
	storage_check_flash_errors(svc_flash_lock());
	storage_u2f_offset = 0;
}

// called when u2f area or pin area overflows
static void storage_area_recycle(uint32_t new_pinfails)
{
	// first clear storage marker.  In case of a failure below it is better
	// to clear the storage than to allow restarting with zero PIN failures
	svc_flash_program(FLASH_CR_PROGRAM_X32);
	flash_write32(FLASH_STORAGE_START, 0);
	if (*(const uint32_t *)FLASH_PTR(FLASH_STORAGE_START) != 0) {
		storage_show_error();
	}

	// erase pinarea/u2f sector
	svc_flash_erase_sector(FLASH_META_SECTOR_LAST);
	flash_write32(FLASH_STORAGE_PINAREA, new_pinfails);
	if (*(const volatile uint32_t *)FLASH_PTR(FLASH_STORAGE_PINAREA) != new_pinfails) {
		storage_show_error();
	}

	// restore storage sector
	storageUpdate.has_u2f_counter = true;
	storageUpdate.u2f_counter += storage_u2f_offset;
	storage_u2f_offset = 0;
	storage_commit_locked(true);
}

void storage_resetPinFails(uint32_t flash_pinfails)
{
	svc_flash_unlock();
	if (flash_pinfails + sizeof(uint32_t)
		>= FLASH_STORAGE_PINAREA + FLASH_STORAGE_PINAREA_LEN) {
		// recycle extra storage sector
		storage_area_recycle(0xffffffff);
	} else {
		svc_flash_program(FLASH_CR_PROGRAM_X32);
		flash_write32(flash_pinfails, 0);
	}
	storage_check_flash_errors(svc_flash_lock());
}

bool storage_increasePinFails(uint32_t flash_pinfails)
{
	uint32_t newctr = *(const uint32_t*)FLASH_PTR(flash_pinfails) << 1;
	// counter already at maximum, we do not increase it any more
	// return success so that a good pin is accepted
	if (!newctr)
		return true;

	svc_flash_unlock();
	svc_flash_program(FLASH_CR_PROGRAM_X32);
	flash_write32(flash_pinfails, newctr);
	storage_check_flash_errors(svc_flash_lock());

	return *(const uint32_t*)FLASH_PTR(flash_pinfails) == newctr;
}

uint32_t storage_getPinWait(uint32_t flash_pinfails)
{
	// The pin failure word is the inverted wait time in seconds.
	// It's inverted because flash allows changing 1 to 0 but not vice versa.
	return ~*(const uint32_t*)FLASH_PTR(flash_pinfails);
}

uint32_t storage_getPinFailsOffset(void)
{
	uint32_t flash_pinfails = FLASH_STORAGE_PINAREA;
	while (*(const uint32_t*)FLASH_PTR(flash_pinfails) == 0)
		flash_pinfails += sizeof(uint32_t);
	return flash_pinfails;
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
	storageUpdate.has_imported = true;
	storageUpdate.imported = imported;
}

bool storage_needsBackup(void)
{
	return storageUpdate.has_needs_backup ? storageUpdate.needs_backup
		: storageRom->has_needs_backup && storageRom->needs_backup;
}

void storage_setNeedsBackup(bool needs_backup)
{
	storageUpdate.has_needs_backup = true;
	storageUpdate.needs_backup = needs_backup;
}

bool storage_unfinishedBackup(void)
{
	return storageUpdate.has_unfinished_backup ? storageUpdate.unfinished_backup
		: storageRom->has_unfinished_backup && storageRom->unfinished_backup;
}

void storage_setUnfinishedBackup(bool unfinished_backup)
{
	storageUpdate.has_unfinished_backup = true;
	storageUpdate.unfinished_backup = unfinished_backup;
}

bool storage_noBackup(void)
{
	return storageUpdate.has_no_backup ? storageUpdate.no_backup
		: storageRom->has_no_backup && storageRom->no_backup;
}

void storage_setNoBackup(void)
{
	storageUpdate.has_no_backup = true;
	storageUpdate.no_backup = true;
}

void storage_applyFlags(uint32_t flags)
{
	if ((storageRom->flags | flags) == storageRom->flags) {
		return; // no new flags
	}
	storageUpdate.has_flags = true;
	storageUpdate.flags |= flags;
	storage_update();
}

uint32_t storage_getFlags(void)
{
	return storageRom->has_flags ? storageRom->flags : 0;
}

uint32_t storage_nextU2FCounter(void)
{
	uint32_t flash_u2f_offset = FLASH_STORAGE_U2FAREA +
		sizeof(uint32_t) * (storage_u2f_offset / 32);
	uint32_t newval = 0xfffffffe << (storage_u2f_offset & 31);

	svc_flash_unlock();
	svc_flash_program(FLASH_CR_PROGRAM_X32);
	flash_write32(flash_u2f_offset, newval);
	storage_u2f_offset++;
	if (storage_u2f_offset >= 8 * FLASH_STORAGE_U2FAREA_LEN) {
		storage_area_recycle(*(const uint32_t*)
							 FLASH_PTR(storage_getPinFailsOffset()));
	}
	storage_check_flash_errors(svc_flash_lock());
	return storageRom->u2f_counter + storage_u2f_offset;
}

void storage_setU2FCounter(uint32_t u2fcounter)
{
	storageUpdate.has_u2f_counter = true;
	storageUpdate.u2f_counter = u2fcounter - storage_u2f_offset;
}

uint32_t storage_getAutoLockDelayMs()
{
	const uint32_t default_delay_ms = 10 * 60 * 1000U; // 10 minutes
	return storageRom->has_auto_lock_delay_ms ? storageRom->auto_lock_delay_ms : default_delay_ms;
}

void storage_setAutoLockDelayMs(uint32_t auto_lock_delay_ms)
{
	const uint32_t min_delay_ms = 10 * 1000U; // 10 seconds
	auto_lock_delay_ms = MAX(auto_lock_delay_ms, min_delay_ms);
	storageUpdate.has_auto_lock_delay_ms = true;
	storageUpdate.auto_lock_delay_ms = auto_lock_delay_ms;
}

void storage_wipe(void)
{
	session_clear(true);
	storage_generate_uuid();

	svc_flash_unlock();
	storage_commit_locked(false);
	storage_check_flash_errors(svc_flash_lock());

	storage_clearPinArea();
}
