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
#include "nem_mosaics.h"

#include "messages.pb.h"
#include "types.pb.h"

#include <stdbool.h>

const char *nem_validate_common(NEMTransactionCommon *common, bool inner);
const char *nem_validate_transfer(const NEMTransfer *transfer, uint8_t network);
const char *nem_validate_provision_namespace(const NEMProvisionNamespace *provision_namespace, uint8_t network);
const char *nem_validate_mosaic_creation(const NEMMosaicCreation *mosaic_creation, uint8_t network);

bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer, const char *desc);
bool nem_fsmTransfer(nem_transaction_ctx *context, const HDNode *node, const NEMTransactionCommon *common, const NEMTransfer *transfer);

bool nem_askProvisionNamespace(const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace, const char *desc);
bool nem_fsmProvisionNamespace(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace);

bool nem_askMosaicCreation(const NEMTransactionCommon *common, const NEMMosaicCreation *mosaic_creation, const char *desc, const char *address);
bool nem_fsmMosaicCreation(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMMosaicCreation *mosaic_creation);

bool nem_askMultisig(const char *address, const char *desc, bool cosigning, uint64_t fee);
bool nem_fsmMultisig(nem_transaction_ctx *context, const NEMTransactionCommon *common, const nem_transaction_ctx *inner, bool cosigning);

const NEMMosaicDefinition *nem_mosaicByName(const char *namespace, const char *mosaic);
void nem_mosaicFormatAmount(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, char *str_out, size_t size);
bool nem_mosaicFormatLevy(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, char *str_out, size_t size);
void nem_mosaicFormatName(const char *namespace, const char *mosaic, char *str_out, size_t size);

static inline bool nem_mosaicMatches(const NEMMosaicDefinition *definition, const char *namespace, const char *mosaic) {
    return strcmp(namespace, definition->namespace) == 0 && strcmp(mosaic, definition->mosaic) == 0;
}

#endif
