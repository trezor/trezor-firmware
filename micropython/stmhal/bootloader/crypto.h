#ifndef __BOOTLOADER_CRYPTO_H__
#define __BOOTLOADER_CRYPTO_H__

#include <stdint.h>
#include <stdbool.h>

bool check_header(const uint8_t *data);

bool check_signature(void);

#endif
