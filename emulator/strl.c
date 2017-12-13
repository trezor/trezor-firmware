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

#include "strl.h"

#include <string.h>

size_t strlcpy(char *dst, const char *src, size_t size) {
	if (size == 0) {
		return 0;
	}

	for (size_t i = 0; i < size - 1; i++) {
		dst[i] = src[i];

		if (src[i] == '\0') {
			return i;
		}
	}

	dst[size - 1] = '\0';
	return size - 2;
}

size_t strlcat(char *dst, const char *src, size_t size) {
	size_t n = strnlen(dst, size);

	return n + strlcpy(&dst[n], src, size - n);
}
