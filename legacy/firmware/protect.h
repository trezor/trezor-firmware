/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __PROTECT_H__
#define __PROTECT_H__

#include <stdbool.h>
#include "messages-common.pb.h"
#include "secbool.h"

#define MAX_PASSPHRASE_LEN 50

bool protectButton(ButtonRequestType type, bool confirm_only);
secbool protectPinUiCallback(uint32_t wait, uint32_t progress,
                             const char* message);
bool protectPin(bool use_cached);
bool protectChangePin(bool removal);
bool protectChangeWipeCode(bool removal);
bool protectPassphrase(char* passphrase);

extern bool protectAbortedByCancel;
extern bool protectAbortedByInitialize;

#endif
