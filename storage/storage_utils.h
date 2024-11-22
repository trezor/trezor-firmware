
#include <stdint.h>

uint32_t hamming_weight(uint32_t value);

#ifndef STORAGE_INSECURE_TESTING_MODE
#define STORAGE_INSECURE_TESTING_MODE 0
#endif

#if STORAGE_INSECURE_TESTING_MODE
#if PRODUCTION
#error "STORAGE_INSECURE_TESTING_MODE can't be used in production"
#else
#pragma message("STORAGE IS INSECURE DO NOT USE THIS IN PRODUCTION")
#endif
#endif
