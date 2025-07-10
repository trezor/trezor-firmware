/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <trezor_types.h>

#ifdef SECURE_MODE

/**
 * @brief Writes data to the secret storage.
 *
 * @param data   Pointer to the data to write.
 * @param offset Offset in the storage to begin writing.
 * @param len    Number of bytes to write.
 */
void secret_write(const uint8_t* data, uint32_t offset, uint32_t len);

/**
 * @brief Reads data from the secret storage.
 *
 * @param data   Pointer to buffer where read data will be stored.
 * @param offset Offset in the storage to begin reading.
 * @param len    Number of bytes to read.
 * @return secbool sectrue on successful read, secfalse otherwise.
 */
secbool secret_read(uint8_t* data, uint32_t offset, uint32_t len);

/**
 * @brief Writes a key to the secret storage.
 *
 * Encrypts the secret if encryption is available on the platform.
 *
 * @param slot Index of the key slot.
 * @param key  Pointer to the key data.
 * @param len  Length of the key in bytes.
 * @return secbool sectrue if the key was written successfully, secfalse
 * otherwise.
 */
secbool secret_key_set(uint8_t slot, const uint8_t* key, size_t len);

/**
 * @brief Reads a secret key from the storage.
 *
 * Decrypts the secret if encryption is available on the platform.
 *
 * @param slot Index of the key slot.
 * @param dest Pointer to destination buffer for the key.
 * @param len  Length of the dest buffer.
 * @return secbool secrue if the key was read successfully, secfalse otherwise.
 */
secbool secret_key_get(uint8_t slot, uint8_t* dest, size_t len);

/**
 * @brief Checks if a secret key slot is writable.
 *
 * @param slot Index of the key slot.
 * @return secbool sectrue if the key slot can be written, secfalse otherwise.
 */
secbool secret_key_writable(uint8_t slot);

/**
 * @brief Regenerates the BHK and writes it to the secret storage.
 */
void secret_bhk_regenerate(void);

/**
 * @brief Prepares the secret storage for running the firmware.
 *
 * Provisions secrets and keys to the firmware depending on the trust level.
 * Disables access to the secret storage until next reset, if possible.
 * This function is called by the bootloader before starting the firmware.
 *
 * @param allow_run_with_secret       Allow firmware to run with secret access.
 * @param allow_provisioning_access   Allow provisioning access to secrets.
 */
void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access);

/**
 * @brief Initializes the secret storage for running the boardloader and next
 * stages.
 *
 * Ensures that secret storage access is enabled.
 * This function is called by the boardloader.
 */
void secret_init(void);

/**
 * @brief Disables access to the data in the storage in case
 *        of a failure or an attack.
 *
 * - On STM32U5, it erases the BHK keys (erases the BHK area), making the
 * storage area unusable.
 *
 * - On STM32F4, it erases the entire storage area.
 *
 */
void secret_safety_erase(void);

#ifdef LOCKABLE_BOOTLOADER

/**
 * @brief Unlocks the bootloader and erases all necessary keys.
 */
void secret_unlock_bootloader(void);

#ifdef TREZOR_EMULATOR

/**
 * @brief Locks the bootloader (emulator only).
 */
void secret_lock_bootloader(void);
#endif
#endif

#endif  // SECURE_MODE

#ifdef LOCKABLE_BOOTLOADER

/**
 * @brief Checks if the bootloader is locked.
 *
 * On platforms where secret storage access cannot be restricted for unofficial
 * firmware, a locked bootloader indicates presence of a non-public key.
 *
 * @return secbool sectrue if bootloader is locked, secfalse otherwise.
 */
secbool secret_bootloader_locked(void);
#endif
