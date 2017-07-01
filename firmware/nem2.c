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

const char *nem_validate_common(NEMTransactionCommon *common, bool inner) {
	if (!common->has_network) {
		common->has_network = true;
		common->network = NEM_NETWORK_MAINNET;
	}

	if (nem_network_name(common->network) == NULL) {
		return inner ? _("Invalid NEM network in inner transaction") : _("Invalid NEM network");
	}

	if (!common->has_timestamp) {
		return inner ? _("No timestamp provided in inner transaction") : _("No timestamp provided");
	}

	if (!common->has_fee) {
		return inner ? _("No fee provided in inner transaction") : _("No fee provided");
	}

	if (!common->has_deadline) {
		return inner ? _("No deadline provided in inner transaction") : _("No deadline provided");
	}

	if (inner != common->has_signer) {
		return inner ? _("No signer provided in inner transaction") : _("Signer not allowed in outer transaction");
	}

	if (common->has_signer && common->signer.size != sizeof(ed25519_public_key)) {
		return _("Invalid signer public key in inner transaction");
	}

	return NULL;
}

const char *nem_validate_transfer(const NEMTransfer *transfer, uint8_t network) {
	if (!transfer->has_recipient) return _("No recipient provided");
	if (!transfer->has_amount) return _("No amount provided");

	if (transfer->has_public_key && transfer->public_key.size != sizeof(ed25519_public_key)) {
		return _("Invalid recipient public key");
	}

	if (!nem_validate_address(transfer->recipient, network)) return _("Invalid recipient address");

	for (size_t i = 0; i < transfer->mosaics_count; i++) {
		const NEMMosaic *mosaic = &transfer->mosaics[i];

		if (!mosaic->has_namespace) return _("No mosaic namespace provided");
		if (!mosaic->has_mosaic) return _("No mosaic name provided");
		if (!mosaic->has_quantity) return _("No mosaic quantity provided");
	}

	return NULL;
}


bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer, const char *desc) {
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

		layoutNEMTransferXEM(desc, xemQuantity == NULL ? 0 : *xemQuantity, &mul, common->fee);
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
		layoutNEMTransferXEM(desc, transfer->amount, NULL, common->fee);
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

	layoutNEMDialog(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		desc,
		_("Confirm transfer to"),
		transfer->recipient,
		NULL,
		NULL);
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
			fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to attach mosaics"));
			return false;
		}
	}

	return true;
}

bool nem_askMultisig(const char *address, const char *desc, bool cosigning, uint64_t fee) {
	layoutNEMDialog(&bmp_icon_question,
		_("Cancel"),
		_("Next"),
		desc,
		cosigning ? _("Cosign transaction for") : _("Initiate transaction for"),
		address,
		NULL,
		NULL);

	if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
		return false;
	}

	layoutNEMNetworkFee(desc, false, _("Confirm multisig fee"), fee, NULL, 0);

	if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
		return false;
	}

	return true;
}

bool nem_fsmMultisig(nem_transaction_ctx *context, const NEMTransactionCommon *common, const nem_transaction_ctx *inner, bool cosigning) {
	bool ret;
	if (cosigning) {
		ret = nem_transaction_create_multisig_signature(context,
			common->network,
			common->timestamp,
			NULL,
			common->fee,
			common->deadline,
			inner);
	} else {
		ret = nem_transaction_create_multisig(context,
			common->network,
			common->timestamp,
			NULL,
			common->fee,
			common->deadline,
			inner);
	}

	if (!ret) {
		fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to create multisig transaction"));
		return false;
	}

	return true;
}
