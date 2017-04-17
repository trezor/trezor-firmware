#include <stdio.h>
#include <stdlib.h>

#include "common.h"

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    printf("FATAL ERROR:\n");
    printf("%s\n", msg);
    exit(1);
}
