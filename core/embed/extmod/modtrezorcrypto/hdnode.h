/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __HDNODE_H__
#define __HDNODE_H__

#include "py/obj.h"

#include "bip32.h"

typedef struct _mp_obj_HDNode_t {
  mp_obj_base_t base;
  uint32_t fingerprint;
  HDNode hdnode;
} mp_obj_HDNode_t;

extern const mp_obj_type_t mod_trezorcrypto_HDNode_type;

#endif
