/**
 * Copyright (c) 2017 Saleem Rashid
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef __NEM_H__
#define __NEM_H__

#include <stdbool.h>
#include <stdint.h>

#define NEM_NETWORK_MAINNET 0x68
#define NEM_NETWORK_TESTNET 0x98
#define NEM_NETWORK_MIJIN   0x60

#define NEM_ADDRESS_SIZE 40
#define NEM_ADDRESS_SIZE_RAW 25

const char *nem_network_name(uint8_t network);

void nem_get_address_raw(const ed25519_public_key public_key, uint8_t version, uint8_t *address);
bool nem_get_address(const ed25519_public_key public_key, uint8_t version, char *address);

bool nem_validate_address_raw(const uint8_t *address, uint8_t network);
bool nem_validate_address(const char *address, uint8_t network);

#endif
