/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2023 Trezor Company s.r.o.
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

#ifndef __ETHEREUM_TOKENS_H__
#define __ETHEREUM_TOKENS_H__

#include <stdint.h>
#include "ethereum_definitions.h"

extern const EthereumTokenInfo UNKNOWN_TOKEN;

const EthereumTokenInfo *ethereum_token_by_address(uint64_t chain_id,
                                                   const uint8_t *address);
bool is_unknown_token(const EthereumTokenInfo *token);

#endif
