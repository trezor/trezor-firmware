/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2022 Martin Novak <martin.novak@satoshilabs.com>
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

#ifndef __ETHEREUM_DEFINITIONS_H__
#define __ETHEREUM_DEFINITIONS_H__

#include "messages-ethereum.pb.h"

typedef struct {
  EthereumNetworkInfo network;
  EthereumTokenInfo token;
} EthereumDefinitions;

const EthereumDefinitions *get_EthereumDefinitions(const EthereumEncodedDefinitions_encoded_network_t *encoded_network, const EthereumEncodedDefinitions_encoded_token_t *encoded_token, const uint64_t ref_chain_id, const char *ref_address);

#endif
