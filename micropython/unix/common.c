#include <stdio.h>
#include <stdlib.h>

#include "common.h"

void __attribute__((noreturn)) __fatal_error(const char *msg, const char *file, int line, const char *func) {
    printf("\nFATAL ERROR:\n%s\n", msg);
    if (file) {
        printf("File: %s:%d\n", file, line);
    }
    if (func) {
        printf("Func: %s\n", func);
    }
    exit(1);
}
