/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#ifndef __COINS_H__
#define __COINS_H__

#include "types.pb.h"

#define COINS_COUNT 9

extern const CoinType coins[COINS_COUNT];

const CoinType *coinByName(const char *name);
const CoinType *coinByAddressType(uint32_t address_type);
bool coinExtractAddressType(const CoinType *coin, const char *addr, uint32_t *address_type);
bool coinExtractAddressTypeRaw(const CoinType *coin, const uint8_t *addr_raw, uint32_t *address_type);

#endif
