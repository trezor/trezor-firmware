#ifndef __BOOTLOADER_HEADER_H__
#define __BOOTLOADER_HEADER_H__

#include <stdint.h>
#include <stdbool.h>

bool read_header(const uint8_t *data, uint32_t *expiry, uint32_t *version, uint8_t *sigidx, uint8_t *sig);

#endif
