/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef __CRC_H__
#define __CRC_H__

#include <stdint.h>

uint32_t crc32(const uint8_t *data, uint32_t length, uint32_t crc);

#endif
