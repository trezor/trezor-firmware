#ifndef __BOOTLOADER_CRYPTO_H__
#define __BOOTLOADER_CRYPTO_H__

#include <stdint.h>
#include <stdbool.h>

bool parse_header(const uint8_t *data, uint32_t *codelen, uint8_t *sigidx, uint8_t *sig);

bool check_signature(const uint8_t *start);

#endif
