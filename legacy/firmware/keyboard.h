/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2019 SatoshiLabs
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

#ifndef __KEYBOARD_H__
#define __KEYBOARD_H__

#include <stdbool.h>
#include "messages-common.pb.h"
#include "secbool.h"

const char *passphrase_keyboard(const char *text);
const char *pin_keyboard(const char *text);

#endif
