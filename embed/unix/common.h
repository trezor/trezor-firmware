#ifndef __TREZORUNIX_COMMON_H__
#define __TREZORUNIX_COMMON_H__

#include "../trezorhal/secbool.h"

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func);

#define ensure(expr, msg) (((expr) == sectrue) ? (void)0 : __fatal_error(#expr, msg, __FILE__, __LINE__, __func__))

#endif
