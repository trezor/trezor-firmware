#ifndef __BOOTLOADER_CRYPTO_H__
#define __BOOTLOADER_CRYPTO_H__

#include <stdint.h>
#include <stdbool.h>

bool parse_header(const uint8_t *data, uint32_t *codelen);

bool check_signature(void);

#endif
