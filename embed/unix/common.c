#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "common.h"
#include "display.h"

void __shutdown(void)
{
    printf("SHUTDOWN\n");
    exit(3);
}

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func)
{
    display_orientation(0);
    display_backlight(255);
    display_print_color(COLOR_WHITE, COLOR_RED128);
    display_printf("\nFATAL ERROR:\n");
    printf("\nFATAL ERROR:\n");
    if (expr) {
        display_printf("expr: %s\n", expr);
        printf("expr: %s\n", expr);
    }
    if (msg) {
        display_printf("msg : %s\n", msg);
        printf("msg : %s\n", msg);
    }
    if (file) {
        display_printf("file: %s:%d\n", file, line);
        printf("file: %s:%d\n", file, line);
    }
    if (func) {
        display_printf("func: %s\n", func);
        printf("func: %s\n", func);
    }
#ifdef GITREV
#define XSTR(s) STR(s)
#define STR(s) #s
    display_printf("rev : %s\n", XSTR(GITREV));
    printf("rev : %s\n", XSTR(GITREV));
#endif
    hal_delay(3000);
    __shutdown();
    for (;;);
}

void hal_delay(uint32_t ms)
{
    usleep(1000 * ms);
}
