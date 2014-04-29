/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include "signing.h"
#include "fsm.h"
#include "layout2.h"
#include "messages.h"
#include "transaction.h"
#include "ecdsa.h"
#include "protect.h"

static uint32_t inputs_count;
static uint32_t outputs_count;
static const CoinType *coin;
static const HDNode *root;
static HDNode node;
static bool signing = false;
enum {
	STAGE_REQUEST_1_INPUT,
	STAGE_REQUEST_2_PREV_META,
	STAGE_REQUEST_2_PREV_INPUT,
	STAGE_REQUEST_2_PREV_OUTPUT,
	STAGE_REQUEST_3_INPUT,
	STAGE_REQUEST_3_OUTPUT,
	STAGE_REQUEST_4_OUTPUT
} signing_stage;
static uint32_t idx1i, idx2i, idx2o, idx3i, idx3o, idx4o;
static TxRequest resp;
static TxInputType input;
static TxOutputBinType bin_output;
static TxStruct to, tp, ti, tc;
static uint8_t hash[32], hash_check[32], privkey[32], pubkey[33], sig[64];
static uint64_t to_spend, spending, change_spend;
const uint32_t version = 1;
const uint32_t lock_time = 0;
static uint32_t progress, progress_total;

/*
Workflow of streamed signing

I - input
O - output

foreach I:
    Request I                                                         STAGE_REQUEST_1_INPUT

    Calculate amount of I:
        Request prevhash I, META                                      STAGE_REQUEST_2_PREV_META
        foreach prevhash I:                                           STAGE_REQUEST_2_PREV_INPUT
            Request prevhash I
        foreach prevhash O:                                           STAGE_REQUEST_2_PREV_OUTPUT
            Request prevhash O
            Store amount of I
        Calculate hash of streamed tx, compare to prevhash I

    foreach I:                                                        STAGE_REQUEST_3_INPUT
        Request I
        If I == I-to-be-signed:
            Fill scriptsig
        Add I to StreamTransactionSign
    foreach O:
        Request O                                                     STAGE_REQUEST_3_OUTPUT
        If I=0:
            Display output
            Ask for confirmation
        Add O to StreamTransactionSign

    If I=0:
        Check tx fee
        Calculate txhash
    else:
        Compare current hash with txhash
        If different:
            Failure

    Sign StreamTransactionSign
    Return signed chunk
 */

void send_req_1_input(void)
{
	idx2i = idx2o = idx3i = idx3o = 0;
	signing_stage = STAGE_REQUEST_1_INPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXINPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx1i;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_prev_meta(void)
{
	signing_stage = STAGE_REQUEST_2_PREV_META;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXMETA;
	resp.has_details = true;
	resp.details.has_tx_hash = true;
	resp.details.tx_hash.size = input.prev_hash.size;
	memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes, input.prev_hash.size);
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_prev_input(void)
{
	signing_stage = STAGE_REQUEST_2_PREV_INPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXINPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx2i;
	resp.details.has_tx_hash = true;
	resp.details.tx_hash.size = input.prev_hash.size;
	memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes, resp.details.tx_hash.size);
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_prev_output(void)
{
	signing_stage = STAGE_REQUEST_2_PREV_OUTPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXOUTPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx2o;
	resp.details.has_tx_hash = true;
	resp.details.tx_hash.size = input.prev_hash.size;
	memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes, resp.details.tx_hash.size);
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_input(void)
{
	signing_stage = STAGE_REQUEST_3_INPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXINPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx3i;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_output(void)
{
	signing_stage = STAGE_REQUEST_3_OUTPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXOUTPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx3o;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_4_output(void)
{
	signing_stage = STAGE_REQUEST_4_OUTPUT;
	resp.has_request_type = true;
	resp.request_type = RequestType_TXOUTPUT;
	resp.has_details = true;
	resp.details.has_request_index = true;
	resp.details.request_index = idx4o;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_finished(void)
{
	resp.has_request_type = true;
	resp.request_type = RequestType_TXFINISHED;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void signing_init(uint32_t _inputs_count, uint32_t _outputs_count, const CoinType *_coin, HDNode *_root)
{
	inputs_count = _inputs_count;
	outputs_count = _outputs_count;
	coin = _coin;
	root = _root;

	idx1i = idx2i = idx2o = idx3i = idx3o = idx4o = 0;
	to_spend = 0;
	spending = 0;
	change_spend = 0;
	memset(&input, 0, sizeof(TxInputType));
	memset(&resp, 0, sizeof(TxRequest));

	signing = true;
	progress = 1;
	progress_total = inputs_count * (1 + inputs_count + outputs_count) + outputs_count;

	tx_init(&to, inputs_count, outputs_count, version, lock_time, false);

	send_req_1_input();
}

void signing_txack(TransactionType *tx)
{
	if (!signing) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Signing mode");
		layoutHome();
		return;
	}

	int co;

	memset(&resp, 0, sizeof(TxRequest));

	switch (signing_stage) {
		case STAGE_REQUEST_1_INPUT:
			layoutProgress("Signing", 1000 * progress / progress_total, progress); progress++;
			memcpy(&input, tx->inputs, sizeof(TxInputType));
			send_req_2_prev_meta();
			return;
		case STAGE_REQUEST_2_PREV_META:
			tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time, false);
			send_req_2_prev_input();
			return;
		case STAGE_REQUEST_2_PREV_INPUT:
			if (!tx_hash_input(&tp, tx->inputs)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize input");
				signing_abort();
				return;
			}
			if (idx2i < tp.inputs_len - 1) {
				idx2i++;
				send_req_2_prev_input();
			} else {
				send_req_2_prev_output();
			}
			return;
		case STAGE_REQUEST_2_PREV_OUTPUT:
			if (!tx_hash_output(&tp, tx->bin_outputs)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize output");
				signing_abort();
				return;
			}
			if (idx2o == input.prev_index) {
				to_spend += tx->bin_outputs[0].amount;
			}
			if (idx2o < tp.outputs_len - 1) {
				idx2o++;
				send_req_2_prev_output();
			} else {
				tx_hash_final(&tp, hash, true);
				if (memcmp(hash, input.prev_hash.bytes, 32) != 0) {
					fsm_sendFailure(FailureType_Failure_Other, "Encountered invalid prevhash");
					signing_abort();
					return;
				}
				tx_init(&ti, inputs_count, outputs_count, version, lock_time, true);
				tx_init(&tc, inputs_count, outputs_count, version, lock_time, true);
				memset(privkey, 0, 32);
				memset(pubkey, 0, 33);
				send_req_3_input();
			}
			return;
		case STAGE_REQUEST_3_INPUT:
			layoutProgress("Signing", 1000 * progress / progress_total, progress); progress++;
			if (!tx_hash_input(&tc, tx->inputs)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize input");
				signing_abort();
				return;
			}
			if (idx3i == idx1i) {
				memcpy(&node, root, sizeof(HDNode));
				uint32_t k;
				for (k = 0; k < tx->inputs[0].address_n_count; k++) {
					hdnode_private_ckd(&node, tx->inputs[0].address_n[k]);
				}
				ecdsa_get_pubkeyhash(node.public_key, hash);
				tx->inputs[0].script_sig.size = compile_script_sig(coin->address_type, hash, tx->inputs[0].script_sig.bytes);
				if (tx->inputs[0].script_sig.size == 0) {
					fsm_sendFailure(FailureType_Failure_Other, "Failed to compile input");
					signing_abort();
					return;
				}
				memcpy(privkey, node.private_key, 32);
				memcpy(pubkey, node.public_key, 33);
			} else {
				tx->inputs[0].script_sig.size = 0;
			}
			if (!tx_hash_input(&ti, tx->inputs)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize input");
				signing_abort();
				return;
			}
			if (idx3i < inputs_count - 1) {
				idx3i++;
				send_req_3_input();
			} else {
				send_req_3_output();
			}
			return;
		case STAGE_REQUEST_3_OUTPUT:
			layoutProgress("Signing", 1000 * progress / progress_total, progress); progress++;
			co = compile_output(coin, root, tx->outputs, &bin_output, idx1i == 0);
			if (co < 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Signing cancelled by user");
				signing_abort();
				return;
			} else if (co == 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to compile output");
				signing_abort();
				return;
			}
			if (!tx_hash_output(&tc, &bin_output)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize output");
				signing_abort();
				return;
			}
			if (!tx_hash_output(&ti, &bin_output)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize output");
				signing_abort();
				return;
			}
			if (idx1i == 0) {
				if (tx->outputs[0].address_n_count > 0) { // address_n set -> change address
					if (change_spend == 0) { // not set
						change_spend = tx->outputs[0].amount;
					} else {
						fsm_sendFailure(FailureType_Failure_Other, "Only one change output allowed");
						signing_abort();
						return;
					}
				}
				spending += tx->outputs[0].amount;
			}
			if (idx3o < outputs_count - 1) {
				idx3o++;
				send_req_3_output();
			} else {
				if (idx1i == 0) {
					tx_hash_final(&tc, hash_check, false);
				} else {
					tx_hash_final(&tc, hash, false);
					if (memcmp(hash, hash_check, 32) != 0) {
						fsm_sendFailure(FailureType_Failure_Other, "Transaction has changed during signing");
						signing_abort();
						return;
					}
				}
				tx_hash_final(&ti, hash, false);
				resp.has_serialized = true;
				resp.serialized.has_signature_index = true;
				resp.serialized.signature_index = idx1i;
				resp.serialized.has_signature = true;
				resp.serialized.has_serialized_tx = true;
				ecdsa_sign_digest(privkey, hash, sig);
				resp.serialized.signature.size = ecdsa_sig_to_der(sig, resp.serialized.signature.bytes);
				input.script_sig.size = serialize_script_sig(resp.serialized.signature.bytes, resp.serialized.signature.size, pubkey, 33, input.script_sig.bytes);
				resp.serialized.serialized_tx.size = tx_serialize_input(&to, input.prev_hash.bytes, input.prev_index, input.script_sig.bytes, input.script_sig.size, input.sequence, resp.serialized.serialized_tx.bytes);
				if (idx1i < inputs_count - 1) {
					idx1i++;
					send_req_1_input();
				} else {
					if (spending > to_spend) {
						fsm_sendFailure(FailureType_Failure_NotEnoughFunds, "Not enough funds");
						layoutHome();
						return;
					}
					uint64_t fee = to_spend - spending;
					if (fee > (((uint64_t)tc.size + 999) / 1000) * coin->maxfee_kb) {
						layoutFeeOverThreshold(coin, fee, ((uint64_t)tc.size + 999) / 1000);
						if (!protectButton(ButtonRequestType_ButtonRequest_FeeOverThreshold, false)) {
							fsm_sendFailure(FailureType_Failure_ActionCancelled, "Fee over threshold. Signing cancelled.");
							layoutHome();
							return;
						}
					}
					// last confirmation
					layoutConfirmTx(coin, to_spend - change_spend - fee, fee);
					if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
						fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled by user");
						signing_abort();
						return;
					}
					send_req_4_output();
				}
			}
			return;
		case STAGE_REQUEST_4_OUTPUT:
			layoutProgress("Signing", 1000 * progress / progress_total, progress); progress++;
			if (compile_output(coin, root, tx->outputs, &bin_output, false) <= 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to compile output");
				signing_abort();
				return;
			}
			resp.has_serialized = true;
			resp.serialized.has_serialized_tx = true;
			resp.serialized.serialized_tx.size = tx_serialize_output(&to, bin_output.amount, bin_output.script_pubkey.bytes, bin_output.script_pubkey.size, resp.serialized.serialized_tx.bytes);
			if (idx4o < outputs_count - 1) {
				idx4o++;
				send_req_4_output();
			} else {
				send_req_finished();
				signing_abort();
			}
			return;
	}

	fsm_sendFailure(FailureType_Failure_Other, "Signing error");
	signing_abort();
}

void signing_abort(void)
{
	if (signing) {
		layoutHome();
		signing = false;
	}
}
