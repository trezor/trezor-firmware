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

#ifndef __STORAGE_H__
#define __STORAGE_H__

#include "types.pb.h"
#include "storage.pb.h"
#include "messages.pb.h"
#include "bip32.h"

void storage_init(void);
void storage_reset_uuid(void);
void storage_reset(void);
void storage_commit(void);
void session_clear(void);

void storage_loadDevice(LoadDevice *msg);

bool storage_getRootNode(HDNode *node);

const char *storage_getLabel(void);
void storage_setLabel(const char *label);

const char *storage_getLanguage(void);
void storage_setLanguage(const char *lang);

void storage_setPassphraseProtection(bool passphrase_protection);

void session_cachePassphrase(const char *passphrase);
bool session_isPassphraseCached(void);

bool storage_isPinCorrect(const char *pin);
bool storage_hasPin(void);
void storage_setPin(const char *pin);
void session_cachePin(const char *pin);
bool session_isPinCached(void);
void storage_resetPinFails(void);
void storage_increasePinFails(void);
uint32_t storage_getPinFails(void);

bool storage_isInitialized(void);

extern Storage storage;

extern char storage_uuid_str[25];

#endif
