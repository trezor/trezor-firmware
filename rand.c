/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdio.h>
#ifdef _WIN32
#include <time.h>
#else
#include <assert.h>
#endif

#include "rand.h"

static FILE *frand = NULL;

int finalize_rand(void)
{
#ifdef _WIN32
	return 0;
#else
	if (!frand) return 0;
	int err = fclose(frand);
	frand = NULL;
	return err;
#endif
}

uint32_t random32(void)
{
#ifdef _WIN32
	srand((unsigned)time(NULL));
	return ((rand() % 0xFF) | ((rand() % 0xFF) << 8) | ((rand() % 0xFF) << 16) | ((rand() % 0xFF) << 24));
#else
	uint32_t r;
	size_t len = sizeof(r);
	if (!frand) {
		frand = fopen("/dev/urandom", "r");
	}
	size_t len_read = fread(&r, 1, len, frand);
	(void)len_read;
	assert(len_read == len);
	return r;
#endif
}

uint32_t random_uniform(uint32_t n)
{
	uint32_t x, max = 0xFFFFFFFF - (0xFFFFFFFF % n);
	while ((x = random32()) >= max);
	return x / (max / n);
}

void random_buffer(uint8_t *buf, size_t len)
{
#ifdef _WIN32
	srand((unsigned)time(NULL));
	size_t i;
	for (i = 0; i < len; i++) {
		buf[i] = rand() % 0xFF;
	}
#else
	if (!frand) {
		frand = fopen("/dev/urandom", "r");
	}
	size_t len_read = fread(buf, 1, len, frand);
	(void)len_read;
	assert(len_read == len);
#endif
}

void random_permute(char *str, size_t len)
{
	int i, j;
	char t;
	for (i = len - 1; i >= 1; i--) {
		j = random_uniform(i + 1);
		t = str[j];
		str[j] = str[i];
		str[i] = t;
	}
}
