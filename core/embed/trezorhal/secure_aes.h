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

#ifndef TREZOR_HAL_SECURE_AES_H
#define TREZOR_HAL_SECURE_AES_H

#include <secbool.h>
#include <stddef.h>
#include <stdint.h>

// Initializes secure AES module
secbool secure_aes_init(void);

// Encrypts a block of data using AES-256 EBB and (DHUK xor BHK) key
// Input and output must be aligned to 32 bits, size is in bytes
secbool secure_aes_encrypt(uint32_t* input, size_t size, uint32_t* output);

// Decrypts a block of data using AES-256 ECB and (DHUK xor BHK) key
// Input and output must be aligned to 32 bits, size is in bytes
secbool secure_aes_decrypt(uint32_t* input, size_t size, uint32_t* output);

void secure_aes_test();

#endif  // TREZOR_HAL_SECURE_AES_H
