/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
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

#ifndef __ETHEREUM_NETWORKS_H__
#define __ETHEREUM_NETWORKS_H__

#include <stdbool.h>
#include <stdint.h>

#define SLIP44_UNKNOWN UINT32_MAX
#define UNKNOWN_NETWORK_SHORTCUT " UNKN"

const char *get_ethereum_suffix(uint64_t chain_id);
bool is_ethereum_slip44(uint32_t slip44);
uint32_t ethereum_slip44_by_chain_id(uint64_t chain_id);

#endif
