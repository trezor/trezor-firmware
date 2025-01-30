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

// Parses the string as a signed 32-bit integer in the specified base.
//
// If the entire string represents a valid integer, the parsed value is stored
// in 'result', and the function returns true. Otherwise, the function returns
// false, and 'result' remains unchanged.
bool cstr_parse_int32(const char* str, int base, int32_t* result);

// Parses the string as a unsigned 32-bit integer in the specified base.
//
// If the entire string represents a valid integer, the parsed value is stored
// in 'result', and the function returns true. Otherwise, the function returns
// false, and 'result' remains unchanged.
bool cstr_parse_uint32(const char* str, int base, uint32_t* result);

// Skips leading whitespace in the string and returns the pointer to the first
// non-whitespace character.
const char* cstr_skip_whitespace(const char* str);

// Returns true if the null-terminated C-string starts with the prefix
bool cstr_starts_with(const char* str, const char* prefix);

// Decodes the string as a hexadecimal string and writes the binary data to the
// destination buffer.
//
// Hexadecimal digits can be in upper or lower case and may be separated by
// whitespace.
//
// Number of bytes written to the destination buffer is stored in
// `bytes_written` (even if the function returns false).
//
// Returns true if the entire slice was parsed successfully.
bool cstr_decode_hex(const char* str, uint8_t* dst, size_t dst_len,
                     size_t* bytes_written);

// Encodes binary data to null-terminated hexadecimal string
//
// Destination buffer must be at least 2 * src_len + 1 bytes long.
//
// If the destination buffer is too small, the function will return false and
// the destination buffer will be set to empty string.
bool cstr_encode_hex(char* dst, size_t dst_len, const void* src,
                     size_t src_len);
