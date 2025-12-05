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

/**
 * Parses the string as a signed 32-bit integer in the specified base.
 *
 * If the entire string represents a valid integer, the parsed value is stored
 * in 'result', and the function returns true. Otherwise, the function returns
 * false, and 'result' remains unchanged.
 *
 * @param str The null-terminated C-string to parse
 * @param base The numeral base (e.g., 10 for decimal, 16 for hexadecimal)
 * @param result Pointer to store the parsed integer value
 * @return true if parsing was successful, false otherwise
 */
bool cstr_parse_int32(const char* str, int base, int32_t* result);

/**
 * Parses the string as a unsigned 32-bit integer in the specified base.
 *
 * If the entire string represents a valid integer, the parsed value is stored
 * in 'result', and the function returns true. Otherwise, the function returns
 * false, and 'result' remains unchanged.
 *
 * @param str The null-terminated C-string to parse
 * @param base The numeral base (e.g., 10 for decimal, 16 for hexadecimal)
 * @param result Pointer to store the parsed integer value
 * @return true if parsing was successful, false otherwise
 */
bool cstr_parse_uint32(const char* str, int base, uint32_t* result);

/**
 * Skips leading whitespace in the string and returns the pointer to the first
 * non-whitespace character.
 *
 * @param str The null-terminated C-string to process
 * @return Pointer to the first non-whitespace character in the string
 */
const char* cstr_skip_whitespace(const char* str);

/**
 * Returns true if the null-terminated C-string starts with the prefix.
 *
 * @param str The null-terminated C-string to check
 * @param prefix The prefix to look for
 * @return true if the string starts with the prefix, false otherwise
 */
bool cstr_starts_with(const char* str, const char* prefix);

/**
 * Decodes the string as a hexadecimal string and writes the binary data to the
 * destination buffer.
 *
 * Hexadecimal digits can be in upper or lower case and may be separated by
 * whitespace.
 *
 * @param str The null-terminated C-string to decode
 * @param dst Pointer to the destination buffer to write the binary data
 * @param dst_len Length of the destination buffer in bytes
 * @param bytes_written Pointer to store the number of bytes written to the
 *   destination buffer
 *
 * @return true if the entire string was parsed successfully, false otherwise
 */
bool cstr_decode_hex(const char* str, uint8_t* dst, size_t dst_len,
                     size_t* bytes_written);

/**
 * Encodes binary data to null-terminated hexadecimal string
 *
 * Destination buffer must be at least 2 * src_len + 1 bytes long otherwise
 * the function will return false and the destination buffer will be set to
 * empty string.
 *
 * @param dst Pointer to the destination buffer to write the hexadecimal string
 * @param dst_len Length of the destination buffer in bytes
 * @param src Pointer to the source binary data
 * @param src_len Length of the source binary data in bytes
 * @return true if encoding was successful, false otherwise
 */
bool cstr_encode_hex(char* dst, size_t dst_len, const void* src,
                     size_t src_len);

/**
 * Appends the null-terminated C-string 'src' to the end of the null-terminated
 * C-string 'dst', ensuring that the total length does not exceed 'dst_len'.
 *
 * The function ensures that 'dst' remains null-terminated after the operation.
 * If there is not enough space in 'dst' to append 'src', the function returns
 * appends as much of 'src' as possible and returns false.
 *
 * @param dst Pointer to the destination C-string
 * @param dst_len Length of the destination buffer in bytes
 * @param src Pointer to the source C-string to append
 * @return true if the entire string was appended successfully, false otherwise
 */
bool cstr_append(char* dst, size_t dst_len, const char* src);

/**
 * Appends the string representation of a signed 32-bit integer to the end of
 * the null-terminated C-string 'dst', ensuring that the total length does not
 * exceed 'dst_len'.
 *
 * The function ensures that 'dst' remains null-terminated after the operation.
 * If there is not enough space in 'dst' to append the integer, the function
 * returns false, but appends as much as possible.
 *
 * @param dst Pointer to the destination C-string
 * @param dst_len Length of the destination buffer in bytes
 * @param value The signed 32-bit integer to append
 * @return true if the entire integer was appended successfully, false otherwise
 */
bool cstr_append_int32(char* dst, size_t dst_len, int32_t value);

/**
 * Appends the string representation of an unsigned 32-bit integer to the end of
 * the null-terminated C-string 'dst', ensuring that the total length does not
 * exceed 'dst_len'.
 *
 * The function ensures that 'dst' remains null-terminated after the operation.
 * If there is not enough space in 'dst' to append the integer, the function
 * returns false, but appends as much as possible.
 *
 * @param dst Pointer to the destination C-string
 * @param dst_len Length of the destination buffer in bytes
 * @param value The unsigned 32-bit integer to append
 * @return true if the entire integer was appended successfully, false otherwise
 */
bool cstr_append_uint32(char* dst, size_t dst_len, uint32_t value);

/**
 * Appends the hexadecimal string representation of an unsigned 32-bit
 * integer to the end of the null-terminated C-string 'dst', ensuring that
 * the total length does not exceed 'dst_len'.
 *
 * The function ensures that 'dst' remains null-terminated after the operation.
 * If there is not enough space in 'dst' to append the hexadecimal string, the
 * function returns false, but appends as much as possible.
 *
 * @param dst Pointer to the destination C-string
 * @param dst_len Length of the destination buffer in bytes
 * @param value The unsigned 32-bit integer to append in hexadecimal format
 * @return true if the entire hexadecimal string was appended successfully,
 * false otherwise
 */
bool cstr_append_uint32_hex(char* dst, size_t dst_len, uint32_t value);
