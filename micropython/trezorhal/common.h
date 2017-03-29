#ifndef __TREZORHAL_COMMON_H__
#define __TREZORHAL_COMMON_H__

#include <stdint.h>

void periph_init(void);

void __attribute__((noreturn)) nlr_jump_fail(void *val);

void __attribute__((noreturn)) __fatal_error(const char *msg);

void jump_to(uint32_t address);

#endif
