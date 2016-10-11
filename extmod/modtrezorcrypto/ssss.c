/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "ssss.h"

bool ssss_split(const bignum256 *secret, int m, int n, bignum256 *shares)
{
	if (m < 1 || n < 1 || m > 15 || n > 15 || m > n) {
		return false;
	}
	return true;
}

bool ssss_combine(const bignum256 *shares, int n, bignum256 *secret)
{
	return true;
}
