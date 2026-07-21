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
