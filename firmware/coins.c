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

const CoinType coins[COINS_COUNT] = {
	{true, "Bitcoin",  true, "BTC",  true,   0, true,     10000, true,   5},
	{true, "Testnet",  true, "TEST", true, 111, true,  10000000, true, 196},
	{true, "Namecoin", true, "NMC",  true,  52, true,  10000000, true,   5},
	{true, "Litecoin", true, "LTC",  true,  48, true,  10000000, true,   5},
	{true, "Dogecoin", true, "DOGE", true,  30, true, 100000000, true,  22},
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

const CoinType *coinByAddressType(uint8_t address_type)
{
	int i;
	for (i = 0; i < COINS_COUNT; i++) {
		if (address_type == coins[i].address_type) {
			return &(coins[i]);
		}
	}
	return 0;
}
