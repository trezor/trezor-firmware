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

#include "noise.h"

#define SECURE_CHANNEL_INPUT_SIZE (sizeof(noise_response_t))
#define SECURE_CHANNEL_OUTPUT_SIZE (sizeof(noise_request_t))
#define SECURE_CHANNEL_TAG_SIZE (NOISE_TAG_SIZE)

bool secure_channel_handshake_1(uint8_t output[SECURE_CHANNEL_OUTPUT_SIZE]);
bool secure_channel_handshake_2(const uint8_t input[SECURE_CHANNEL_INPUT_SIZE]);
bool secure_channel_encrypt(const uint8_t* plaintext, size_t plaintext_length,
                            const uint8_t* associated_data,
                            size_t associated_data_length, uint8_t* ciphertext);
