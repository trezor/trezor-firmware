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

// Configures OTFDEC1 region 1 to transparently decrypt all CPU reads from the
// OCTOSPI1 memory-mapped window, enabling XIP from AES-128-CTR encrypted NOR
// flash.
//
// Prerequisites:
//   - OTFDEC1 must be clocked and marked SEC|PRIV (done by tz_init() in
//     secmon before the NS kernel starts).
//   - SAES must be initialized (secure_aes_init()) before calling this
//     function, as it uses the DHUK path to derive the region key.
//
// nonce[2]:  64-bit nonce written into the OTFDEC region nonce registers.
//            Must match the nonce used when the flash content was encrypted.
// version:   Firmware version counter used by OTFDEC for replay protection.
//
// TODO: replace the internal key derivation with a proper KDF (e.g. HKDF
//       over DHUK) once the key-management scheme is finalised.  Currently
//       the region key is produced by AES-256-ECB(DHUK, fixed_label), which
//       is device-unique but not yet tied to a firmware version or policy.
secbool ext_flash_otfdec_init(const uint32_t nonce[2], uint16_t version);

// Disables OTFDEC1 region 1 and de-initialises the peripheral.
// Call before updating the ext-flash content so that reads during erase/write
// are not passed through the now-incorrect decryption window.
void ext_flash_otfdec_deinit(void);

// Encrypts `byte_len` bytes of `plaintext` using OTFDEC1 encipher mode,
// producing ciphertext that — when written to ext-flash at `flash_addr` —
// will be transparently decrypted by OTFDEC on CPU fetch (XIP).
//
// Constraints:
//   - `flash_addr` must be within the OCTOSPI1 memory-mapped window
//   - `byte_len` must be a non-zero multiple of 16 (OTFDEC AES block size)
//   - both buffers must be 4-byte aligned
//   - OCTOSPI1 must be in memory-mapped (XIP) mode at call time
//
// In non-secure builds this call crosses the TrustZone boundary via smcall;
// the actual encryption executes in secmon where OTFDEC1 is SEC|PRIV.
bool ext_flash_otfdec_cipher(uint32_t flash_addr, const uint8_t *plaintext,
                              uint32_t byte_len, uint8_t *ciphertext_out);
