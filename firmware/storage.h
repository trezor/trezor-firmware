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

#ifndef __STORAGE_H__
#define __STORAGE_H__

#include "types.pb.h"
#include "storage.pb.h"
#include "messages.pb.h"
#include "bip32.h"

extern Storage storageUpdate;

void storage_init(void);
void storage_generate_uuid(void);
void storage_clear_update(void);
void storage_update(void);
void session_clear(bool clear_pin);

void storage_loadDevice(LoadDevice *msg);

const uint8_t *storage_getSeed(bool usePassphrase);

bool storage_getRootNode(HDNode *node, const char *curve, bool usePassphrase);

const char *storage_getLabel(void);
void storage_setLabel(const char *label);

const char *storage_getLanguage(void);
void storage_setLanguage(const char *lang);

void storage_setPassphraseProtection(bool passphrase_protection);
bool storage_hasPassphraseProtection(void);

const uint8_t *storage_getHomescreen(void);
void storage_setHomescreen(const uint8_t *data, uint32_t size);

void session_cachePassphrase(const char *passphrase);
bool session_isPassphraseCached(void);

void storage_setMnemonic(const char *mnemonic);
bool storage_containsMnemonic(const char *mnemonic);
bool storage_hasMnemonic(void);
const char *storage_getMnemonic(void);

bool storage_hasNode(void);
const HDNode *storage_getNode(void);

bool storage_containsPin(const char *pin);
bool storage_hasPin(void);
const char *storage_getPin(void);
void storage_setPin(const char *pin);
void session_cachePin(void);
bool session_isPinCached(void);
void storage_clearPinArea(void);
void storage_resetPinFails(uint32_t *pinfailptr);
bool storage_increasePinFails(uint32_t *pinfailptr);
uint32_t *storage_getPinFailsPtr(void);

uint32_t storage_nextU2FCounter(void);
void storage_setU2FCounter(uint32_t u2fcounter);

bool storage_isInitialized(void);

bool storage_isImported(void);
void storage_setImported(bool imported);

bool storage_needsBackup(void);
void storage_setNeedsBackup(bool needs_backup);

void storage_applyFlags(uint32_t flags);
uint32_t storage_getFlags(void);

void storage_wipe(void);

extern char storage_uuid_str[25];

#endif
