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
#include "secp256k1.h"

static void format_amount(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, const bignum256 *multiplier2, int divisor, char *str_out, size_t size);

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

const char *nem_validate_provision_namespace(const NEMProvisionNamespace *provision_namespace, uint8_t network) {
	if (!provision_namespace->has_namespace) return _("No namespace provided");
	if (!provision_namespace->has_sink) return _("No rental sink provided");
	if (!provision_namespace->has_fee) return _("No rental sink fee provided");

	if (!nem_validate_address(provision_namespace->sink, network)) return _("Invalid rental sink address");

	return NULL;
}

bool nem_askTransfer(const NEMTransactionCommon *common, const NEMTransfer *transfer, const char *desc) {
	if (transfer->mosaics_count) {
		struct {
			bool skip;
			uint64_t quantity;
			const NEMMosaicDefinition *definition;
		} mosaics[transfer->mosaics_count], *xem = NULL;

		memset(mosaics, 0, sizeof(mosaics));

		bool unknownMosaic = false;

		for (size_t i = 0; i < transfer->mosaics_count; i++) {
			// Skip duplicate mosaics
			if (mosaics[i].skip) continue;

			const NEMMosaic *mosaic = &transfer->mosaics[i];

			if ((mosaics[i].definition = nem_mosaicByName(mosaic->namespace, mosaic->mosaic))) {
				// XEM is displayed separately
				if (mosaics[i].definition == NEM_MOSAIC_DEFINITION_XEM) {
					// Do not display as a mosaic
					mosaics[i].skip = true;
					xem = &mosaics[i];
				}
			} else {
				unknownMosaic = true;
			}

			mosaics[i].quantity = mosaic->quantity;
			for (size_t j = i + 1; j < transfer->mosaics_count; j++) {
				const NEMMosaic *new_mosaic = &transfer->mosaics[j];

				if (nem_mosaicMatches(mosaics[i].definition, new_mosaic->namespace, new_mosaic->mosaic)) {
					// Merge duplicate mosaics
					mosaics[j].skip = true;
					mosaics[i].quantity += new_mosaic->quantity;
				}
			}
		}

		bignum256 multiplier;
		bn_read_uint64(transfer->amount, &multiplier);

		if (unknownMosaic) {
			layoutDialogSwipe(&bmp_icon_question,
				_("Cancel"),
				_("I take the risk"),
				_("Unknown Mosaics"),
				_("Divisibility and levy"),
				_("cannot be shown for"),
				_("unknown mosaics!"),
				NULL,
				NULL,
				NULL);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
				return false;
			}
		}

		layoutNEMTransferXEM(desc, xem ? xem->quantity : 0, &multiplier, common->fee);
		if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
			return false;
		}

		for (size_t i = 0; i < transfer->mosaics_count; i++) {
			// Skip duplicate mosaics or XEM
			if (mosaics[i].skip) continue;

			const NEMMosaic *mosaic = &transfer->mosaics[i];

			if (mosaics[i].definition) {
				layoutNEMTransferMosaic(mosaics[i].definition, mosaics[i].quantity, &multiplier);
			} else {
				layoutNEMTransferUnknownMosaic(mosaic->namespace, mosaic->mosaic, mosaics[i].quantity, &multiplier);
			}

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
		transfer->recipient);
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

bool nem_askProvisionNamespace(const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace, const char *desc) {
	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Next"),
		desc,
		_("Create namespace"),
		provision_namespace->namespace,
		provision_namespace->has_parent ? _("under namespace") : NULL,
		provision_namespace->has_parent ? provision_namespace->parent : NULL,
		NULL,
		NULL);
	if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
		return false;
	}

	layoutNEMNetworkFee(desc, true, _("Confirm rental fee of"), provision_namespace->fee, _("and network fee of"), common->fee);
	if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
		return false;
	}

	return true;
}

bool nem_fsmProvisionNamespace(nem_transaction_ctx *context, const NEMTransactionCommon *common, const NEMProvisionNamespace *provision_namespace) {
	return nem_transaction_create_provision_namespace(context,
		common->network,
		common->timestamp,
		NULL,
		common->fee,
		common->deadline,
		provision_namespace->namespace,
		provision_namespace->has_parent ? provision_namespace->parent : NULL,
		provision_namespace->sink,
		provision_namespace->fee);
}

bool nem_askMultisig(const char *address, const char *desc, bool cosigning, uint64_t fee) {
	layoutNEMDialog(&bmp_icon_question,
		_("Cancel"),
		_("Next"),
		desc,
		cosigning ? _("Cosign transaction for") : _("Initiate transaction for"),
		address);
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

const NEMMosaicDefinition *nem_mosaicByName(const char *namespace, const char *mosaic) {
	for (size_t i = 0; i < NEM_MOSAIC_DEFINITIONS_COUNT; i++) {
		const NEMMosaicDefinition *definition = &NEM_MOSAIC_DEFINITIONS[i];

		if (nem_mosaicMatches(definition, namespace, mosaic)) {
			return definition;
		}
	}

	return NULL;
}

void format_amount(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, const bignum256 *multiplier2, int divisor, char *str_out, size_t size) {
	uint32_t divisibility = definition && definition->has_divisibility ? definition->divisibility : 0;
	const char *ticker = definition && definition->has_ticker ? definition->ticker : NULL;

	bignum256 amnt;
	bn_read_uint64(quantity, &amnt);

	if (multiplier2) {
		bn_multiply(multiplier2, &amnt, &secp256k1.prime);
	}

	// Do not use prefix/suffix with bn_format, it messes with the truncation code
	if (multiplier) {
		bn_multiply(multiplier, &amnt, &secp256k1.prime);
		divisor += NEM_MOSAIC_DEFINITION_XEM->divisibility;
	}

	// bn_format(amnt / (10 ^ divisor), divisibility)
	bn_format(&amnt, NULL, NULL, divisibility + divisor, str_out, size);

	// Truncate as if we called bn_format with (divisibility) instead of (divisibility + divisor)
	char *decimal = strchr(str_out, '.');
	if (decimal != NULL) {
		const char *terminator = strchr(str_out, '\0');

		if (divisibility == 0) {
			// Truncate as an integer
			*decimal = '\0';
		} else {
			char *end = decimal + divisibility + 1;
			if (end < terminator) {
				*end = '\0';
			}
		}
	}

	if (ticker) {
		strlcat(str_out, " ", size);
		strlcat(str_out, ticker, size);
	}
}

void nem_mosaicFormatAmount(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, char *str_out, size_t size) {
	format_amount(definition, quantity, multiplier, NULL, 0, str_out, size);
}

bool nem_mosaicFormatLevy(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, char *str_out, size_t size) {
	bignum256 multiplier2;

	if (!definition->has_levy || !definition->has_fee) {
		return false;
	}

	switch (definition->levy) {
	case NEMMosaicLevy_MosaicLevy_Absolute:
		format_amount(definition, definition->fee, NULL, NULL, 0, str_out, size);
		break;

	case NEMMosaicLevy_MosaicLevy_Percentile:
		bn_read_uint64(definition->fee, &multiplier2);
		format_amount(definition, quantity, multiplier, &multiplier2, NEM_LEVY_PERCENTILE_DIVISOR, str_out, size);
		break;

	default:
		return false;
	}

	return true;
}
