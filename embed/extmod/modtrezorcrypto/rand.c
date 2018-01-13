/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "rand.h"
#include "rng.h"

uint32_t random32(void)
{
	return rng_get();
}
