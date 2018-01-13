/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include <libopencm3/cm3/common.h>
#include <libopencm3/stm32/memorymap.h>
#include <libopencm3/stm32/f2/rng.h>

#include "rng.h"

#if !EMULATOR
uint32_t random32(void)
{
	static uint32_t last = 0, new = 0;
	while (new == last) {
		if ((RNG_SR & (RNG_SR_SECS | RNG_SR_CECS | RNG_SR_DRDY)) == RNG_SR_DRDY) {
			new = RNG_DR;
		}
	}
	last = new;
	return new;
}
#endif
