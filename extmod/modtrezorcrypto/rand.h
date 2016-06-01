#ifndef __RAND_H__
#define __RAND_H__

#include <stdint.h>
#include <stdlib.h>

uint32_t random32(void);
uint32_t random_uniform(uint32_t n);
void random_buffer(uint8_t *buf, size_t len);
void random_permute(void *buf, size_t size, size_t count);

#endif
