#ifndef __ZEROIZE_H__
#define __ZEROIZE_H__

#include <stdlib.h>

#define ZEROIZE_STACK_SIZE 1024

void zeroize(unsigned char* b, size_t len);

void zeroize_stack(void);

#endif
