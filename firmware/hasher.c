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

#include "hasher.h"

void hasher_Init(Hasher *hasher, HasherType type) {
	hasher->type = type;

	switch (hasher->type) {
	case HASHER_SHA2:
		sha256_Init(&hasher->ctx.sha2);
		break;
	}
}

void hasher_Reset(Hasher *hasher) {
	hasher_Init(hasher, hasher->type);
}

void hasher_Update(Hasher *hasher, const uint8_t *data, size_t length) {
	switch (hasher->type) {
	case HASHER_SHA2:
		sha256_Update(&hasher->ctx.sha2, data, length);
		break;
	}
}

void hasher_Final(Hasher *hasher, uint8_t hash[HASHER_DIGEST_LENGTH]) {
	switch (hasher->type) {
	case HASHER_SHA2:
		sha256_Final(&hasher->ctx.sha2, hash);
		break;
	}
}

void hasher_Double(Hasher *hasher, uint8_t hash[HASHER_DIGEST_LENGTH]) {
	hasher_Final(hasher, hash);
	hasher_Raw(hasher->type, hash, HASHER_DIGEST_LENGTH, hash);
}

void hasher_Raw(HasherType type, const uint8_t *data, size_t length, uint8_t hash[HASHER_DIGEST_LENGTH]) {
	Hasher hasher;

	hasher_Init(&hasher, type);
	hasher_Update(&hasher, data, length);
	hasher_Final(&hasher, hash);
}
