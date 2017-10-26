/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef __TREZORHAL_TOUCH_H__
#define __TREZORHAL_TOUCH_H__

#include <stdint.h>

#define TOUCH_START (1U << 24)
#define TOUCH_MOVE  (2U << 24)
#define TOUCH_END   (4U << 24)

void touch_init(void);
uint32_t touch_read(void);
uint32_t touch_click(void);

#endif
