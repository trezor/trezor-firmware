/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2016 Alex Beregszaszi <alex@rtfs.hu>
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

#ifndef __ETHEREUM_H__
#define __ETHEREUM_H__

#include <stdbool.h>
#include <stdint.h>
#include "bip32.h"
#include "messages-ethereum.pb.h"

void ethereum_signing_init(const EthereumSignTx *msg, const HDNode *node);
void ethereum_signing_init_eip1559(const EthereumSignTxEIP1559 *msg,
                                   const HDNode *node);
void ethereum_signing_abort(void);
void ethereum_signing_txack(const EthereumTxAck *msg);

void ethereum_message_sign(const EthereumSignMessage *msg, const HDNode *node,
                           EthereumMessageSignature *resp);
int ethereum_message_verify(const EthereumVerifyMessage *msg);
bool ethereum_parse(const char *address, uint8_t pubkeyhash[20]);

#endif
