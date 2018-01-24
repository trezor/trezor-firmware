/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef TREZORHAL_TOUCH_H
#define TREZORHAL_TOUCH_H

#include <stdint.h>

#define TOUCH_START (1U << 24)
#define TOUCH_MOVE  (2U << 24)
#define TOUCH_END   (4U << 24)

void touch_init(void);
uint32_t touch_read(void);
uint32_t touch_click(void);
inline uint16_t touch_get_x(uint32_t evt) { return (evt >> 12) & 0xFFF; }
inline uint16_t touch_get_y(uint32_t evt) { return (evt >> 0) & 0xFFF; }
inline uint32_t touch_pack_xy(uint16_t x, uint16_t y) { return ((x & 0xFFF) << 12) | (y & 0xFFF); }

#endif
