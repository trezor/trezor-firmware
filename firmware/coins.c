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
#include "ecdsa.h"
#include "base58.h"

// filled CoinType Protobuf structure defined in https://github.com/trezor/trezor-common/blob/master/protob/types.proto#L133
// address types > 0xFF represent a two-byte prefix in big-endian order
const CoinType coins[COINS_COUNT] = {
	{true, "Bitcoin",       true, " BTC",  true,    0, true,     500000, true,    5, true, "\x18" "Bitcoin Signed Message:\n",  true, 0x0488b21e, true, 0x0488ade4, true, false, },
	{true, "Testnet",       true, " TEST", true,  111, true,   10000000, true,  196, true, "\x18" "Bitcoin Signed Message:\n",  true, 0x043587cf, true, 0x04358394, true, true,  },
	{true, "Namecoin",      true, " NMC",  true,   52, true,   10000000, true,    5, true, "\x19" "Namecoin Signed Message:\n", true, 0x019da462, true, 0x019d9cfe, true, false, },
	{true, "Litecoin",      true, " LTC",  true,   48, true,   40000000, true,   50, true, "\x19" "Litecoin Signed Message:\n", true, 0x019da462, true, 0x019d9cfe, true, true,  },
	{true, "Dogecoin",      true, " DOGE", true,   30, true, 1000000000, true,   22, true, "\x19" "Dogecoin Signed Message:\n", true, 0x02facafd, true, 0x02fac398, true, false, },
	{true, "Dash",          true, " DASH", true,   76, true,     100000, true,   16, true, "\x19" "DarkCoin Signed Message:\n", true, 0x02fe52cc, true, 0x02fe52f8, true, false, },
	{true, "Zcash",         true, " ZEC",  true, 7352, true,    1000000, true, 7357, true, "\x16" "Zcash Signed Message:\n",    true, 0x0488b21e, true, 0x0488ade4, true, false, },
	{true, "Zcash Testnet", true, " TAZ",  true, 7461, true,   10000000, true, 7354, true, "\x16" "Zcash Signed Message:\n",    true, 0x043587cf, true, 0x04358394, true, false, },
};

const CoinType *coinByName(const char *name)
{
	if (!name) return 0;
	for (int i = 0; i < COINS_COUNT; i++) {
		if (strcmp(name, coins[i].coin_name) == 0) {
			return &(coins[i]);
		}
	}
	return 0;
}

const CoinType *coinByAddressType(uint32_t address_type)
{
	for (int i = 0; i < COINS_COUNT; i++) {
		if (address_type == coins[i].address_type) {
			return &(coins[i]);
		}
	}
	return 0;
}

bool coinExtractAddressType(const CoinType *coin, const char *addr, uint32_t *address_type)
{
	if (!addr) return false;
	uint8_t addr_raw[MAX_ADDR_RAW_SIZE];
	int len = base58_decode_check(addr, addr_raw, MAX_ADDR_RAW_SIZE);
	if (len >= 21) {
		return coinExtractAddressTypeRaw(coin, addr_raw, address_type);
	}
	return false;
}

bool coinExtractAddressTypeRaw(const CoinType *coin, const uint8_t *addr_raw, uint32_t *address_type)
{
	if (coin->has_address_type && address_check_prefix(addr_raw, coin->address_type)) {
		*address_type = coin->address_type;
		return true;
	}
	if (coin->has_address_type_p2sh && address_check_prefix(addr_raw, coin->address_type_p2sh)) {
		*address_type = coin->address_type_p2sh;
		return true;
	}
	*address_type = 0;
	return false;
}
