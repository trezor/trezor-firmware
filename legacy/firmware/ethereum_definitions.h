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

#include "messages-definitions.pb.h"
#include "messages-ethereum.pb.h"

typedef EthereumDefinitions_encoded_network_t EncodedNetwork;
typedef EthereumDefinitions_encoded_token_t EncodedToken;

typedef struct {
  const EthereumNetworkInfo *network;
  const EthereumTokenInfo *token;
} EthereumDefinitionsDecoded;

const EthereumDefinitionsDecoded *ethereum_get_definitions(
    const EncodedNetwork *encoded_network, const EncodedToken *encoded_token,
    const uint64_t chain_id, const uint32_t slip44, const char *token_address);

#endif
