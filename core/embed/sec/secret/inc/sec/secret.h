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

#ifdef KERNEL_MODE

#define SECRET_HEADER_MAGIC "TRZS"
#define SECRET_HEADER_LEN 16
#define SECRET_OPTIGA_KEY_OFFSET 16
#define SECRET_OPTIGA_KEY_LEN 32
#define SECRET_TROPIC_KEY_LEN 32

#define SECRET_MONOTONIC_COUNTER_OFFSET 48
#define SECRET_MONOTONIC_COUNTER_LEN 1024
#define SECRET_MONOTONIC_COUNTER2_OFFSET (SECRET_MONOTONIC_COUNTER_LEN + 48)

#define SECRET_BHK_OFFSET (1024 * 8)
#define SECRET_BHK_LEN 32

// Writes data to the secret storage
void secret_write(const uint8_t* data, uint32_t offset, uint32_t len);

// Reads data from the secret storage
secbool secret_read(uint8_t* data, uint32_t offset, uint32_t len);

// Checks if the secret storage has been wiped
secbool secret_wiped(void);

// Verifies that the secret storage has the correct header
secbool secret_verify_header(void);

// Erases the entire secret storage
void secret_erase(void);

// Writes the secret header to the secret storage
void secret_write_header(void);

// Writes optiga pairing secret to the secret storage
// Encrypts the secret if encryption is available on the platform
// Returns true if the secret was written successfully
secbool secret_optiga_set(const uint8_t secret[SECRET_OPTIGA_KEY_LEN]);

// Reads optiga pairing secret
// Decrypts the secret if encryption is available on the platform
// Returns true if the secret was read successfully
// Reading can fail if optiga is not paired, the pairing secret was not
// provisioned to the firmware (by calling secret_optiga_backup), or the secret
// was made unavailable by calling secret_optiga_hide
secbool secret_optiga_get(uint8_t dest[SECRET_OPTIGA_KEY_LEN]);

// Checks if the optiga pairing secret is present in the secret storage
secbool secret_optiga_present(void);

// Checks if the optiga pairing secret can be written to the secret storage
secbool secret_optiga_writable(void);

// Erases optiga pairing secret from the secret storage
void secret_optiga_erase(void);

secbool secret_tropic_get_trezor_privkey(uint8_t dest[SECRET_TROPIC_KEY_LEN]);

secbool secret_tropic_get_tropic_pubkey(uint8_t dest[SECRET_TROPIC_KEY_LEN]);

// Regenerates the BHK and writes it to the secret storage
void secret_bhk_regenerate(void);

// Prepares the secret storage for running the firmware
// Provisions secrets/keys to the firmware, depending on the trust level
// Disables access to the secret storage until next reset, if possible
// This function is called by the bootloader before starting the firmware
void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access);

// Prepares the secret storage for running the boardloader and next stages
// Ensures that secret storage access is enabled
// This function is called by the boardloader
void secret_init(void);

#endif  // KERNEL_MODE

// Checks if bootloader is locked, that is the secret storage contains optiga
// pairing secret on platforms where access to the secret storage cannot be
// restricted for unofficial firmware
secbool secret_bootloader_locked(void);
