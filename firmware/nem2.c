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

#include "nem2.h"

#include "aes.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "protect.h"
#include "rng.h"

const char *nem_validate_common(NEMTransactionCommon *common) {
	if (!common->has_network) {
		common->has_network = true;
		common->network = NEM_NETWORK_MAINNET;
	}

	if (nem_network_name(common->network) == NULL) return _("Invalid NEM network");
	if (!common->has_timestamp) return _("No timestamp provided");
	if (!common->has_fee) return _("No fee provided");
	if (!common->has_deadline) return _("No deadline provided");

	return NULL;
}

const char *nem_validate_transfer(const NEMTransfer *transfer, uint8_t network) {
	if (!transfer->has_recipient) return _("No recipient provided");
	if (!transfer->has_amount) return _("No amount provided");
	if (transfer->has_public_key && transfer->public_key.size != 32) return _("Invalid recipient public key");

	if (!nem_validate_address(transfer->recipient, network)) return _("Invalid recipient address");

	for (size_t i = 0; i < transfer->mosaics_count; i++) {
		const NEMMosaic *mosaic = &transfer->mosaics[i];

		if (!mosaic->has_namespace) return "No mosaic namespace provided";
		if (!mosaic->has_mosaic) return "No mosaic name provided";
		if (!mosaic->has_quantity) return "No mosaic quantity provided";
	}

	return NULL;
}


bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer) {
	const char *network = nem_network_name(common->network);
	if (network == NULL) {
		return false;
	}


	if (transfer->mosaics_count) {
		bool done[transfer->mosaics_count];
		memset(done, 0, sizeof(done));

		uint64_t quantity[transfer->mosaics_count];
		uint64_t *xemQuantity = NULL;

		bignum256 mul;
		bn_read_uint64(transfer->amount, &mul);

		for (size_t i = 0; i < transfer->mosaics_count; i++) {
			// Skip duplicate mosaics
			if (done[i]) continue;

			const NEMMosaic *mosaic = &transfer->mosaics[i];

			// XEM is treated specially
			if (strcmp(mosaic->namespace, "nem") == 0 && strcmp(mosaic->mosaic, "xem") == 0) {
				done[i] = true;
				xemQuantity = &quantity[i];
			}

			quantity[i] = mosaic->quantity;
			for (size_t j = i + 1; j < transfer->mosaics_count; j++) {
				const NEMMosaic *new_mosaic = &transfer->mosaics[j];

				if (strcmp(mosaic->namespace, new_mosaic->namespace) == 0 && strcmp(mosaic->mosaic, new_mosaic->mosaic) == 0) {
					// Duplicate mosaics are merged into one
					done[i] = true;
					quantity[i] += transfer->mosaics[j].quantity;
				}
			}
		}

		layoutNEMTransferXEM(network, xemQuantity == NULL ? 0 : *xemQuantity, &mul, common->fee);
		if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
			return false;
		}

		for (size_t i = 0; i < transfer->mosaics_count; i++) {
			// Skip special or duplicate mosaics
			if (done[i]) continue;

			const NEMMosaic *mosaic = &transfer->mosaics[i];

			layoutNEMTransferMosaic(mosaic->namespace, mosaic->mosaic, quantity[i], &mul);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
				return false;
			}
		}
	} else {
		layoutNEMTransferXEM(network, transfer->amount, NULL, common->fee);
		if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
			return false;
		}
	}

	if (transfer->has_payload) {
		layoutNEMTransferPayload(transfer->payload.bytes, transfer->payload.size, transfer->has_public_key);
		if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
			return false;
		}
	}

	layoutNEMTransferTo(network, transfer->recipient);
	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		return false;
	}

	return true;
}

bool nem_fsmTransfer(nem_transaction_ctx *context, const HDNode *node, const NEMTransactionCommon *common, const NEMTransfer *transfer) {
	static uint8_t encrypted[NEM_ENCRYPTED_PAYLOAD_SIZE(sizeof(transfer->payload.bytes))];

	const uint8_t *payload = transfer->payload.bytes;
	size_t size = transfer->payload.size;

	if (transfer->has_public_key) {
		if (node == NULL) {
			fsm_sendFailure(FailureType_Failure_ProcessError, _("Private key unavailable for encrypted message"));
			return false;
		}

		random_buffer(encrypted, NEM_SALT_SIZE + AES_BLOCK_SIZE);

		// hdnode_nem_encrypt mutates the IV
		uint8_t iv[AES_BLOCK_SIZE];
		memcpy(iv, &encrypted[NEM_SALT_SIZE], AES_BLOCK_SIZE);

		const uint8_t *salt = encrypted;
		uint8_t *buffer = &encrypted[NEM_SALT_SIZE + AES_BLOCK_SIZE];

		bool ret = hdnode_nem_encrypt(node,
				transfer->public_key.bytes,
				iv,
				salt,
				payload,
				size,
				buffer);

		if (!ret) {
			fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to encrypt payload"));
			return false;
		}

		payload = encrypted;
		size = NEM_ENCRYPTED_PAYLOAD_SIZE(size);
	}

	bool ret = nem_transaction_create_transfer(context,
			common->network,
			common->timestamp,
			NULL,
			common->fee,
			common->deadline,
			transfer->recipient,
			transfer->amount,
			payload,
			size,
			transfer->has_public_key,
			transfer->mosaics_count);

	if (!ret) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to create transfer transaction"));
		return false;
	}

	for (size_t i = 0; i < transfer->mosaics_count; i++) {
		const NEMMosaic *mosaic = &transfer->mosaics[i];

		ret = nem_transaction_write_mosaic(context,
			mosaic->namespace,
			mosaic->mosaic,
			mosaic->quantity);

		if (!ret) {
			fsm_sendFailure(FailureType_Failure_ProcessError, "Failed to attach mosaics");
			return false;
		}
	}

	return true;
}
