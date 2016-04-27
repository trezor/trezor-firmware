#include "rand.h"

#ifdef UNIX
#include <stdio.h>
#include <assert.h>
static FILE *frand = NULL;
#else
uint32_t rng_get(void);
#endif

uint32_t random32(void)
{
#ifdef UNIX
	uint32_t r;
	size_t len = sizeof(r);
	if (!frand) {
		frand = fopen("/dev/urandom", "r");
	}
	size_t len_read = fread(&r, 1, len, frand);
	(void)len_read;
	assert(len_read == len);
	return r;
#else
	return rng_get();
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
#ifdef UNIX
	if (!frand) {
		frand = fopen("/dev/urandom", "r");
	}
	size_t len_read = fread(buf, 1, len, frand);
	(void)len_read;
	assert(len_read == len);
#else
	size_t i;
	uint32_t r = 0;
	for (i = 0; i < len; i++) {
		if (i % 4 == 0) {
			r = random32();
		}
		buf[i] = (r >> ((i % 4) * 8)) & 0xFF;
	}
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
