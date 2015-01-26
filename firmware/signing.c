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
#include "crypto.h"

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
static bool multisig_fp_set, multisig_fp_mismatch;
static uint8_t multisig_fp[32];

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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
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
	layoutProgress("Signing transaction", 1000 * progress / progress_total);
	resp.has_request_type = true;
	resp.request_type = RequestType_TXFINISHED;
	msg_write(MessageType_MessageType_TxRequest, &resp);
}

void signing_init(uint32_t _inputs_count, uint32_t _outputs_count, const CoinType *_coin, const HDNode *_root)
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
	progress_total = inputs_count * (1 + inputs_count + outputs_count) + outputs_count + 1;

	multisig_fp_set = false;
	multisig_fp_mismatch = false;

	tx_init(&to, inputs_count, outputs_count, version, lock_time, false);

	layoutProgressSwipe("Signing transaction", 0);

	send_req_1_input();
}

void signing_txack(TransactionType *tx)
{
	if (!signing) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Signing mode");
		layoutHome();
		return;
	}

	layoutProgress("Signing transaction", 1000 * progress / progress_total);

	int co;
	memset(&resp, 0, sizeof(TxRequest));

	switch (signing_stage) {
		case STAGE_REQUEST_1_INPUT:
			progress++;
			memcpy(&input, tx->inputs, sizeof(TxInputType));
			send_req_2_prev_meta();
			return;
		case STAGE_REQUEST_2_PREV_META:
			tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time, false);
			send_req_2_prev_input();
			return;
		case STAGE_REQUEST_2_PREV_INPUT:
			if (!tx_serialize_input_hash(&tp, tx->inputs)) {
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
			if (!tx_serialize_output_hash(&tp, tx->bin_outputs)) {
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
			progress++;
			if (!tx_serialize_input_hash(&tc, tx->inputs)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize input");
				signing_abort();
				return;
			}
			if (idx1i == 0) {
				if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG &&
				    tx->inputs[0].has_multisig && !multisig_fp_mismatch) {
					if (multisig_fp_set) {
						uint8_t h[32];
						if (cryptoMultisigFingerprint(&(tx->inputs[0].multisig), h) == 0) {
							fsm_sendFailure(FailureType_Failure_Other, "Error computing multisig fingeprint");
							signing_abort();
							return;
						}
						if (memcmp(multisig_fp, h, 32) != 0) {
							multisig_fp_mismatch = true;
						}
					} else {
						if (cryptoMultisigFingerprint(&(tx->inputs[0].multisig), multisig_fp) == 0) {
							fsm_sendFailure(FailureType_Failure_Other, "Error computing multisig fingeprint");
							signing_abort();
							return;
						}
						multisig_fp_set = true;
					}
				}
			}
			if (idx3i == idx1i) {
				memcpy(&node, root, sizeof(HDNode));
				if (hdnode_private_ckd_cached(&node, tx->inputs[0].address_n, tx->inputs[0].address_n_count) == 0) {
					fsm_sendFailure(FailureType_Failure_Other, "Failed to derive private key");
					signing_abort();
					return;
				}
				if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG) {
					if (!tx->inputs[0].has_multisig) {
						fsm_sendFailure(FailureType_Failure_Other, "Multisig info not provided");
						signing_abort();
						return;
					}
					tx->inputs[0].script_sig.size = compile_script_multisig(&(tx->inputs[0].multisig), tx->inputs[0].script_sig.bytes);
				} else { // SPENDADDRESS
					ecdsa_get_pubkeyhash(node.public_key, hash);
					tx->inputs[0].script_sig.size = compile_script_sig(coin->address_type, hash, tx->inputs[0].script_sig.bytes);
				}
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
			if (!tx_serialize_input_hash(&ti, tx->inputs)) {
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
			progress++;
			if (idx1i == 0) {
				bool is_change = false;
				if (tx->outputs[0].script_type == OutputScriptType_PAYTOMULTISIG &&
				    tx->outputs[0].has_multisig &&
				    multisig_fp_set && !multisig_fp_mismatch) {
					uint8_t h[32];
					if (cryptoMultisigFingerprint(&(tx->outputs[0].multisig), h) == 0) {
						fsm_sendFailure(FailureType_Failure_Other, "Error computing multisig fingeprint");
						signing_abort();
						return;
					}
					if (memcmp(multisig_fp, h, 32) == 0) {
						is_change = true;
					}
				} else
				if (tx->outputs[0].script_type == OutputScriptType_PAYTOADDRESS &&
				    tx->outputs[0].address_n_count > 0) {
					is_change = true;
				}
				if (is_change) {
					if (change_spend == 0) { // not set
						change_spend = tx->outputs[0].amount;
					} else {
						fsm_sendFailure(FailureType_Failure_Other, "Only one change output allowed");
						signing_abort();
						return;
					}
				}
				spending += tx->outputs[0].amount;
				co = compile_output(coin, root, tx->outputs, &bin_output, !is_change);
				if (!is_change) {
					layoutProgress("Signing transaction", 1000 * progress / progress_total);
				}
			} else {
				co = compile_output(coin, root, tx->outputs, &bin_output, false);
			}
			if (co < 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Signing cancelled by user");
				signing_abort();
				return;
			} else if (co == 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to compile output");
				signing_abort();
				return;
			}
			if (!tx_serialize_output_hash(&tc, &bin_output)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize output");
				signing_abort();
				return;
			}
			if (!tx_serialize_output_hash(&ti, &bin_output)) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize output");
				signing_abort();
				return;
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
				ecdsa_sign_digest(privkey, hash, sig, 0);
				resp.serialized.signature.size = ecdsa_sig_to_der(sig, resp.serialized.signature.bytes);
				if (input.script_type == InputScriptType_SPENDMULTISIG) {
					if (!input.has_multisig) {
						fsm_sendFailure(FailureType_Failure_Other, "Multisig info not provided");
						signing_abort();
						return;
					}
					// fill in the signature
					int pubkey_idx = cryptoMultisigPubkeyIndex(&(input.multisig), pubkey);
					if (pubkey_idx < 0) {
						fsm_sendFailure(FailureType_Failure_Other, "Pubkey not found in multisig script");
						signing_abort();
						return;
					}
					memcpy(input.multisig.signatures[pubkey_idx].bytes, resp.serialized.signature.bytes, resp.serialized.signature.size);
					input.multisig.signatures[pubkey_idx].size = resp.serialized.signature.size;
					input.script_sig.size = serialize_script_multisig(&(input.multisig), input.script_sig.bytes);
					if (input.script_sig.size == 0) {
						fsm_sendFailure(FailureType_Failure_Other, "Failed to serialize multisig script");
						signing_abort();
						return;
					}
				} else { // SPENDADDRESS
					input.script_sig.size = serialize_script_sig(resp.serialized.signature.bytes, resp.serialized.signature.size, pubkey, 33, input.script_sig.bytes);
				}
				resp.serialized.serialized_tx.size = tx_serialize_input(&to, &input, resp.serialized.serialized_tx.bytes);
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
					uint32_t tx_est_size = transactionEstimateSizeKb(inputs_count, outputs_count);
					if (fee > (uint64_t)tx_est_size * coin->maxfee_kb) {
						layoutFeeOverThreshold(coin, fee, tx_est_size);
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
			progress++;
			if (compile_output(coin, root, tx->outputs, &bin_output, false) <= 0) {
				fsm_sendFailure(FailureType_Failure_Other, "Failed to compile output");
				signing_abort();
				return;
			}
			resp.has_serialized = true;
			resp.serialized.has_serialized_tx = true;
			resp.serialized.serialized_tx.size = tx_serialize_output(&to, &bin_output, resp.serialized.serialized_tx.bytes);
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
