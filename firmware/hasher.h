/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

#ifndef __HASHER_H__
#define __HASHER_H__

#include <stddef.h>
#include <stdint.h>

#include "sha2.h"

#define HASHER_DIGEST_LENGTH 32

typedef enum {
    HASHER_SHA2,
} HasherType;

typedef struct {
    HasherType type;

    union {
        SHA256_CTX sha2;
    } ctx;
} Hasher;

void hasher_Init(Hasher *hasher, HasherType type);
void hasher_Reset(Hasher *hasher);
void hasher_Update(Hasher *hasher, const uint8_t *data, size_t length);
void hasher_Final(Hasher *hasher, uint8_t hash[HASHER_DIGEST_LENGTH]);
void hasher_Double(Hasher *hasher, uint8_t hash[HASHER_DIGEST_LENGTH]);

void hasher_Raw(HasherType type, const uint8_t *data, size_t length, uint8_t hash[HASHER_DIGEST_LENGTH]);

#endif
