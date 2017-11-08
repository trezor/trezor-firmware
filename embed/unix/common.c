#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "common.h"

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func)
{
    printf("\nFATAL ERROR:\n");
    if (expr) {
        printf("expr: %s\n", expr);
    }
    if (msg) {
        printf("msg : %s\n", msg);
    }
    if (file) {
        printf("file: %s:%d\n", file, line);
    }
    if (func) {
        printf("func: %s\n", func);
    }
#ifdef GITREV
#define XSTR(s) STR(s)
#define STR(s) #s
    printf("rev : %s\n", XSTR(GITREV));
#endif
    exit(1);
}

void hal_delay(uint32_t ms)
{
    usleep(1000 * ms);
}

void shutdown(void)
{
    exit(1);
}
