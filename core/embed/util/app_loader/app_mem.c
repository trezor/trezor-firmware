
#include <stdlib.h>

#include "app_mem.h"

#ifdef TREZOR_EMULATOR

void* app_mem_alloc(size_t size) { return malloc(size); }

void app_mem_free(void* ptr) { free(ptr); }

#else

void* app_mem_alloc(size_t size) { return NULL; }

void app_mem_free(void* ptr) {}

#endif
