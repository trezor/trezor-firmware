#ifndef __TREZORHAL_COMMON_H__
#define __TREZORHAL_COMMON_H__

#include <stdint.h>
#include "secbool.h"

extern void memset_reg(volatile void *start, volatile void *stop, uint32_t val);

void clear_otg_hs_memory(void);

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func);

#define ensure(expr, msg) (((expr) == sectrue) ? (void)0 : __fatal_error(#expr, msg, __FILE__, __LINE__, __func__))

void jump_to(uint32_t address);

void hal_delay(uint32_t ms);

void shutdown(void);

extern uint32_t __stack_chk_guard;

#endif
