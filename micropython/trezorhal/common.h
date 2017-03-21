#ifndef __TREZORHAL_COMMON_H__
#define __TREZORHAL_COMMON_H__

void SystemClock_Config(void); // defined in stm32_system.c

void __attribute__((noreturn)) nlr_jump_fail(void *val);

void __attribute__((noreturn)) __fatal_error(const char *msg);

#endif
