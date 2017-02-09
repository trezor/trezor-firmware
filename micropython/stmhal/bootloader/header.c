#include <string.h>
#include "header.h"

bool read_header(const uint8_t *data, uint32_t *expiry, uint32_t *version, uint8_t *sigidx, uint8_t *sig)
{
    uint32_t magic;
    memcpy(&magic, data, 4);
    if (magic != 0x425A5254) return false; // TRZB

    uint32_t hdrlen;
    memcpy(&hdrlen, data + 4, 4);
    if (hdrlen != 256) return false;

    memcpy(expiry, data + 8, 4);

    uint32_t codelen;
    memcpy(&codelen, data + 12, 4);
    if (codelen != 64 * 1024) return false;

    memcpy(version, data + 16, 4);

    // reserved

    memcpy(sigidx, data + 0x00BF, 1);

    memcpy(sig, data + 0x00C0, 64);

    return true;
}
