/*
 * This file is part of the Trezor project, https://trezor.io/
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

#ifndef __CONFIG_H__
#define __CONFIG_H__

#include "bip32.h"
#include "messages-common.pb.h"
#include "messages-management.pb.h"

#define STORAGE_FIELD(TYPE, NAME) \
  bool has_##NAME;                \
  TYPE NAME;

#define STORAGE_STRING(NAME, SIZE) \
  bool has_##NAME;                 \
  char NAME[SIZE];

#define STORAGE_BYTES(NAME, SIZE) \
  bool has_##NAME;                \
  struct {                        \
    uint32_t size;                \
    uint8_t bytes[SIZE];          \
  } NAME;

#define STORAGE_BOOL(NAME) STORAGE_FIELD(bool, NAME)
#define STORAGE_NODE(NAME) STORAGE_FIELD(StorageHDNode, NAME)
#define STORAGE_UINT32(NAME) STORAGE_FIELD(uint32_t, NAME)

typedef struct {
  uint32_t depth;
  uint32_t fingerprint;
  uint32_t child_num;
  struct {
    uint32_t size;
    uint8_t bytes[32];
  } chain_code;

  STORAGE_BYTES(private_key, 32);
  STORAGE_BYTES(public_key, 33);
} StorageHDNode;

typedef struct _Storage {
  uint32_t version;

  STORAGE_NODE(node)
  STORAGE_STRING(mnemonic, 241)
  STORAGE_BOOL(passphrase_protection)
  STORAGE_UINT32(pin_failed_attempts)
  STORAGE_STRING(pin, 10)
  STORAGE_STRING(language, 17)
  STORAGE_STRING(label, 33)
  STORAGE_BOOL(imported)
  STORAGE_BYTES(homescreen, 1024)
  STORAGE_UINT32(u2f_counter)
  STORAGE_BOOL(needs_backup)
  STORAGE_UINT32(flags)
  STORAGE_NODE(u2froot)
  STORAGE_BOOL(unfinished_backup)
  STORAGE_UINT32(auto_lock_delay_ms)
  STORAGE_BOOL(no_backup)
} Storage;

extern Storage configUpdate;

#define MAX_PIN_LEN 50
#define MAX_LABEL_LEN 32
#define MAX_LANGUAGE_LEN 16
#define MAX_MNEMONIC_LEN 240
#define HOMESCREEN_SIZE 1024
#define UUID_SIZE 12

#if DEBUG_LINK
#define MIN_AUTOLOCK_DELAY_MS (10 * 1000U)  // 10 seconds
#else
#define MIN_AUTOLOCK_DELAY_MS (60 * 1000U)  // 1 minute
#endif
#define MAX_AUTOLOCK_DELAY_MS 0x20000000U  // ~6 days

void config_init(void);
void session_clear(bool lock);
void session_endCurrentSession(void);
void config_lockDevice(void);

void config_loadDevice(const LoadDevice *msg);

const uint8_t *config_getSeed(void);

bool config_getU2FRoot(HDNode *node);
bool config_getRootNode(HDNode *node, const char *curve);

bool config_getLabel(char *dest, uint16_t dest_size);
void config_setLabel(const char *label);

bool config_getLanguage(char *dest, uint16_t dest_size);
void config_setLanguage(const char *lang);

void config_setPassphraseProtection(bool passphrase_protection);
bool config_getPassphraseProtection(bool *passphrase_protection);

bool config_getHomescreen(uint8_t *dest, uint16_t dest_size);
void config_setHomescreen(const uint8_t *data, uint32_t size);

uint8_t *session_startSession(const uint8_t *received_session_id);

bool config_setMnemonic(const char *mnemonic);
bool config_containsMnemonic(const char *mnemonic);
bool config_hasMnemonic(void);
bool config_getMnemonic(char *dest, uint16_t dest_size);
bool config_getMnemonicBytes(uint8_t *dest, uint16_t dest_size,
                             uint16_t *real_size);

#if DEBUG_LINK
bool config_dumpNode(HDNodeType *node);
bool config_getPin(char *dest, uint16_t dest_size);
#endif

bool config_unlock(const char *pin);
bool config_hasPin(void);
bool config_changePin(const char *old_pin, const char *new_pin);
bool session_isUnlocked(void);

bool config_hasWipeCode(void);
bool config_changeWipeCode(const char *pin, const char *wipe_code);

uint32_t config_nextU2FCounter(void);
void config_setU2FCounter(uint32_t u2fcounter);

bool config_isInitialized(void);

bool config_getImported(bool *imported);
void config_setImported(bool imported);

bool config_getNeedsBackup(bool *needs_backup);
void config_setNeedsBackup(bool needs_backup);

bool config_getUnfinishedBackup(bool *unfinished_backup);
void config_setUnfinishedBackup(bool unfinished_backup);

bool config_getNoBackup(bool *no_backup);
void config_setNoBackup(void);

void config_applyFlags(uint32_t flags);
bool config_getFlags(uint32_t *flags);

uint32_t config_getAutoLockDelayMs(void);
void config_setAutoLockDelayMs(uint32_t auto_lock_delay_ms);

SafetyCheckLevel config_getSafetyCheckLevel(void);
void config_setSafetyCheckLevel(SafetyCheckLevel safety_check_level);

void config_wipe(void);

extern char config_uuid_str[2 * UUID_SIZE + 1];

#endif
