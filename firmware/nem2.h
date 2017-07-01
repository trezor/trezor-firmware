/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2017 Saleem Rashid <dev@saleemrashid.com>
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

#ifndef __NEM2_H__
#define __NEM2_H__

#include "nem.h"

#include "messages.pb.h"
#include "types.pb.h"

#include <stdbool.h>

const char *nem_validate_common(NEMTransactionCommon *common, bool inner);
const char *nem_validate_transfer(const NEMTransfer *transfer, uint8_t network);

bool nem_askTransaction(const char *desc, const NEMTransactionCommon *common, const NEMSignTx *msg);
bool nem_fsmTransaction(nem_transaction_ctx *context, const HDNode *node, const NEMTransactionCommon *common, const NEMSignTx *msg);

bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer, const char *desc);
bool nem_fsmTransfer(nem_transaction_ctx *context, const HDNode *node, const NEMTransactionCommon *common, const NEMTransfer *transfer);

bool nem_askMultisig(const char *address, const char *desc, bool cosigning, uint64_t fee);
bool nem_fsmMultisig(nem_transaction_ctx *context, const NEMTransactionCommon *common, const nem_transaction_ctx *inner, bool cosigning);

#endif
