/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

#include "messages-nem.pb.h"

#include <stdbool.h>

const char *nem_validate_common(NEMTransactionCommon *common, bool inner);
const char *nem_validate_transfer(const NEMTransfer *transfer, uint8_t network);
const char *nem_validate_provision_namespace(const NEMProvisionNamespace *provision_namespace, uint8_t network);
const char *nem_validate_mosaic_creation(const NEMMosaicCreation *mosaic_creation, uint8_t network);
const char *nem_validate_supply_change(const NEMMosaicSupplyChange *supply_change);
const char *nem_validate_aggregate_modification(const NEMAggregateModification *aggregate_modification, bool creation);
const char *nem_validate_importance_transfer(const NEMImportanceTransfer *importance_transfer);

bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer, const char *desc);
bool nem_fsmTransfer(nem_transaction_ctx *context, const HDNode *node, const NEMTransactionCommon *common, const NEMTransfer *transfer);

bool nem_askProvisionNamespace(const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace, const char *desc);
bool nem_fsmProvisionNamespace(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace);

bool nem_askMosaicCreation(const NEMTransactionCommon *common, const NEMMosaicCreation *mosaic_creation, const char *desc, const char *address);
bool nem_fsmMosaicCreation(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMMosaicCreation *mosaic_creation);

bool nem_askSupplyChange(const NEMTransactionCommon *common, const NEMMosaicSupplyChange *supply_change, const char *desc);
bool nem_fsmSupplyChange(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMMosaicSupplyChange *supply_change);

bool nem_askAggregateModification(const NEMTransactionCommon *common, const NEMAggregateModification *aggregate_modification, const char *desc, bool creation);
bool nem_fsmAggregateModification(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMAggregateModification *aggregate_modification);

bool nem_askImportanceTransfer(const NEMTransactionCommon *common, const NEMImportanceTransfer *importance_transfer, const char *desc);
bool nem_fsmImportanceTransfer(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMImportanceTransfer *importance_transfer);

bool nem_askMultisig(const char *address, const char *desc, bool cosigning, uint64_t fee);
bool nem_fsmMultisig(nem_transaction_ctx *context, const NEMTransactionCommon *common, const nem_transaction_ctx *inner, bool cosigning);

const NEMMosaicDefinition *nem_mosaicByName(const char *namespace, const char *mosaic, uint8_t network);

size_t nem_canonicalizeMosaics(NEMMosaic *mosaics, size_t mosaics_count);
void nem_mosaicFormatAmount(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, char *str_out, size_t size);
bool nem_mosaicFormatLevy(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, uint8_t network, char *str_out, size_t size);

static inline void nem_mosaicFormatName(const char *namespace, const char *mosaic, char *str_out, size_t size) {
	strlcpy(str_out, namespace, size);
	strlcat(str_out, ".", size);
	strlcat(str_out, mosaic, size);
}

static inline bool nem_mosaicMatches(const NEMMosaicDefinition *definition, const char *namespace, const char *mosaic, uint8_t network) {
	if (strcmp(namespace, definition->namespace) == 0 && strcmp(mosaic, definition->mosaic) == 0) {
		if (definition->networks_count == 0) {
			return true;
		}

		for (size_t i = 0; i < definition->networks_count; i++) {
			if (definition->networks[i] == network) {
				return true;
			}
		}
	}

	return false;
}

static inline int nem_mosaicCompare(const NEMMosaic *a, const NEMMosaic *b) {
	size_t namespace_length = strlen(a->namespace);

	// Ensure that strlen(a->namespace) <= strlen(b->namespace)
	if (namespace_length > strlen(b->namespace)) {
		return -nem_mosaicCompare(b, a);
	}

	int r = strncmp(a->namespace, b->namespace, namespace_length);

	if (r == 0 && b->namespace[namespace_length] != '\0') {
		// The next character would be the separator
		r = (':' - b->namespace[namespace_length]);
	}

	if (r == 0) {
		// Finally compare the mosaic
		r = strcmp(a->mosaic, b->mosaic);
	}

	return r;
}

#endif
