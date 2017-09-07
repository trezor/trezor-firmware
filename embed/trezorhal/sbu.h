/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef __TREZORHAL_SBU_H__
#define __TREZORHAL_SBU_H__

#include <stdbool.h>

int sbu_init(void);
void sbu_set(bool sbu1, bool sbu2);

#endif
