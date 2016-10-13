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

#include <string.h>
#include "coins.h"
#include "address.h"

// filled CoinType Protobuf structure defined in https://github.com/trezor/trezor-common/blob/master/protob/types.proto#L133
// address types > 0xFF represent a two-byte prefix in big-endian order
const CoinType coins[COINS_COUNT] = {
	{true, "Bitcoin",       true, "BTC",  true,      0, true,     100000, true,      5, true,  6, true, 10, true, "\x18" "Bitcoin Signed Message:\n"},
	{true, "Testnet",       true, "TEST", true,    111, true,   10000000, true,    196, true,  3, true, 40, true, "\x18" "Bitcoin Signed Message:\n"},
	{true, "Namecoin",      true, "NMC",  true,     52, true,   10000000, true,      5, false, 0, false, 0, true, "\x19" "Namecoin Signed Message:\n"},
	{true, "Litecoin",      true, "LTC",  true,     48, true,    1000000, true,      5, false, 0, false, 0, true, "\x19" "Litecoin Signed Message:\n"},
	{true, "Dogecoin",      true, "DOGE", true,     30, true, 1000000000, true,     22, false, 0, false, 0, true, "\x19" "Dogecoin Signed Message:\n"},
	{true, "Dash",          true, "DASH", true,     76, true,     100000, true,     16, false, 0, false, 0, true, "\x19" "DarkCoin Signed Message:\n"},
	{true, "Zcash",         true, "ZEC",  true, 0x1CBD, true,    1000000, true, 0x1CB8, false, 0, false, 0, true, "\x16" "Zcash Signed Message:\n"},
	{true, "Zcash Testnet", true, "TAZ",  true, 0x1D25, true,    1000000, true, 0x1CBA, false, 0, false, 0, true, "\x16" "Zcash Signed Message:\n"},
};

const CoinType *coinByShortcut(const char *shortcut)
{
	if (!shortcut) return 0;
	int i;
	for (i = 0; i < COINS_COUNT; i++) {
		if (strcmp(shortcut, coins[i].coin_shortcut) == 0) {
			return &(coins[i]);
		}
	}
	return 0;
}

const CoinType *coinByName(const char *name)
{
	if (!name) return 0;
	int i;
	for (i = 0; i < COINS_COUNT; i++) {
		if (strcmp(name, coins[i].coin_name) == 0) {
			return &(coins[i]);
		}
	}
	return 0;
}

const CoinType *coinByAddressType(uint32_t address_type)
{
	int i;
	for (i = 0; i < COINS_COUNT; i++) {
		if (address_type == coins[i].address_type) {
			return &(coins[i]);
		}
	}
	return 0;
}

bool coinExtractAddressType(const CoinType *coin, const uint8_t *addr, uint32_t *address_type)
{
	if (coin->has_address_type && address_check_prefix(addr, coin->address_type)) {
		*address_type = coin->address_type;
		return true;
	}
	if (coin->has_address_type_p2sh && address_check_prefix(addr, coin->address_type_p2sh)) {
		*address_type = coin->address_type_p2sh;
		return true;
	}
	if (coin->has_address_type_p2wpkh && address_check_prefix(addr, coin->address_type_p2wpkh)) {
		*address_type = coin->address_type_p2wpkh;
		return true;
	}
	if (coin->has_address_type_p2wsh && address_check_prefix(addr, coin->address_type_p2wsh)) {
		*address_type = coin->address_type_p2wsh;
		return true;
	}
	*address_type = 0;
	return false;
}
