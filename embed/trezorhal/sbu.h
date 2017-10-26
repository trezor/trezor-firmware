/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef __TREZORHAL_SBU_H__
#define __TREZORHAL_SBU_H__

#include "secbool.h"

void sbu_init(void);
void sbu_set(secbool sbu1, secbool sbu2);

#endif
