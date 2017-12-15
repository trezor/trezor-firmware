#include <stdio.h>
#include <stdlib.h>

#include "common.h"
#include "rng.h"

uint32_t rng_get(void)
{
    static FILE *frand = NULL;
    if (!frand) {
        frand = fopen("/dev/urandom", "r");
    }
    ensure(sectrue * (frand != NULL), "fopen failed");
    uint32_t r;
    ensure(sectrue * (sizeof(r) == fread(&r, 1, sizeof(r), frand)), "fread failed");
    return r;
}
