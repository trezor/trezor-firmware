/*
 * This file is part of the Trezor project, https://trezor.io/
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
#include "config.h"
#include "crypto.h"
#include "ecdsa.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "protect.h"
#include "secp256k1.h"
#include "transaction.h"
#include "zkp_bip340.h"
#if DEBUG_LINK
#include <inttypes.h>
#include <stdio.h>
#endif

static uint32_t change_count;
static const CoinInfo *coin;
static AmountUnit amount_unit;
static bool serialize;
static CONFIDENTIAL HDNode root;
static CONFIDENTIAL HDNode node;
static bool signing = false;
enum {
  STAGE_REQUEST_1_INPUT,
  STAGE_REQUEST_1_ORIG_META,
  STAGE_REQUEST_1_ORIG_INPUT,
  STAGE_REQUEST_2_OUTPUT,
  STAGE_REQUEST_2_ORIG_OUTPUT,
#if !BITCOIN_ONLY
  STAGE_REQUEST_2_ORIG_EXTRADATA,
#endif
  STAGE_REQUEST_3_INPUT,
  STAGE_REQUEST_3_PREV_META,
  STAGE_REQUEST_3_PREV_INPUT,
  STAGE_REQUEST_3_PREV_OUTPUT,
#if !BITCOIN_ONLY
  STAGE_REQUEST_3_PREV_EXTRADATA,
#endif
  STAGE_REQUEST_3_ORIG_INPUT,
  STAGE_REQUEST_3_ORIG_OUTPUT,
  STAGE_REQUEST_3_ORIG_NONLEGACY_INPUT,
  STAGE_REQUEST_4_INPUT,
  STAGE_REQUEST_4_OUTPUT,
  STAGE_REQUEST_NONLEGACY_INPUT,
  STAGE_REQUEST_5_OUTPUT,
  STAGE_REQUEST_SEGWIT_WITNESS,
#if !BITCOIN_ONLY
  STAGE_REQUEST_DECRED_WITNESS,
#endif
} signing_stage;
static bool foreign_address_confirmed;  // indicates that user approved warning
static bool taproot_only;  // indicates whether all internal inputs are Taproot
static bool has_unverified_external_input;
static uint32_t idx1;  // The index of the input or output in the current tx
                       // which is being processed, signed or serialized.
static uint32_t idx2;  // The index of the input or output in the original tx
                       // (Phase 1), in the previous tx (Phase 2) or in the
                       // current tx when computing the legacy digest (Phase 2).
static uint32_t external_inputs[16];  // bitfield of external input indices
static uint32_t signatures;
static TxRequest resp;
static TxInputType input;
static TxOutputType output;
static TxOutputBinType bin_output;
static TxStruct to;  // Used to serialize the current transaction.
static TxStruct tp;  // Used to compute TXID of original tx in Phase 1 and
                     // previous tx in Phase 2.
static TxStruct ti;  // Used in Phase 1 to compute original legacy digest or
                     // Decred hashPrefix, and in Phase 2 to compute legacy
                     // digest or Decred witness hash.
static Hasher hasher_check;
static uint8_t CONFIDENTIAL privkey[32];
static uint8_t pubkey[33];  // Used in Phase 2 to compile scriptSig when signing
                            // legacy inputs.
static uint8_t sig[64];     // Used in Phase 1 to store signature of original tx
                            // and in Phase 2 as a temporary signature buffer.
#if !BITCOIN_ONLY
static uint8_t decred_hash_prefix[32];
#endif
static uint64_t total_in, external_in, total_out, change_out;
static uint64_t orig_total_in, orig_external_in, orig_total_out,
    orig_change_out;
static uint32_t progress_step, progress_steps, progress_substep,
    progress_substeps, progress_midpoint, progress_update;
static const char *progress_label;
static uint32_t tx_weight, tx_base_weight, our_weight, our_inputs_len;
PathSchema unlocked_schema;

typedef enum _MatchState {
  MatchState_UNDEFINED = 0,
  MatchState_MATCH = 1,
  MatchState_MISMATCH = 2,
} MatchState;

typedef struct {
  uint32_t inputs_count;
  uint32_t outputs_count;
  uint32_t segwit_count;
  uint32_t next_legacy_input;
  uint32_t min_sequence;
  bool multisig_fp_set;
  bool multisig_fp_mismatch;
  uint8_t multisig_fp[32];
  bool is_multisig;
  MatchState is_multisig_state;
  uint32_t in_address_n[8];
  size_t in_address_n_count;
  InputScriptType in_script_type;
  MatchState in_script_type_state;
  uint32_t version;
  uint32_t lock_time;
  uint32_t expiry;
  uint32_t version_group_id;
  uint32_t timestamp;
#if !BITCOIN_ONLY
  uint32_t branch_id;
  uint8_t hash_header[32];
#endif
  Hasher hasher_check;
  Hasher hasher_prevouts;
  Hasher hasher_amounts;
  Hasher hasher_scriptpubkeys;
  Hasher hasher_sequences;
  Hasher hasher_outputs;
  uint8_t hash_inputs_check[32];
  uint8_t hash_prevouts[32];
  uint8_t hash_amounts[32];
  uint8_t hash_scriptpubkeys[32];
  uint8_t hash_sequences[32];
  uint8_t hash_outputs[32];
  uint8_t hash_prevouts143[32];
  uint8_t hash_outputs143[32];
  uint8_t hash_sequence143[32];
} TxInfo;

static TxInfo info;

/* Variables specific to replacement transactions. */
static bool is_replacement;  // Is this a replacement transaction?
static TxInfo orig_info;
static uint8_t orig_hash[32];  // TXID of the original transaction.

/* Variables specific to CoinJoin transactions. */
static secbool is_coinjoin;  // Is this a CoinJoin transaction?
static uint64_t coinjoin_coordination_fee_base;
static AuthorizeCoinJoin coinjoin_authorization;
static CoinJoinRequest coinjoin_request;

/* A marker for in_address_n_count to indicate a mismatch in bip32 paths in
   input */
#define BIP32_NOCHANGEALLOWED 1

/* transaction header size: 4 byte version */
#define TXSIZE_HEADER 4
/* transaction footer size: 4 byte lock time */
#define TXSIZE_FOOTER 4
/* transaction segwit overhead 2 marker */
#define TXSIZE_SEGWIT_OVERHEAD 2

/* The maximum number of change-outputs allowed without user confirmation. */
#define MAX_SILENT_CHANGE_COUNT 2

/* The maximum number of inputs allowed in a transaction is limited by the
 * number of external inputs that the firmware can count. */
#define MAX_INPUTS_COUNT (sizeof(external_inputs) * 8)

/* Setting nSequence to this value for every input in a transaction disables
   nLockTime. */
#define SEQUENCE_FINAL 0xffffffff

/* Setting nSequence to a value greater than this for every input in a
   transaction disables replace-by-fee opt-in. */
#define MAX_BIP125_RBF_SEQUENCE 0xFFFFFFFD

/* supported version of Decred script_version */
#define DECRED_SCRIPT_VERSION 0

enum {
  DECRED_SERIALIZE_FULL = 0,
  DECRED_SERIALIZE_NO_WITNESS = 1,
  DECRED_SERIALIZE_WITNESS_SIGNING = 3,
};

/* progress_step/meta_step are fixed point numbers, giving the
 * progress per input in permille with these many additional bits.
 */
#define PROGRESS_PRECISION 16

/*
clang-format off

Workflow of streamed signing
The STAGE_ constants describe the signing_stage when request is sent.

I - input
O - output

Phase1 - process inputs
       - confirm outputs
       - check fee and confirm totals
       - check previous transactions
=========================================================

Stage 1: Get inputs and optionally get original inputs.
foreach I (idx1):
    Request I                                                 STAGE_REQUEST_1_INPUT
    Add I to segwit sub-hashes
    Add I to Decred decred_hash_prefix
    Add I to TransactionChecksum (prevout and type)
    if (I has orig_hash)
        Request input I2 orig_hash, orig_index                STAGE_REQUEST_1_ORIG_INPUT
        Check I matches I2
        Add I2 to original segwit sub-hashes
        Add I2 to orig_info.hash_inputs_check
    if (Decred)
        Return I

Stage 2: Get outputs and optionally get original outputs.
foreach O (idx1):
    Request O                                                 STAGE_REQUEST_2_OUTPUT
    Add O to Decred decred_hash_prefix
    Add O to TransactionChecksum
    if (is_replacement)
        Request output O2 orig_hash, orig_index               STAGE_REQUEST_2_ORIG_OUTPUT
        Check O matches O2
        Add O2 to orig_hash_outputs
    if (Decred)
        Return O
    if (!is_change and !is_replacement)
        Display output
        Ask for confirmation

Check tx fee
Ask for confirmation

Stage 3: Check transaction.

if (taproot_only)
    Skip checking of previous transactions.

foreach I (idx1):
    Request I                                                 STAGE_REQUEST_3_INPUT
    Request prevhash I, META                                  STAGE_REQUEST_3_PREV_META
    foreach prevhash I (idx2):
        Request prevhash I                                    STAGE_REQUEST_3_PREV_INPUT
    foreach prevhash O (idx2):
        Request prevhash O                                    STAGE_REQUEST_3_PREV_OUTPUT
        Add amount of prevhash O (which is amount of I)
    Request prevhash extra data (if applicable)               STAGE_REQUEST_3_PREV_EXTRADATA
    Calculate hash of streamed tx, compare to prevhash I

if (is_replacement)
    foreach orig I (idx1):
        if (orig idx1 is not legacy)
            Request input I, orig_hash, idx1                  STAGE_REQUEST_3_ORIG_NONLEGACY_INPUT
            Add I to OuterTransactionChecksum
            Verify signature of I if I is internal
        else
            foreach orig I (idx2):
                Request input I, orig_hash, idx2              STAGE_REQUEST_3_ORIG_INPUT
                Add I to InnerTransactionChecksum
                Add I to LegacyTransactionDigest
                if idx1 == idx2
                    Add I to OuterTransactionChecksum
                    Save signature for verification

            Ensure InnerTransactionChecksum matches orig_info.hash_inputs_check

            foreach orig O (idx2):
                Request output O, orig_hash, idx2             STAGE_REQUEST_3_ORIG_OUTPUT
                Add O to InnerTransactionChecksum
                Add O to LegacyTransactionDigest

            Ensure InnerTransactionChecksum matches orig_hash_outputs
            Verify signature of LegacyTransactionDigest

Ensure OuterTransactionChecksum matches orig_info.hash_inputs_check


Phase2: sign inputs, check that nothing changed
===============================================

if (Decred)
    Skip to STAGE_REQUEST_DECRED_WITNESS

foreach I (idx1):  // input to sign
    if (idx1 is not legacy)
        Request I                                             STAGE_REQUEST_NONLEGACY_INPUT
        Return serialized input chunk

    else
        foreach I (idx2):
            Request I                                         STAGE_REQUEST_4_INPUT
            If idx1 == idx2
                Fill scriptsig
                Remember key for signing
            Add I to StreamTransactionSign
            Add I to TransactionChecksum
        foreach O (idx2):
            Request O                                         STAGE_REQUEST_4_OUTPUT
            Add O to StreamTransactionSign
            Add O to TransactionChecksum

        Compare TransactionChecksum with checksum computed in Phase 1
        If different:
            Failure
        Sign StreamTransactionSign
        Return signed chunk

foreach O (idx1):
    Request O                                                 STAGE_REQUEST_5_OUTPUT
	Rewrite change address
	Return O


Phase3: sign segwit inputs, check that nothing changed
===============================================

foreach I (idx1):  // input to sign
    Request I                                                 STAGE_REQUEST_SEGWIT_WITNESS
	Check amount
	Sign  segwit prevhash, sequence, amount, outputs
	Return witness

Phase3: sign Decred inputs
==========================

foreach I (idx1): // input to sign                            STAGE_REQUEST_DECRED_WITNESS
    Request I
	Fill scriptSig
	Compute hash_witness

    Sign (hash_type || decred_hash_prefix || hash_witness)
    Return witness

clang-format on
*/

static bool add_amount(uint64_t *dest, uint64_t amount) {
  if (*dest + amount < *dest) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
    signing_abort();
    return false;
  }
  *dest += amount;
  return true;
}

static bool is_rbf_enabled(TxInfo *tx_info) {
  return tx_info->min_sequence <= MAX_BIP125_RBF_SEQUENCE;
}

static void set_external_input(uint32_t i) {
  external_inputs[i / 32] |= (1 << (i % 32));
}

static bool is_external_input(uint32_t i) {
  return external_inputs[i / 32] & (1 << (i % 32));
}

static void report_progress(bool force) {
  static uint32_t update_ctr = 0;
  if (!force && update_ctr < progress_update) {
    update_ctr++;
    return;
  }

  uint32_t progress = 0;
  if (progress_midpoint != 0) {
    if (progress_step < progress_midpoint) {
      // Checking previous transactions.
      progress =
          (500 * progress_step + 500 * progress_substep / progress_substeps) /
          progress_midpoint;
    } else {
      // Signing transaction after checking. No substeps.
      progress = 500 + 500 * (progress_step - progress_midpoint) /
                           (progress_steps - progress_midpoint);
    }
  } else {
    // Loading transaction or signing transaction without checking. No substeps.
    progress = 1000 * progress_step / progress_steps;
  }

  layoutProgress(progress_label, progress);
  update_ctr = 0;
}

#if DEBUG_LINK
static bool assert_progress_finished(void) {
  char line[54] = {0};
  if (progress_step != progress_steps) {
    snprintf(line, sizeof(line), "%s finished at %" PRIu32 "/%" PRIu32,
             progress_label, progress_step, progress_steps);
  } else if (progress_substep != 0) {
    snprintf(line, sizeof(line), "%s finished at substep %" PRIu32,
             progress_label, progress_substep);
  } else {
    return true;
  }
  fsm_sendFailure(FailureType_Failure_FirmwareError, line);
  signing_abort();
  return false;
}
#endif

static void init_loading_progress(void) {
  progress_label = _("Loading transaction");
  progress_step = 0;
  progress_substep = 0;
  progress_substeps = 1;  // no substeps in tx loading
  progress_midpoint = 0;  // no midpoint in tx loading
  progress_update = 10;   // update screen every 10 steps

  // Stage 1 and 2 - load inputs and outputs
  progress_steps = info.inputs_count + info.outputs_count;

  report_progress(true);
}

static void init_signing_progress(void) {
  progress_label = _("Signing transaction");
  progress_step = 0;
  progress_steps = 0;
  progress_update = 20;  // update screen every 20 steps

  // Verify previous transactions (STAGE_REQUEST_3_PREV_*).
  // We don't know how long it will take to fetch the previous transactions. If
  // they need to be checked, then we will reserve 50 % of the progress for
  // this. Once we fetch a prev_tx's metadata, we subdivide the reserved space
  // into substeps which represent the progress of fetching one prev_tx input or
  // output.
  if (!taproot_only && !(coin->overwintered && info.version == 5)) {
    progress_steps += info.inputs_count;
    progress_midpoint = progress_steps;
  }

  uint32_t external_count = 0;
  for (size_t i = 0; i < info.inputs_count; ++i) {
    external_count += is_external_input(i);
  }

  // Process inputs.
  if (!(coin->force_bip143 || coin->overwintered || coin->decred)) {
    // Sign and optionally serialize legacy inputs (STAGE_REQUEST_4_*).
    progress_steps += (info.inputs_count - info.segwit_count - external_count) *
                      (info.inputs_count + info.outputs_count);

    if (serialize) {
      // Serialize non-legacy inputs (STAGE_REQUEST_NONLEGACY_INPUT).
      progress_steps += info.segwit_count + external_count;
    }

    if (is_replacement) {
      // Verify original input signatures (STAGE_REQUEST_3_ORIG_*).
      progress_steps +=
          (orig_info.inputs_count - orig_info.segwit_count - external_count) *
          (orig_info.inputs_count + orig_info.outputs_count);
      progress_steps += orig_info.segwit_count;
    }
  } else {
    // Sign and optionally serialize each input (STAGE_REQUEST_NONLEGACY_INPUT,
    // or in case of Decred STAGE_REQUEST_DECRED_WITNESS).
    progress_steps += info.inputs_count;
    if (is_replacement) {
      // Verify each original input (STAGE_REQUEST_3_ORIG_NONLEGACY_INPUT).
      progress_steps += orig_info.inputs_count;
    }
  }

  if (to.is_segwit) {
    if (serialize) {
      // Serialize witnesses for all inputs (STAGE_REQUEST_SEGWIT_WITNESS).
      progress_steps += info.inputs_count;
    } else {
      // Process witnesses for all internal inputs
      // (STAGE_REQUEST_SEGWIT_WITNESS).
      progress_steps += info.inputs_count - external_count;
    }
  }

  // Serialize outputs (STAGE_REQUEST_5_OUTPUT).
  if (serialize && !coin->decred) {
    progress_steps += info.outputs_count;
  }

  report_progress(true);
}

void send_req_1_input(void) {
  signing_stage = STAGE_REQUEST_1_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_1_orig_meta(void) {
  signing_stage = STAGE_REQUEST_1_ORIG_META;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXMETA;
  resp.has_details = true;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_1_orig_input(void) {
  signing_stage = STAGE_REQUEST_1_ORIG_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXORIGINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_output(void) {
  signing_stage = STAGE_REQUEST_2_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_orig_output(void) {
  signing_stage = STAGE_REQUEST_2_ORIG_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXORIGOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

#if !BITCOIN_ONLY
void send_req_2_orig_extradata(uint32_t chunk_offset, uint32_t chunk_len) {
  signing_stage = STAGE_REQUEST_2_ORIG_EXTRADATA;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXEXTRADATA;
  resp.has_details = true;
  resp.details.has_extra_data_offset = true;
  resp.details.extra_data_offset = chunk_offset;
  resp.details.has_extra_data_len = true;
  resp.details.extra_data_len = chunk_len;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}
#endif

void send_req_3_input(void) {
  signing_stage = STAGE_REQUEST_3_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_prev_meta(void) {
  signing_stage = STAGE_REQUEST_3_PREV_META;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXMETA;
  resp.has_details = true;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = input.prev_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes,
         input.prev_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_prev_input(void) {
  signing_stage = STAGE_REQUEST_3_PREV_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = input.prev_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes,
         resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_prev_output(void) {
  signing_stage = STAGE_REQUEST_3_PREV_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = input.prev_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes,
         resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

#if !BITCOIN_ONLY
void send_req_3_prev_extradata(uint32_t chunk_offset, uint32_t chunk_len) {
  signing_stage = STAGE_REQUEST_3_PREV_EXTRADATA;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXEXTRADATA;
  resp.has_details = true;
  resp.details.has_extra_data_offset = true;
  resp.details.extra_data_offset = chunk_offset;
  resp.details.has_extra_data_len = true;
  resp.details.extra_data_len = chunk_len;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = input.prev_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes,
         resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}
#endif

void send_req_3_orig_nonlegacy_input(void) {
  signing_stage = STAGE_REQUEST_3_ORIG_NONLEGACY_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXORIGINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_orig_input(void) {
  signing_stage = STAGE_REQUEST_3_ORIG_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXORIGINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_3_orig_output(void) {
  signing_stage = STAGE_REQUEST_3_ORIG_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXORIGOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = sizeof(orig_hash);
  memcpy(resp.details.tx_hash.bytes, orig_hash, resp.details.tx_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_4_input(void) {
  signing_stage = STAGE_REQUEST_4_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_4_output(void) {
  signing_stage = STAGE_REQUEST_4_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx2;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_nonlegacy_input(void) {
  signing_stage = STAGE_REQUEST_NONLEGACY_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_segwit_witness(void) {
  signing_stage = STAGE_REQUEST_SEGWIT_WITNESS;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

#if !BITCOIN_ONLY

void send_req_decred_witness(void) {
  signing_stage = STAGE_REQUEST_DECRED_WITNESS;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

#endif

void send_req_5_output(void) {
  signing_stage = STAGE_REQUEST_5_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_finished(void) {
#if DEBUG_LINK
  if (!assert_progress_finished()) {
    return;
  }
#endif
  resp.has_request_type = true;
  resp.request_type = RequestType_TXFINISHED;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void phase1_request_next_input(void) {
  if (idx1 < info.inputs_count - 1) {
    idx1++;
    send_req_1_input();
  } else {
    idx1 = 0;

    if (is_replacement) {
      if (idx2 != orig_info.inputs_count) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Removal of original inputs is not supported."));
        signing_abort();
        return;
      }

      char *description = NULL;
      if (!is_rbf_enabled(&info) && is_rbf_enabled(&orig_info)) {
        description = _("Finalize TXID:");
      } else {
        description = _("Update TXID:");
      }

      // Confirm original TXID.
      layoutConfirmReplacement(description, orig_hash);
      if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        signing_abort();
        return;
      }

      idx2 = 0;
    }

    if (to.is_segwit) {
      tx_base_weight += TXSIZE_SEGWIT_OVERHEAD;
      tx_weight += TXSIZE_SEGWIT_OVERHEAD + to.inputs_len;
      our_weight += TXSIZE_SEGWIT_OVERHEAD + our_inputs_len;
    }

    send_req_2_output();
  }
}

void phase1_request_orig_input(void) {
  if (!is_replacement) {
    // Get original tx metadata before getting first original input.
    memcpy(orig_hash, input.orig_hash.bytes, sizeof(orig_hash));
    is_replacement = true;
    idx2 = 0;
    send_req_1_orig_meta();
  } else {
    if (memcmp(input.orig_hash.bytes, orig_hash, sizeof(orig_hash)) != 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Only one original transaction is allowed."));
      signing_abort();
      return;
    }

    if (input.orig_index >= orig_info.inputs_count) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Not enough inputs in original transaction."));
      signing_abort();
      return;
    }

    if (idx2 != input.orig_index) {
      fsm_sendFailure(
          FailureType_Failure_DataError,
          _("Rearranging or removal of original inputs is not supported."));
      signing_abort();
      return;
    }

    send_req_1_orig_input();
  }
}

void phase2_request_next_witness(bool first) {
  if (first) {
    idx1 = 0;
    if (!to.is_segwit) {
      send_req_finished();
      signing_abort();
      return;
    }
  } else if (idx1 < info.inputs_count - 1) {
    idx1++;
  } else {
    send_req_finished();
    signing_abort();
    return;
  }

  if (!serialize) {
    // Skip external inputs when serialization is disabled.
    while (is_external_input(idx1)) {
      if (idx1 >= info.inputs_count - 1) {
        send_req_finished();
        signing_abort();
        return;
      }
      idx1++;
    }
  }

  send_req_segwit_witness();
  return;
}

void phase2_request_next_output(bool first) {
  if (first) {
    if (serialize) {
      idx1 = 0;
      send_req_5_output();
      return;
    }
  } else if (idx1 < info.outputs_count - 1) {
    idx1++;
    send_req_5_output();
    return;
  }

  // Output serialization is finished. Generate witnesses.
  phase2_request_next_witness(true);
}

void phase2_request_next_input(bool first) {
  if (first) {
    idx1 = 0;
  } else if (idx1 < info.inputs_count - 1) {
    idx1++;
  } else {
    // Input processing is finished. Serialize outputs.
    phase2_request_next_output(true);
    return;
  }

  if (serialize || coin->force_bip143 || coin->overwintered) {
    // We are processing all inputs.
    if (idx1 == info.next_legacy_input) {
      idx2 = 0;
      send_req_4_input();
    } else {
      send_req_nonlegacy_input();
    }
  } else {
    // We are only signing legacy inputs.
    if (info.next_legacy_input == 0xffffffff || idx1 > info.next_legacy_input) {
      // There are no legacy inputs or no more legacy inputs, so serialize
      // outputs.
      phase2_request_next_output(true);
    } else {
      // Sign next legacy input.
      idx1 = info.next_legacy_input;
      idx2 = 0;
      send_req_4_input();
    }
  }
}

void phase2_request_orig_input(void) {
  if (idx1 < orig_info.inputs_count) {
    if (idx1 == 0) {
      // Reset outer transaction check.
      hasher_Reset(&hasher_check);
    }

    if (idx1 == orig_info.next_legacy_input) {
      idx2 = 0;
      send_req_3_orig_input();
    } else {
      send_req_3_orig_nonlegacy_input();
    }
  } else {
    // Ensure that the original transaction inputs haven't changed for the outer
    // transaction check.
    uint8_t hash[32];
    hasher_Final(&hasher_check, hash);
    if (memcmp(hash, orig_info.hash_inputs_check, 32) != 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Transaction has changed during signing"));
      signing_abort();
      return;
    }

    phase2_request_next_input(true);
  }
}

static bool extract_input_multisig_fp(TxInfo *tx_info,
                                      const TxInputType *txinput) {
  if (txinput->has_multisig && !tx_info->multisig_fp_mismatch) {
    uint8_t h[32] = {0};
    if (cryptoMultisigFingerprint(&txinput->multisig, h) == 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Error computing multisig fingerprint"));
      signing_abort();
      return false;
    }
    if (tx_info->multisig_fp_set) {
      if (memcmp(tx_info->multisig_fp, h, 32) != 0) {
        tx_info->multisig_fp_mismatch = true;
      }
    } else {
      memcpy(tx_info->multisig_fp, h, 32);
      tx_info->multisig_fp_set = true;
    }
  } else {  // single signature
    tx_info->multisig_fp_mismatch = true;
  }

  return true;
}

static void extract_is_multisig(TxInfo *tx_info, const TxInputType *txinput) {
  switch (tx_info->is_multisig_state) {
    case MatchState_MISMATCH:
      return;
    case MatchState_UNDEFINED:
      tx_info->is_multisig_state = MatchState_MATCH;
      tx_info->is_multisig = txinput->has_multisig;
      return;
    case MatchState_MATCH:
      if (txinput->has_multisig != tx_info->is_multisig) {
        tx_info->is_multisig_state = MatchState_MISMATCH;
      }
      return;
  }
}

bool check_change_multisig_fp(const TxInfo *tx_info,
                              const TxOutputType *txoutput) {
  uint8_t h[32] = {0};
  return tx_info->multisig_fp_set && !tx_info->multisig_fp_mismatch &&
         cryptoMultisigFingerprint(&(txoutput->multisig), h) &&
         memcmp(tx_info->multisig_fp, h, 32) == 0;
}

bool check_change_is_multisig(const TxInfo *tx_info,
                              const TxOutputType *txoutput) {
  return tx_info->is_multisig_state == MatchState_MATCH &&
         tx_info->is_multisig == txoutput->has_multisig;
}

static InputScriptType simple_script_type(InputScriptType script_type) {
  // SPENDMULTISIG is used only for non-SegWit and is effectively the same as
  // SPENDADDRESS. For SegWit inputs and outputs multisig is indicated by the
  // presence of the multisig structure. for both SegWit and non-SegWit we can
  // rely on multisig_fp to check the multisig structure.
  if (script_type == InputScriptType_SPENDMULTISIG) {
    script_type = InputScriptType_SPENDADDRESS;
  }

  return script_type;
}

void extract_input_script_type(TxInfo *tx_info, const TxInputType *tinput) {
  switch (tx_info->in_script_type_state) {
    case MatchState_UNDEFINED:
      // initialize in_script_type on first input seen
      tx_info->in_script_type = simple_script_type(tinput->script_type);
      tx_info->in_script_type_state = MatchState_MATCH;
      break;
    case MatchState_MATCH:
      // check that all input script types are the same
      if (tx_info->in_script_type != simple_script_type(tinput->script_type)) {
        tx_info->in_script_type_state = MatchState_MISMATCH;
      }
      break;
    default:
      break;
  }
}

bool check_change_script_type(const TxInfo *tx_info,
                              const TxOutputType *toutput) {
  InputScriptType input_script_type = 0;
  if (!change_output_to_input_script_type(toutput->script_type,
                                          &input_script_type)) {
    return false;
  }
  return tx_info->in_script_type_state == MatchState_MATCH &&
         tx_info->in_script_type == simple_script_type(input_script_type);
}

void extract_input_bip32_path(TxInfo *tx_info, const TxInputType *tinput) {
  if (tx_info->in_address_n_count == BIP32_NOCHANGEALLOWED) {
    return;
  }
  size_t count = tinput->address_n_count;
  if (count < BIP32_WALLET_DEPTH) {
    // no change address allowed
    tx_info->in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
  if (tx_info->in_address_n_count == 0) {
    // initialize in_address_n on first input seen
    tx_info->in_address_n_count = count;
    // store the bip32 path up to the account
    memcpy(tx_info->in_address_n, tinput->address_n,
           (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t));
    return;
  }
  // check that all addresses use a path of same length
  if (tx_info->in_address_n_count != count) {
    tx_info->in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
  // check that the bip32 path up to the account matches
  if (memcmp(tx_info->in_address_n, tinput->address_n,
             (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t)) != 0) {
    // mismatch -> no change address allowed
    tx_info->in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
}

bool check_change_bip32_path(const TxInfo *tx_info,
                             const TxOutputType *toutput) {
  size_t count = toutput->address_n_count;

  // Check that the change path has the same bip32 path length,
  // the same path up to the account, and that the wallet components
  // (chain id and address) are as expected.
  // Note: count >= BIP32_WALLET_DEPTH and count == in_address_n_count
  // imply that in_address_n_count != BIP32_NOCHANGEALLOWED
  return (count >= BIP32_WALLET_DEPTH && count == tx_info->in_address_n_count &&
          0 == memcmp(tx_info->in_address_n, toutput->address_n,
                      (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t)) &&
          toutput->address_n[count - 2] <= PATH_MAX_CHANGE &&
          toutput->address_n[count - 1] <= PATH_MAX_ADDRESS_INDEX);
}

static bool fill_input_script_sig(TxInputType *tinput) {
  if (hdnode_fill_public_key(&node) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive public key."));
    signing_abort();
    return false;
  }

  if (tinput->has_multisig) {
    tinput->script_sig.size = compile_script_multisig(coin, &(tinput->multisig),
                                                      tinput->script_sig.bytes);
  } else {  // SPENDADDRESS
    uint8_t hash[20] = {0};
    ecdsa_get_pubkeyhash(node.public_key, coin->curve->hasher_pubkey, hash);
    tinput->script_sig.size =
        compile_script_sig(coin->address_type, hash, tinput->script_sig.bytes);
  }

  if (tinput->script_sig.size == 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to compile input."));
    signing_abort();
    return false;
  }

  return true;
}

static bool fill_input_script_pubkey(TxInputType *in) {
  if (!get_script_pubkey(coin, &node, in->has_multisig, &in->multisig,
                         in->script_type, in->script_pubkey.bytes,
                         &in->script_pubkey.size)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive scriptPubKey"));
    signing_abort();
    return false;
  }
  in->has_script_pubkey = true;
  return true;
}

static bool validate_path(InputScriptType script_type,
                          pb_size_t address_n_count, const uint32_t *address_n,
                          bool has_multisig) {
  if (is_coinjoin == sectrue) {
    // Check whether the authorization matches the parameters of the input.
    if (address_n_count !=
            coinjoin_authorization.address_n_count + BIP32_WALLET_DEPTH ||
        memcmp(address_n, coinjoin_authorization.address_n,
               sizeof(uint32_t) * coinjoin_authorization.address_n_count) !=
            0 ||
        script_type != coinjoin_authorization.script_type) {
      fsm_sendFailure(FailureType_Failure_ProcessError, _("Unauthorized path"));
      signing_abort();
      return false;
    }
  } else {
    // Sanity check not critical for security. The main reason for this is that
    // we are not comfortable with using the same private key in multiple
    // signature schemes (ECDSA and Schnorr) and we want to be sure that the
    // user went through a warning screen before we sign the input.
    if (!coin_path_check(coin, script_type, address_n_count, address_n,
                         has_multisig, unlocked_schema, true)) {
      if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict &&
          !coin_path_check(coin, script_type, address_n_count, address_n,
                           has_multisig, unlocked_schema, false)) {
        fsm_sendFailure(FailureType_Failure_DataError, _("Forbidden key path"));
        signing_abort();
        return false;
      }

      if (!foreign_address_confirmed) {
        if (signing_stage < STAGE_REQUEST_3_INPUT) {
          if (!fsm_layoutPathWarning()) {
            signing_abort();
            return false;
          }
          foreign_address_confirmed = true;
        } else {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Transaction has changed during signing"));
          signing_abort();
          return false;
        }
      }
    }
  }
  return true;
}

static bool input_validate_path(const TxInputType *txi) {
  return validate_path(txi->script_type, txi->address_n_count, txi->address_n,
                       txi->has_multisig);
}

static bool derive_node(InputScriptType script_type, pb_size_t address_n_count,
                        const uint32_t *address_n, bool has_multisig) {
  if (!coin_path_check(coin, script_type, address_n_count, address_n,
                       has_multisig, unlocked_schema, false) &&
      config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Forbidden key path"));
    signing_abort();
    return false;
  }

  memcpy(&node, &root, sizeof(HDNode));
  if (hdnode_private_ckd_cached(&node, address_n, address_n_count, NULL) == 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive private key."));
    signing_abort();
    return false;
  }

  return true;
}

static bool input_derive_node(const TxInputType *txi) {
  return derive_node(txi->script_type, txi->address_n_count, txi->address_n,
                     txi->has_multisig);
}

static bool tx_info_init(TxInfo *tx_info, uint32_t inputs_count,
                         uint32_t outputs_count, uint32_t version,
                         uint32_t lock_time, bool has_expiry, uint32_t expiry,
                         bool has_branch_id, uint32_t branch_id,
                         bool has_version_group_id, uint32_t version_group_id,
                         bool has_timestamp, uint32_t timestamp) {
  if (!coin->overwintered) {
    if (has_version_group_id) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Version group ID not enabled on this coin."));
      signing_abort();
      return false;
    }
    if (has_branch_id) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Branch ID not enabled on this coin."));
      signing_abort();
      return false;
    }
  }

  if (!coin->timestamp && has_timestamp) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Timestamp not enabled on this coin."));
    signing_abort();
    return false;
  }

  if (!coin->decred && !coin->overwintered && has_expiry) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Expiry not enabled on this coin."));
    signing_abort();
    return false;
  }

  if (inputs_count + outputs_count < inputs_count) {
    // Avoid division by zero in progress computations.
    fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
    signing_abort();
    return false;
  }

  tx_info->inputs_count = inputs_count;
  tx_info->outputs_count = outputs_count;
  tx_info->segwit_count = 0;
  tx_info->next_legacy_input = 0xffffffff;
  tx_info->min_sequence = SEQUENCE_FINAL;
  tx_info->multisig_fp_set = false;
  tx_info->multisig_fp_mismatch = false;
  tx_info->is_multisig_state = MatchState_UNDEFINED;
  tx_info->in_address_n_count = 0;
  tx_info->in_script_type = 0;
  tx_info->in_script_type_state = MatchState_UNDEFINED;
  tx_info->version = version;
  tx_info->lock_time = lock_time;

#if BITCOIN_ONLY
  (void)expiry;
  (void)version_group_id;
  (void)timestamp;
  (void)branch_id;
  tx_info->expiry = 0;
  tx_info->version_group_id = 0;
  tx_info->timestamp = 0;
#else
  tx_info->expiry = (coin->decred || coin->overwintered) ? expiry : 0;

  if (coin->timestamp) {
    if (!has_timestamp || !timestamp) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Timestamp must be set."));
      signing_abort();
      return false;
    }
    tx_info->timestamp = timestamp;
  } else {
    tx_info->timestamp = 0;
  }

  if (coin->overwintered) {
    if (!has_version_group_id) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Version group ID must be set."));
      signing_abort();
      return false;
    }

    if (!has_branch_id) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Branch ID must be set."));
      signing_abort();
      return false;
    }

    if (tx_info->version != 4 && tx_info->version != 5) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Unsupported transaction version."));
      signing_abort();
      return false;
    }

    tx_info->version_group_id = version_group_id;
    tx_info->branch_id = branch_id;
  } else {
    tx_info->version_group_id = 0;
    tx_info->branch_id = 0;
  }
#endif

  hasher_Init(&tx_info->hasher_check, HASHER_SHA2);

#if !BITCOIN_ONLY
  if (coin->overwintered) {
    if (tx_info->version == 5) {
      // ZIP-244
      hasher_InitParam(&tx_info->hasher_prevouts, HASHER_BLAKE2B_PERSONAL,
                       "ZTxIdPrevoutHash", 16);
      hasher_InitParam(&tx_info->hasher_amounts, HASHER_BLAKE2B_PERSONAL,
                       "ZTxTrAmountsHash", 16);
      hasher_InitParam(&tx_info->hasher_scriptpubkeys, HASHER_BLAKE2B_PERSONAL,
                       "ZTxTrScriptsHash", 16);
      hasher_InitParam(&tx_info->hasher_sequences, HASHER_BLAKE2B_PERSONAL,
                       "ZTxIdSequencHash", 16);
      hasher_InitParam(&tx_info->hasher_outputs, HASHER_BLAKE2B_PERSONAL,
                       "ZTxIdOutputsHash", 16);
    } else {
      // ZIP-243
      hasher_InitParam(&tx_info->hasher_prevouts, HASHER_BLAKE2B_PERSONAL,
                       "ZcashPrevoutHash", 16);
      hasher_InitParam(&tx_info->hasher_sequences, HASHER_BLAKE2B_PERSONAL,
                       "ZcashSequencHash", 16);
      hasher_InitParam(&tx_info->hasher_outputs, HASHER_BLAKE2B_PERSONAL,
                       "ZcashOutputsHash", 16);
    }
  } else
#endif
  {
    // BIP-143/BIP-341
    hasher_Init(&tx_info->hasher_prevouts, HASHER_SHA2);
    hasher_Init(&tx_info->hasher_amounts, HASHER_SHA2);
    hasher_Init(&tx_info->hasher_scriptpubkeys, HASHER_SHA2);
    hasher_Init(&tx_info->hasher_sequences, HASHER_SHA2);
    hasher_Init(&tx_info->hasher_outputs, HASHER_SHA2);
  }

  return true;
}

static bool init_coinjoin(const SignTx *msg,
                          const AuthorizeCoinJoin *authorization) {
  if (!msg->has_coinjoin_request) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Missing coinjoin request."));
    signing_abort();
    return false;
  }

  if (strcmp(coin->coin_name, authorization->coin_name) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Unauthorized operation."));
  }

  memcpy(&coinjoin_authorization, authorization,
         sizeof(coinjoin_authorization));
  memcpy(&coinjoin_request, &msg->coinjoin_request, sizeof(coinjoin_request));

  return true;
}

void signing_init(const SignTx *msg, const CoinInfo *_coin, const HDNode *_root,
                  const AuthorizeCoinJoin *authorization, PathSchema unlock) {
  coin = _coin;
  amount_unit = msg->has_amount_unit ? msg->amount_unit : AmountUnit_BITCOIN;
  serialize = msg->has_serialize ? msg->serialize : true;
  memcpy(&root, _root, sizeof(HDNode));

  if (msg->inputs_count > MAX_INPUTS_COUNT) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Too many inputs."));
    signing_abort();
    return;
  }

  if (!tx_info_init(&info, msg->inputs_count, msg->outputs_count, msg->version,
                    msg->lock_time, msg->has_expiry, msg->expiry,
                    msg->has_branch_id, msg->branch_id,
                    msg->has_version_group_id, msg->version_group_id,
                    msg->has_timestamp, msg->timestamp)) {
    return;
  }

  uint32_t size = TXSIZE_HEADER + TXSIZE_FOOTER +
                  ser_length_size(info.inputs_count) +
                  ser_length_size(info.outputs_count);
#if !BITCOIN_ONLY
  if (coin->decred) {
    size += 4;                                   // Decred expiry
    size += ser_length_size(info.inputs_count);  // Witness inputs count
  }
#endif

  tx_base_weight = 4 * size;
  tx_weight = tx_base_weight;
  our_weight = tx_base_weight;
  our_inputs_len = 0;

  foreign_address_confirmed = false;
  taproot_only = true;
  has_unverified_external_input = false;
  signatures = 0;
  idx1 = 0;
  total_in = 0;
  external_in = 0;
  total_out = 0;
  change_out = 0;
  change_count = 0;
  orig_total_in = 0;
  orig_external_in = 0;
  orig_total_out = 0;
  orig_change_out = 0;
  coinjoin_coordination_fee_base = 0;
  memzero(external_inputs, sizeof(external_inputs));
  memzero(&input, sizeof(TxInputType));
  memzero(&output, sizeof(TxOutputType));
  memzero(&resp, sizeof(TxRequest));
  memzero(&coinjoin_authorization, sizeof(coinjoin_authorization));
  memzero(&coinjoin_request, sizeof(coinjoin_request));
  is_replacement = false;
  unlocked_schema = unlock;
  signing = true;
  is_coinjoin = (authorization != NULL) ? sectrue : secfalse;
  if (is_coinjoin == sectrue) {
    if (!init_coinjoin(msg, authorization)) {
      return;
    }
  }

  uint32_t branch_id = 0;
#if !BITCOIN_ONLY
  branch_id = info.branch_id;
#endif

  tx_init(&to, info.inputs_count, info.outputs_count, info.version,
          info.lock_time, info.expiry, branch_id, 0, coin->curve->hasher_sign,
          coin->overwintered, info.version_group_id, info.timestamp);

#if !BITCOIN_ONLY
  if (coin->decred) {
    to.version |= (DECRED_SERIALIZE_FULL << 16);
    to.is_decred = true;

    tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
            info.lock_time, info.expiry, branch_id, 0, coin->curve->hasher_sign,
            coin->overwintered, info.version_group_id, info.timestamp);
    ti.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
    ti.is_decred = true;
  }
#endif

  hasher_Init(&hasher_check, HASHER_SHA2);

  init_loading_progress();

  send_req_1_input();
}

#define MIN(a, b) (((a) < (b)) ? (a) : (b))

static bool signing_validate_input(const TxInputType *txinput) {
  if (txinput->prev_hash.size != 32) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Provided prev_hash is invalid."));
    signing_abort();
    return false;
  }

  if (txinput->has_multisig &&
      !is_multisig_input_script_type(txinput->script_type)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Multisig field provided but not expected."));
    signing_abort();
    return false;
  }

  if (!txinput->has_multisig &&
      txinput->script_type == InputScriptType_SPENDMULTISIG) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Multisig details required."));
    signing_abort();
    return false;
  }

  if (is_internal_input_script_type(txinput->script_type)) {
    if (txinput->address_n_count == 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing address_n field."));
      signing_abort();
      return false;
    }

    if (txinput->has_script_pubkey) {
      // scriptPubKey should only be provided for external inputs
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Input's script_pubkey provided but not expected."));
      signing_abort();
      return false;
    }

    if (txinput->has_ownership_proof) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Ownership proof provided but not expected."));
      signing_abort();
      return false;
    }
  } else if (txinput->script_type == InputScriptType_EXTERNAL) {
    if (txinput->address_n_count != 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Input's address_n provided but not expected."));
      signing_abort();
      return false;
    }

    if (!txinput->has_script_pubkey) {
      // scriptPubKey should be provided for external inputs
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing script_pubkey field."));
      signing_abort();
      return false;
    }
  } else {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Unsupported script type."));
    signing_abort();
    return false;
  }

  if (!coin->decred && txinput->has_decred_tree) {
    fsm_sendFailure(
        FailureType_Failure_DataError,
        _("Decred details provided but Decred coin not specified."));
    signing_abort();
    return false;
  }

  if (is_segwit_input_script_type(txinput->script_type)) {
    if (!coin->has_segwit) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Segwit not enabled on this coin"));
      signing_abort();
      return false;
    }
  }

  if (txinput->script_type == InputScriptType_SPENDTAPROOT &&
      !coin->has_taproot) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Taproot not enabled on this coin."));
    signing_abort();
    return false;
  }

  if (txinput->has_commitment_data && !txinput->has_ownership_proof) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("commitment_data field provided but not expected."));
    signing_abort();
    return false;
  }

  if (txinput->has_orig_hash) {
    if (!txinput->has_orig_index) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing orig_index field."));
      signing_abort();
      return false;
    }

    if (txinput->orig_hash.size != 32) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Provided orig_hash is invalid."));
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool signing_validate_prev_input(const TxInputType *txinput) {
  if (txinput->prev_hash.size != 32) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Provided prev_hash is invalid."));
    signing_abort();
    return false;
  }

  if (!coin->decred && txinput->has_decred_tree) {
    fsm_sendFailure(
        FailureType_Failure_DataError,
        _("Decred details provided but Decred coin not specified."));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_validate_output(TxOutputType *txoutput) {
  if (txoutput->has_multisig &&
      !is_multisig_output_script_type(txoutput->script_type)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Multisig field provided but not expected."));
    signing_abort();
    return false;
  }

  if (txoutput->address_n_count > 0 &&
      !is_change_output_script_type(txoutput->script_type)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Output's address_n provided but not expected."));
    signing_abort();
    return false;
  }

  if (txoutput->script_type == OutputScriptType_PAYTOOPRETURN) {
    if (txoutput->has_address || (txoutput->address_n_count > 0) ||
        txoutput->has_multisig) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("OP_RETURN output with address or multisig"));
      signing_abort();
      return false;
    }
    if (txoutput->amount != 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("OP_RETURN output with non-zero amount"));
      signing_abort();
      return false;
    }
  } else {
    if (txoutput->has_op_return_data) {
      fsm_sendFailure(
          FailureType_Failure_DataError,
          _("OP RETURN data provided but not OP RETURN script type."));
      signing_abort();
      return false;
    }
    if (txoutput->has_address && txoutput->address_n_count > 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Both address and address_n provided."));
      signing_abort();
      return false;
    } else if (!txoutput->has_address && txoutput->address_n_count == 0) {
      fsm_sendFailure(FailureType_Failure_DataError, _("Missing address"));
      signing_abort();
      return false;
    }
  }

  if (is_segwit_output_script_type(txoutput->script_type)) {
    if (!coin->has_segwit) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Segwit not enabled on this coin"));
      signing_abort();
      return false;
    }
  }

  if (txoutput->script_type == OutputScriptType_PAYTOTAPROOT &&
      !coin->has_taproot) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Taproot not enabled on this coin."));
    signing_abort();
    return false;
  }

  if (txoutput->has_orig_hash) {
    if (!txoutput->has_orig_index) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing orig_index field."));
      signing_abort();
      return false;
    }

    if (txoutput->orig_hash.size != 32) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Encountered invalid orig_hash"));
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool signing_validate_bin_output(TxOutputBinType *tx_bin_output) {
#if !BITCOIN_ONLY
  if (!coin->decred && tx_bin_output->has_decred_script_version) {
    fsm_sendFailure(
        FailureType_Failure_DataError,
        _("Decred details provided but Decred coin not specified."));
    signing_abort();
    return false;
  }
#else
  (void)tx_bin_output;
#endif
  return true;
}

static bool tx_info_add_input(TxInfo *tx_info, const TxInputType *txinput) {
  if (txinput->script_type != InputScriptType_EXTERNAL) {
    // Compute multisig fingerprint for change-output detection. In order for an
    // output to be considered a change-output, it must have the same
    // fingerprint as all inputs.
    if (!extract_input_multisig_fp(tx_info, txinput)) {
      return false;
    }

    // Remember whether all inputs are singlesig or all inputs are multisig.
    // Change-outputs must be of the same type.
    extract_is_multisig(tx_info, txinput);

    // Remember the input's script type. Change-outputs must use the same script
    // type as all inputs.
    extract_input_script_type(tx_info, txinput);

    // Remember the input's BIP-32 path. Change-outputs must use the same path
    // as all inputs.
    extract_input_bip32_path(tx_info, txinput);
  }

  if (is_segwit_input_script_type(txinput->script_type)) {
    tx_info->segwit_count++;
  }

  // Remember the minimum nSequence value.
  if (txinput->sequence < tx_info->min_sequence) {
    tx_info->min_sequence = txinput->sequence;
  }

  // Add input to BIP-143 and BIP-341 running sub-hashes.
  tx_prevout_hash(&tx_info->hasher_prevouts, txinput);
  tx_amount_hash(&tx_info->hasher_amounts, txinput);
  tx_script_hash(&tx_info->hasher_scriptpubkeys, txinput->script_pubkey.size,
                 txinput->script_pubkey.bytes);
  tx_sequence_hash(&tx_info->hasher_sequences, txinput);

  return true;
}

static bool tx_info_check_input(TxInfo *tx_info, TxInputType *tinput) {
  bool result = true;

  if (!tx_info->multisig_fp_mismatch) {
    // check that this is still multisig
    uint8_t h[32] = {0};
    if (!tinput->has_multisig ||
        cryptoMultisigFingerprint(&(tinput->multisig), h) == 0 ||
        memcmp(tx_info->multisig_fp, h, 32) != 0) {
      result = false;
    }
  }

  if (tx_info->in_script_type_state == MatchState_MATCH) {
    // check that input script type didn't change
    if (simple_script_type(tinput->script_type) != tx_info->in_script_type) {
      result = false;
    }
  }

  if (tx_info->in_address_n_count != BIP32_NOCHANGEALLOWED) {
    // check that input address didn't change
    size_t count = tinput->address_n_count;
    if (count < 2 || count != tx_info->in_address_n_count ||
        0 != memcmp(tx_info->in_address_n, tinput->address_n,
                    (count - 2) * sizeof(uint32_t))) {
      result = false;
    }
  }

  if (result == false) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Transaction has changed during signing"));
    signing_abort();
  }
  return result;
}

static bool tx_info_add_output(TxInfo *tx_info,
                               const TxOutputBinType *tx_bin_output) {
  // Add output to BIP-143/BIP-341 hashOutputs.
  tx_output_hash(&tx_info->hasher_outputs, tx_bin_output, coin->decred);
  return true;
}

#if !BITCOIN_ONLY
static void txinfo_fill_zip244_header_hash(TxInfo *tx_info) {
  // `T.1: header_digest` field.
  // https://zips.z.cash/zip-0244#t-1-header-digest
  Hasher hasher = {0};
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, "ZTxIdHeadersHash", 16);

  // T.1a: version (4-byte little-endian version identifier including
  // overwintered flag)
  uint32_t ver = tx_info->version | TX_OVERWINTERED;
  hasher_Update(&hasher, (const uint8_t *)&ver, 4);
  // T.1b: version_group_id (4-byte little-endian version group identifier)
  hasher_Update(&hasher, (const uint8_t *)&tx_info->version_group_id, 4);
  // T.1c: consensus_branch_id (4-byte little-endian consensus branch id)
  hasher_Update(&hasher, (const uint8_t *)&tx_info->branch_id, 4);
  // T.1d: lock_time (4-byte little-endian nLockTime value)
  hasher_Update(&hasher, (const uint8_t *)&tx_info->lock_time, 4);
  // T.1e: expiry_height (4-byte little-endian block height)
  hasher_Update(&hasher, (const uint8_t *)&tx_info->expiry, 4);
  hasher_Final(&hasher, tx_info->hash_header);
}
#endif

static void tx_info_finish(TxInfo *tx_info) {
  hasher_Final(&tx_info->hasher_check, tx_info->hash_inputs_check);
  hasher_Final(&tx_info->hasher_prevouts, tx_info->hash_prevouts);
  hasher_Final(&tx_info->hasher_amounts, tx_info->hash_amounts);
  hasher_Final(&tx_info->hasher_scriptpubkeys, tx_info->hash_scriptpubkeys);
  hasher_Final(&tx_info->hasher_sequences, tx_info->hash_sequences);
  hasher_Final(&tx_info->hasher_outputs, tx_info->hash_outputs);

  if (coin->curve->hasher_sign == HASHER_SHA2D) {
    hasher_Raw(HASHER_SHA2, tx_info->hash_prevouts,
               sizeof(tx_info->hash_prevouts), tx_info->hash_prevouts143);
    hasher_Raw(HASHER_SHA2, tx_info->hash_sequences,
               sizeof(tx_info->hash_sequences), tx_info->hash_sequence143);
    hasher_Raw(HASHER_SHA2, tx_info->hash_outputs,
               sizeof(tx_info->hash_outputs), tx_info->hash_outputs143);
  } else {
    memcpy(tx_info->hash_prevouts143, tx_info->hash_prevouts,
           sizeof(tx_info->hash_prevouts));
    memcpy(tx_info->hash_sequence143, tx_info->hash_sequences,
           sizeof(tx_info->hash_sequences));
    memcpy(tx_info->hash_outputs143, tx_info->hash_outputs,
           sizeof(tx_info->hash_outputs));
  }

#if !BITCOIN_ONLY
  if (coin->overwintered && tx_info->version == 5) {
    txinfo_fill_zip244_header_hash(tx_info);
  }
#endif
}

static bool tx_info_check_inputs_hash(TxInfo *tx_info) {
  uint8_t hash[32];
  hasher_Final(&tx_info->hasher_check, hash);
  if (memcmp(hash, tx_info->hash_inputs_check, 32) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Transaction has changed during signing"));
    signing_abort();
    return false;
  }
  return true;
}

static bool tx_info_check_outputs_hash(TxInfo *tx_info) {
  uint8_t hash[32] = {0};
  hasher_Final(&tx_info->hasher_check, hash);
  if (memcmp(hash, tx_info->hash_outputs, 32) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Transaction has changed during signing"));
    signing_abort();
    return false;
  }
  return true;
}

static bool coinjoin_add_input(TxInputType *txi) {
  // Mask for the no_fee bits in coinjoin_flags.
  const uint8_t COINJOIN_FLAGS_NO_FEE = 0x02;

  if (txi->script_type == InputScriptType_EXTERNAL) {
    return true;
  }

  // Add to coordination_fee_base, except for remixes and small inputs which are
  // not charged a coordination fee.
  bool no_fee = txi->coinjoin_flags & COINJOIN_FLAGS_NO_FEE;
  if (txi->amount > coinjoin_request.no_fee_threshold && !no_fee) {
    if (!add_amount(&coinjoin_coordination_fee_base, txi->amount)) {
      return false;
    }
  }

  // Since this took a longer time, update progress.
  report_progress(true);
  return true;
}

static bool signing_add_input(TxInputType *txinput) {
  // hash all input data to check it later (relevant for fee computation)
  if (!tx_input_check_hash(&info.hasher_check, txinput)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to hash input"));
    signing_abort();
    return false;
  }

  if (txinput->script_type != InputScriptType_EXTERNAL) {
    // External inputs should have scriptPubKey set by the host.
    if (!input_validate_path(txinput) || !input_derive_node(txinput) ||
        !fill_input_script_pubkey(txinput)) {
      return false;
    }
  }

  // Add input to BIP-143/BIP-341 computation.
  if (!tx_info_add_input(&info, txinput)) {
    return false;
  }

  if (is_coinjoin == sectrue) {
    if (!coinjoin_add_input(txinput)) {
      return false;
    }
  }

#if !BITCOIN_ONLY
  if (coin->decred) {
    if (serialize) {
      // serialize Decred prefix in Phase 1
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size =
          tx_serialize_input(&to, txinput, resp.serialized.serialized_tx.bytes);
    }

    // compute Decred hashPrefix
    tx_serialize_input_hash(&ti, txinput);
  }
#endif
  return true;
}

// check if the hash of the prevtx matches
static bool signing_check_prevtx_hash(void) {
  uint8_t hash[32] = {0};
  tx_hash_final(&tp, hash, true);
  if (memcmp(hash, input.prev_hash.bytes, 32) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Encountered invalid prevhash"));
    signing_abort();
    return false;
  }

  // prevtx is checked
  progress_step++;
  progress_substep = 0;

  if (idx1 < info.inputs_count - 1) {
    idx1++;
    send_req_3_input();
  } else {
    if (!tx_info_check_inputs_hash(&info)) {
      return false;
    }

    idx1 = 0;
#if !BITCOIN_ONLY
    if (coin->decred) {
      // Decred prefix serialized in Phase 1, skip Phase 2
      send_req_decred_witness();
    } else
#endif
    {
      if (is_replacement) {
        // Verify original transaction.
        phase2_request_orig_input();
      } else {
        // Proceed to transaction signing.
        phase2_request_next_input(true);
      }
    }
  }

  return true;
}

static bool compile_output(TxOutputType *in, TxOutputBinType *out,
                           bool needs_confirm) {
  memzero(out, sizeof(TxOutputBinType));
  out->amount = in->amount;
  out->decred_script_version = DECRED_SCRIPT_VERSION;

  if (in->script_type == OutputScriptType_PAYTOOPRETURN) {
    // only 0 satoshi allowed for OP_RETURN
    if (in->amount != 0 || in->has_address || (in->address_n_count > 0) ||
        in->has_multisig) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to compile output"));
      signing_abort();
      return false;
    }
    if (needs_confirm) {
      if (in->op_return_data.size >= 8 &&
          memcmp(in->op_return_data.bytes, "omni", 4) ==
              0) {  // OMNI transaction
        layoutConfirmOmni(in->op_return_data.bytes, in->op_return_data.size);
      } else {
        layoutConfirmOpReturn(in->op_return_data.bytes,
                              in->op_return_data.size);
      }
      if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput,
                         false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        signing_abort();
        return false;
      }
    }
    op_return_to_script_pubkey(
        in->op_return_data.bytes, in->op_return_data.size,
        out->script_pubkey.bytes, &out->script_pubkey.size);
    return true;
  }

  if (in->address_n_count > 0) {
    InputScriptType input_script_type = 0;

    if (!change_output_to_input_script_type(in->script_type,
                                            &input_script_type)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to compile output"));
      signing_abort();
      return false;
    }
    if (!derive_node(input_script_type, in->address_n_count, in->address_n,
                     in->has_multisig)) {
      return false;
    }
    if (hdnode_fill_public_key(&node) != 0 ||
        !compute_address(coin, input_script_type, &node, in->has_multisig,
                         &in->multisig, in->address)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to compile output"));
      signing_abort();
      return false;
    }
  } else if (!in->has_address) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to compile output"));
    signing_abort();
    return false;
  }

  if (!address_to_script_pubkey(coin, in->address, out->script_pubkey.bytes,
                                &out->script_pubkey.size)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to compile output"));
    signing_abort();
    return false;
  }

  if (needs_confirm) {
    layoutConfirmOutput(coin, amount_unit, in);
    if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool is_change_output(const TxInfo *tx_info,
                             const TxOutputType *txoutput) {
  if (!is_change_output_script_type(txoutput->script_type)) {
    return false;
  }

  if (txoutput->address_n_count == 0) {
    return false;
  }

  if (txoutput->has_multisig) {
    if (!check_change_multisig_fp(tx_info, txoutput)) {
      return false;
    }
    if (!multisig_uses_single_path(&(txoutput->multisig))) {
      // An address that uses different derivation paths for different xpubs
      // could be difficult to discover if the user did not note all the paths.
      // The reason is that each path ends with an address index, which can have
      // 1,000,000 possible values. If the address is a t-out-of-n multisig, the
      // total number of possible paths is 1,000,000^n. This can be exploited by
      // an attacker who has compromised the user's computer. The attacker could
      // randomize the address indices and then demand a ransom from the user to
      // reveal the paths. To prevent this, we require that all xpubs use the
      // same derivation path.
      return false;
    }
  }

  if (!check_change_is_multisig(tx_info, txoutput)) {
    return false;
  }

  if (!check_change_script_type(tx_info, txoutput)) {
    return false;
  }

  return check_change_bip32_path(tx_info, txoutput);
}

static bool signing_add_output(TxOutputType *txoutput) {
  // Phase1: Check outputs
  //   add it to hash_outputs
  //   ask user for permission

  bool is_change = is_change_output(&info, txoutput);

  uint32_t output_weight = tx_output_weight(coin, txoutput);
  tx_weight += output_weight;
  if (is_change) {
    our_weight += output_weight;
  }

  // Don't allow adding new external outputs in replacement transactions. There
  // is actually nothing wrong with adding new external outputs, but the only
  // way to pay for them would be by supplying a new (verified) external input,
  // which is currently not supported.
  if (is_replacement && !txoutput->has_orig_hash && !is_change) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Adding new external outputs in replacement transactions "
                      "is not supported."));
    signing_abort();
    return false;
  }

  // Add amounts.

  if (!add_amount(&total_out, txoutput->amount)) {
    return false;
  }

  if (is_change) {
    if (!add_amount(&change_out, txoutput->amount)) {
      return false;
    }

    change_count++;
    if (change_count <= 0) {
      fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
      signing_abort();
      return false;
    }
  }

  // If address_n is specified, then check that the script type matches.
  if (txoutput->address_n_count != 0) {
    InputScriptType script_type = 0;
    if (!change_output_to_input_script_type(txoutput->script_type,
                                            &script_type)) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Unsupported script type."));
      signing_abort();
      return false;
    }

    if (!validate_path(script_type, txoutput->address_n_count,
                       txoutput->address_n, txoutput->has_multisig)) {
      return false;
    }
  }

  // Skip confirmation of change-outputs and skip output confirmation altogether
  // in replacement transactions.
  bool skip_confirm = is_change || is_replacement || (is_coinjoin == sectrue);
  if (!compile_output(txoutput, &bin_output, !skip_confirm)) {
    return false;
  }
  if (!skip_confirm) {
    report_progress(true);
  }
#if !BITCOIN_ONLY
  if (coin->decred) {
    if (serialize) {
      // serialize Decred prefix in Phase 1
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size = tx_serialize_output(
          &to, &bin_output, resp.serialized.serialized_tx.bytes);
    }

    // compute Decred hashPrefix
    tx_serialize_output_hash(&ti, &bin_output);
  }
#endif
  // Add output to BIP-143/BIP-341 computation.
  return tx_info_add_output(&info, &bin_output);
}

static bool save_signature(TxInputType *txinput) {
  // Locate the signature in the witness or script_sig. We are assuming that the
  // input is not multisig, which simplifies verification.
  uint8_t *bytes = NULL;
  size_t size = 0;
  if (txinput->has_witness && txinput->witness.size > 1) {
    // Skip the number of stack items.
    bytes = txinput->witness.bytes + 1;
    size = txinput->witness.size - 1;
  } else if (txinput->has_script_sig && txinput->script_sig.size != 0) {
    bytes = txinput->script_sig.bytes;
    size = txinput->script_sig.size;
  }

  // We make use of the fact that the signature with hash type is at most
  // 73 bytes in length and that both VarInt <= 252 and OP_PUSH length <= 75
  // encode to one byte.
  if (bytes == NULL || bytes[0] < 1 || bytes[0] > size) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Unsupported signature script."));
    signing_abort();
    return false;
  }
  size = bytes[0];
  bytes += 1;

  if (txinput->script_type == InputScriptType_SPENDTAPROOT) {
    if (size != 64) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Unsupported signature script."));
      signing_abort();
      return false;
    }
    memcpy(sig, bytes, size);
  } else {
    // Decode the DER-encoded signature and store in sig.
    if (bytes[size - 1] != SIGHASH_ALL ||
        ecdsa_sig_from_der(bytes, size - 1, sig) != 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Unsupported signature script."));
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool signing_add_orig_input(TxInputType *orig_input) {
  // hash all input data to check it later
  if (!tx_input_check_hash(&orig_info.hasher_check, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to hash input"));
    signing_abort();
    return false;
  }

  if (orig_input->script_type != InputScriptType_EXTERNAL) {
    // External inputs should have scriptPubKey set by the host.
    if (!input_derive_node(orig_input) ||
        !fill_input_script_pubkey(orig_input)) {
      return false;
    }
  }

  // Verify that the original input matches the current input.
  // An input is characterized by its prev_hash and prev_index. We also
  // check that the amounts match, so that we don't have to stream the
  // prevtx twice for the same prevtx output. Verifying that script_type
  // matches is just a sanity check. When all inputs are taproot, we don't
  // check the prevtxs, so we have to ensure that the claims about the
  // script_pubkey values and amounts remain consistent throughout.
  if (orig_input->prev_hash.size != input.prev_hash.size ||
      memcmp(orig_input->prev_hash.bytes, input.prev_hash.bytes,
             input.prev_hash.size) != 0 ||
      orig_input->prev_index != input.prev_index ||
      orig_input->amount != input.amount ||
      orig_input->script_type != input.script_type ||
      orig_input->script_pubkey.size != input.script_pubkey.size ||
      memcmp(orig_input->script_pubkey.bytes, input.script_pubkey.bytes,
             input.script_pubkey.size) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Original input does not match current input."));
    signing_abort();
    return false;
  }

  // Add input to original BIP-143/BIP-341 computation.
  if (!tx_info_add_input(&orig_info, orig_input)) {
    return false;
  }

  if (!add_amount(&orig_total_in, orig_input->amount)) {
    return false;
  }

  // Add input to original TXID computation.
  if (!tx_serialize_input_hash(&tp, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize input"));
    signing_abort();
    return false;
  }

  // Remember the first original internal legacy input.
  if ((orig_input->script_type == InputScriptType_SPENDMULTISIG ||
       orig_input->script_type == InputScriptType_SPENDADDRESS) &&
      !coin->force_bip143 && !coin->overwintered) {
    if (orig_info.next_legacy_input == 0xffffffff) {
      orig_info.next_legacy_input = idx2;
    }
  }

  return true;
}

static bool signing_add_orig_output(TxOutputType *orig_output) {
  // Compute scriptPubKey.
  TxOutputBinType orig_bin_output;
  if (!compile_output(orig_output, &orig_bin_output, false)) {
    return false;
  }

  // Add output to original BIP-143/BIP-341 computation.
  if (!tx_info_add_output(&orig_info, &orig_bin_output)) {
    return false;
  }

  // Add output to original TXID computation.
  if (!tx_serialize_output_hash(&tp, &orig_bin_output)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize output"));
    signing_abort();
    return false;
  }

  // Add amounts.

  if (!add_amount(&orig_total_out, orig_output->amount)) {
    return false;
  }

  bool is_change = is_change_output(&orig_info, orig_output);
  if (is_change) {
    if (!add_amount(&orig_change_out, orig_output->amount)) {
      return false;
    }
  }

  if (idx2 != output.orig_index) {
    // Check a removed original output.

    // Only removal of change-outputs is allowed.
    if (!is_change) {
      fsm_sendFailure(
          FailureType_Failure_DataError,
          _("Removal of original external outputs is not supported."));
      signing_abort();
      return false;
    }
  } else {
    // Check the original output which corresponds to the current output.

    // The scriptPubkeys must come out the same for original and current.
    if (bin_output.script_pubkey.size != orig_bin_output.script_pubkey.size ||
        memcmp(bin_output.script_pubkey.bytes,
               orig_bin_output.script_pubkey.bytes,
               bin_output.script_pubkey.size) != 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Not an original output."));
      signing_abort();
      return false;
    }

    // If the current output is a change-output, then the original output must
    // also be a change-output.
    if (is_change_output(&info, &output) && !is_change) {
      fsm_sendFailure(
          FailureType_Failure_DataError,
          _("Original output is missing change-output parameters."));
      signing_abort();
      return false;
    }

    if (!is_change) {
      if (output.amount < orig_output->amount) {
        // Replacement transactions may need to decrease the value of external
        // outputs to bump the fee. This is needed if the original transaction
        // transfers the entire account balance ("Send Max").
        for (int page = 0; page < 2; ++page) {
          layoutConfirmModifyOutput(coin, amount_unit, &output, orig_output,
                                    page);
          if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput,
                             false)) {
            fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
            signing_abort();
            return false;
          }
        }
      } else if (output.amount > orig_output->amount) {
        // Only PayJoin transactions may increase the value of external outputs
        // by supplying a verified external input. However, verified external
        // inputs are currently not supported.
        fsm_sendFailure(
            FailureType_Failure_ProcessError,
            _("Increasing original output amounts is not supported."));
        signing_abort();
        return false;
      }
    }
  }

  return true;
}

static bool payment_confirm_tx(void) {
  if (has_unverified_external_input) {
    layoutConfirmUnverifiedExternalInputs();
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      signing_abort();
      return false;
    }
  }

  if (coin->negative_fee) {
    // bypass check for negative fee coins, required for reward TX
  } else {
    // check fees
    if (total_out > total_in) {
      fsm_sendFailure(FailureType_Failure_NotEnoughFunds,
                      _("Not enough funds"));
      signing_abort();
      return false;
    }
  }

  uint64_t fee = 0;
  if (total_out <= total_in) {
    fee = total_in - total_out;
    if (fee > ((uint64_t)tx_weight * coin->maxfee_kb) / 4000) {
      layoutFeeOverThreshold(coin, amount_unit, fee);
      if (!protectButton(ButtonRequestType_ButtonRequest_FeeOverThreshold,
                         false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        signing_abort();
        return false;
      }
    }
  } else {
    fee = 0;
  }

  if (change_count > MAX_SILENT_CHANGE_COUNT) {
    layoutChangeCountOverThreshold(change_count);
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      signing_abort();
      return false;
    }
  }

  if (is_replacement) {
    // Replacement transaction.

    // Reject negative fees in original or replacement transactions, so that we
    // don't have to deal with the UI implications.
    if (total_out > total_in || orig_total_out > orig_total_in) {
      fsm_sendFailure(
          FailureType_Failure_ProcessError,
          _("Negative fees not supported in transaction replacement."));
      signing_abort();
      return false;
    }
    uint64_t orig_fee = orig_total_in - orig_total_out;

    // Reject adding external inputs to the original transaction, so that we
    // don't have to deal with the UI implications. This could be used for
    // BIP-78 Payjoins when we support presigned external inputs.
    if (external_in != orig_external_in) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Adding external inputs is not supported."));
      signing_abort();
      return false;
    }

    // Sanity check. Replacement transactions are only allowed to make
    // amendments which do not increase the amount that we are spending on
    // external outputs. Additional funds can only go towards the fee, which is
    // confirmed by the user. The check may fail if the replacement transaction
    // starts mixing accounts and breaks change-output identification.
    if (total_out - change_out - external_in >
        orig_total_out - orig_change_out - orig_external_in) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Invalid replacement transaction."));
      signing_abort();
      return false;
    }

    // Replacement transactions must not change the effective nLockTime.
    uint32_t effective_lock_time =
        info.min_sequence == SEQUENCE_FINAL ? 0 : info.lock_time;
    uint32_t orig_effective_lock_time =
        orig_info.min_sequence == SEQUENCE_FINAL ? 0 : orig_info.lock_time;
    if (effective_lock_time != orig_effective_lock_time) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Original transactions must have same effective "
                        "nLockTime as replacement transaction."));
      signing_abort();
      return false;
    }

    // Fee modification.
    if (fee != orig_fee) {
      layoutConfirmModifyFee(coin, amount_unit, orig_fee, fee, tx_weight);
      if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        signing_abort();
        return false;
      }
    }
  } else {
    // Standard transaction.

    if (info.lock_time != 0) {
      bool lock_time_disabled = (info.min_sequence == SEQUENCE_FINAL);
      layoutConfirmNondefaultLockTime(info.lock_time, lock_time_disabled);
      if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        signing_abort();
        return false;
      }
    }

    // last confirmation
    layoutConfirmTx(coin, amount_unit, total_in, external_in, total_out,
                    change_out, tx_weight);
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool coinjoin_confirm_tx(void) {
  // Minimum registrable output amount accepted by the CoinJoin coordinator. The
  // CoinJoin request may specify an even lower amount.
  const uint64_t MIN_REGISTRABLE_OUTPUT_AMOUNT = 5000;

  // Largest possible weight of an output supported by Trezor (P2TR or P2WSH).
  const uint64_t MAX_OUTPUT_WEIGHT = 4 * (8 + 1 + 1 + 1 + 32);

  if (has_unverified_external_input) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Unverifiable external input."));
    signing_abort();
    return false;
  }

  uint64_t mining_fee = 0;
  if (total_out <= total_in) {
    mining_fee = total_in - total_out;
  }

  // The maximum mining fee that the user should be paying.
  uint64_t our_max_mining_fee =
      coinjoin_authorization.max_fee_per_kvbyte * ((our_weight + 3) / 4) / 1000;

  // The coordination fee for the user's inputs.
  uint64_t our_coordination_fee =
      MIN(coinjoin_request.fee_rate,
          coinjoin_authorization.max_coordinator_fee_rate) *
      coinjoin_coordination_fee_base / FEE_RATE_DECIMALS / 100;

  // Total fees that the user is paying.
  uint64_t our_fees = 0;
  if (change_out <= total_in - external_in) {
    our_fees = total_in - external_in - change_out;
  }

  // For the next step we need to estimate an upper bound on the mining fee used
  // by the coordinator. The coordinator does not include the base weight of the
  // transaction when computing the mining fee, so we take this into account.
  uint64_t max_fee_per_output =
      MAX_OUTPUT_WEIGHT * mining_fee / (tx_weight - tx_base_weight);

  // Calculate the minimum registrable output amount in a CoinJoin plus the
  // mining fee that it would cost to register. Amounts below this value are
  // left to the coordinator or miners and effectively constitute an extra fee
  // for the user.
  uint64_t min_allowed_output_amount_plus_fee =
      MIN(coinjoin_request.min_registrable_amount,
          MIN_REGISTRABLE_OUTPUT_AMOUNT) +
      max_fee_per_output;

  if (our_fees > our_coordination_fee + our_max_mining_fee +
                     min_allowed_output_amount_plus_fee) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Total fee over threshold."));
    signing_abort();
    return false;
  }

  if (coinjoin_authorization.max_rounds < 1) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Exceeded number of coinjoin rounds."));
    signing_abort();
    return false;
  }

  coinjoin_authorization.max_rounds -= 1;
  if (coinjoin_authorization.max_rounds >= 1) {
    config_setCoinJoinAuthorization(&coinjoin_authorization);
  } else {
    config_setCoinJoinAuthorization(NULL);
  }

  return true;
}

static bool signing_confirm_tx(void) {
  if (is_coinjoin == sectrue) {
    return coinjoin_confirm_tx();
  } else {
    return payment_confirm_tx();
  }
}

static uint32_t signing_hash_type(const TxInputType *txinput) {
  uint32_t hash_type = SIGHASH_ALL;
  if (txinput->script_type == InputScriptType_SPENDTAPROOT) {
    hash_type = SIGHASH_ALL_TAPROOT;
  }

  if (coin->has_fork_id) {
    hash_type |= (coin->fork_id << 8) | SIGHASH_FORKID;
  }

  return hash_type;
}

static void signing_hash_bip143(const TxInfo *tx_info,
                                const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type(txinput);
  Hasher hasher_preimage = {0};
  hasher_Init(&hasher_preimage, coin->curve->hasher_sign);

  // nVersion
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->version, 4);
  // hashPrevouts
  hasher_Update(&hasher_preimage, tx_info->hash_prevouts143, 32);
  // hashSequence
  hasher_Update(&hasher_preimage, tx_info->hash_sequence143, 32);
  // outpoint
  tx_prevout_hash(&hasher_preimage, txinput);
  // scriptCode
  tx_script_hash(&hasher_preimage, txinput->script_sig.size,
                 txinput->script_sig.bytes);
  // amount
  hasher_Update(&hasher_preimage, (const uint8_t *)&txinput->amount, 8);
  // nSequence
  tx_sequence_hash(&hasher_preimage, txinput);
  // hashOutputs
  hasher_Update(&hasher_preimage, tx_info->hash_outputs143, 32);
  // nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->lock_time, 4);
  // nHashType
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);

  hasher_Final(&hasher_preimage, hash);
}

static void signing_hash_bip341(const TxInfo *tx_info, uint32_t i,
                                uint8_t sighash_type, uint8_t *hash) {
  const uint8_t zero = 0;
  Hasher sigmsg_hasher = {0};
  hasher_Init(&sigmsg_hasher, HASHER_SHA2_TAPSIGHASH);
  // sighash epoch 0
  hasher_Update(&sigmsg_hasher, &zero, 1);
  // nHashType
  hasher_Update(&sigmsg_hasher, &sighash_type, 1);
  // nVersion
  hasher_Update(&sigmsg_hasher, (const uint8_t *)&tx_info->version, 4);
  // nLockTime
  hasher_Update(&sigmsg_hasher, (const uint8_t *)&tx_info->lock_time, 4);
  // sha_prevouts
  hasher_Update(&sigmsg_hasher, tx_info->hash_prevouts, 32);
  // sha_amounts
  hasher_Update(&sigmsg_hasher, tx_info->hash_amounts, 32);
  // sha_scriptpubkeys
  hasher_Update(&sigmsg_hasher, tx_info->hash_scriptpubkeys, 32);
  // sha_sequences
  hasher_Update(&sigmsg_hasher, tx_info->hash_sequences, 32);
  // sha_outputs
  hasher_Update(&sigmsg_hasher, tx_info->hash_outputs, 32);
  // spend_type 0 (no tapscript message extension, no annex)
  hasher_Update(&sigmsg_hasher, &zero, 1);
  // input_index
  hasher_Update(&sigmsg_hasher, (const uint8_t *)&i, 4);

  hasher_Final(&sigmsg_hasher, hash);
}

#if !BITCOIN_ONLY
static void signing_hash_zip243(const TxInfo *tx_info,
                                const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type(txinput);
  const uint8_t null_bytes[32] = {0};
  uint8_t personal[16] = {0};
  memcpy(personal, "ZcashSigHash", 12);
  memcpy(personal + 12, &tx_info->branch_id, 4);
  Hasher hasher_preimage = {0};
  hasher_InitParam(&hasher_preimage, HASHER_BLAKE2B_PERSONAL, personal,
                   sizeof(personal));

  // 1. nVersion | fOverwintered
  uint32_t ver = tx_info->version | TX_OVERWINTERED;
  hasher_Update(&hasher_preimage, (const uint8_t *)&ver, 4);
  // 2. nVersionGroupId
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->version_group_id,
                4);
  // 3. hashPrevouts
  hasher_Update(&hasher_preimage, tx_info->hash_prevouts, 32);
  // 4. hashSequence
  hasher_Update(&hasher_preimage, tx_info->hash_sequences, 32);
  // 5. hashOutputs
  hasher_Update(&hasher_preimage, tx_info->hash_outputs, 32);
  // 6. hashJoinSplits
  hasher_Update(&hasher_preimage, null_bytes, 32);
  // 7. hashShieldedSpends
  hasher_Update(&hasher_preimage, null_bytes, 32);
  // 8. hashShieldedOutputs
  hasher_Update(&hasher_preimage, null_bytes, 32);
  // 9. nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->lock_time, 4);
  // 10. expiryHeight
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->expiry, 4);
  // 11. valueBalance
  hasher_Update(&hasher_preimage, null_bytes, 8);
  // 12. nHashType
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);
  // 13a. outpoint
  tx_prevout_hash(&hasher_preimage, txinput);
  // 13b. scriptCode
  tx_script_hash(&hasher_preimage, txinput->script_sig.size,
                 txinput->script_sig.bytes);
  // 13c. value
  hasher_Update(&hasher_preimage, (const uint8_t *)&txinput->amount, 8);
  // 13d. nSequence
  tx_sequence_hash(&hasher_preimage, txinput);

  hasher_Final(&hasher_preimage, hash);
}
#endif

#if !BITCOIN_ONLY
static void signing_hash_zip244(const TxInfo *tx_info,
                                const TxInputType *txinput, uint8_t *hash) {
  Hasher hasher = {0};

  // `S.2g: txin_sig_digest` field for signature digest computation.
  // https://zips.z.cash/zip-0244#s-2g-txin-sig-digest
  uint8_t txin_sig_digest[32] = {0};
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, "Zcash___TxInHash", 16);
  // S.2g.i: prevout (field encoding)
  tx_prevout_hash(&hasher, txinput);
  // S.2g.ii: value (8-byte signed little-endian)
  hasher_Update(&hasher, (const uint8_t *)&txinput->amount, 8);
  // S.2g.iii: scriptPubKey (field encoding)
  tx_script_hash(&hasher, txinput->script_pubkey.size,
                 txinput->script_pubkey.bytes);
  // S.2g.iv: nSequence (4-byte unsigned little-endian)
  hasher_Update(&hasher, (const uint8_t *)&txinput->sequence, 4);
  hasher_Final(&hasher, txin_sig_digest);

  // `S.2: transparent_sig_digest` field for signature digest computation.
  // https://zips.z.cash/zip-0244#s-2-transparent-sig-digest
  uint8_t transparent_sig_digest[32] = {0};
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, "ZTxIdTranspaHash", 16);
  uint32_t hash_type = signing_hash_type(txinput);
  // S.2a: hash_type (1 byte)
  hasher_Update(&hasher, (const uint8_t *)&hash_type, 1);
  // S.2b: prevouts_sig_digest (32-byte hash)
  hasher_Update(&hasher, tx_info->hash_prevouts,
                sizeof(tx_info->hash_prevouts));
  // S.2c: amounts_sig_digest (32-byte hash)
  hasher_Update(&hasher, tx_info->hash_amounts, sizeof(tx_info->hash_amounts));
  // S.2d: scriptpubkeys_sig_digest (32-byte hash)
  hasher_Update(&hasher, tx_info->hash_scriptpubkeys,
                sizeof(tx_info->hash_scriptpubkeys));
  // S.2e: sequence_sig_digest (32-byte hash)
  hasher_Update(&hasher, tx_info->hash_sequences,
                sizeof(tx_info->hash_sequences));
  // S.2f: outputs_sig_digest (32-byte hash)
  hasher_Update(&hasher, tx_info->hash_outputs, sizeof(tx_info->hash_outputs));
  // S.2g: txin_sig_digest (32-byte hash)
  hasher_Update(&hasher, txin_sig_digest, sizeof(txin_sig_digest));
  hasher_Final(&hasher, transparent_sig_digest);

  // `S.3: sapling_digest` field. Empty Sapling bundle.
  uint8_t sapling_digest[32] = {0};
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, "ZTxIdSaplingHash", 16);
  hasher_Final(&hasher, sapling_digest);

  // `S.4: orchard_digest` field. Empty Orchard bundle.
  uint8_t orchard_digest[32] = {0};
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, "ZTxIdOrchardHash", 16);
  hasher_Final(&hasher, orchard_digest);

  // Final transaction signature digest.
  // https://zips.z.cash/zip-0244#id13
  uint8_t personal[16] = {0};
  memcpy(personal, "ZcashTxHash_", 12);
  memcpy(personal + 12, &tx_info->branch_id, 4);
  hasher_InitParam(&hasher, HASHER_BLAKE2B_PERSONAL, personal,
                   sizeof(personal));
  // S.1: header_digest (32-byte hash output)
  hasher_Update(&hasher, tx_info->hash_header, sizeof(tx_info->hash_header));
  // S.2: transparent_sig_digest (32-byte hash output)
  hasher_Update(&hasher, transparent_sig_digest,
                sizeof(transparent_sig_digest));
  // S.3: sapling_digest (32-byte hash output)
  hasher_Update(&hasher, sapling_digest, sizeof(sapling_digest));
  // S.4: orchard_digest (32-byte hash output)
  hasher_Update(&hasher, orchard_digest, sizeof(orchard_digest));
  hasher_Final(&hasher, hash);
}
#endif

static bool signing_verify_orig_nonlegacy_input(TxInputType *orig_input) {
  // Nothing to verify for external inputs.
  if (orig_input->script_type == InputScriptType_EXTERNAL) {
    return true;
  }

  // Save the signature before script_sig is overwritten.
  if (!save_signature(orig_input)) {
    return false;
  }

  // Derive node.public_key and fill script_sig with the legacy scriptPubKey
  // (aka BIP-143 script code), which is what our code expects here in order
  // to properly compute the BIP-143 transaction digest.
  if (!input_derive_node(orig_input) || !fill_input_script_sig(orig_input)) {
    return false;
  }

  // Compute the signed digest and verify signature.
  uint8_t hash[32] = {0};
  uint32_t hash_type = signing_hash_type(orig_input);
  bool valid = false;
  if (orig_input->script_type == InputScriptType_SPENDTAPROOT) {
    signing_hash_bip341(&orig_info, idx1, hash_type & 0xff, hash);
    uint8_t output_public_key[32] = {0};
    valid = (zkp_bip340_tweak_public_key(node.public_key + 1, NULL,
                                         output_public_key) == 0) &&
            (zkp_bip340_verify_digest(output_public_key, sig, hash) == 0);
  } else {
#if !BITCOIN_ONLY
    if (coin->overwintered) {
      signing_hash_zip243(&orig_info, orig_input, hash);
    } else
#endif
    {
      signing_hash_bip143(&orig_info, orig_input, hash);
    }

    valid = ecdsa_verify_digest(coin->curve->params, node.public_key, sig,
                                hash) == 0;
  }

  if (!valid) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature."));
    signing_abort();
  }

  return valid;
}

static bool signing_verify_orig_legacy_input(void) {
  // Finalize legacy digest computation.
  uint32_t hash_type = signing_hash_type(&input);
  hasher_Update(&ti.hasher, (const uint8_t *)&hash_type, 4);

  // Compute the signed digest and verify signature.
  uint8_t hash[32] = {0};
  tx_hash_final(&ti, hash, false);

  bool valid = ecdsa_verify_digest(coin->curve->params, pubkey, sig, hash) == 0;

  if (!valid) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature."));
    signing_abort();
  }

  return valid;
}

static bool signing_hash_orig_input(TxInputType *orig_input) {
  if (idx2 == 0) {
    uint32_t branch_id = 0;
#if !BITCOIN_ONLY
    branch_id = orig_info.branch_id;
#endif
    tx_init(&ti, orig_info.inputs_count, orig_info.outputs_count,
            orig_info.version, orig_info.lock_time, orig_info.expiry, branch_id,
            0, coin->curve->hasher_sign, coin->overwintered,
            orig_info.version_group_id, orig_info.timestamp);
    // Reset the inner transaction check.
    hasher_Reset(&orig_info.hasher_check);
  }

  // Add input to the inner transaction check.
  if (!tx_input_check_hash(&orig_info.hasher_check, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to hash input"));
    signing_abort();
    return false;
  }

  if (idx2 == idx1) {
    // Add input to the outer transaction check.
    if (!tx_input_check_hash(&hasher_check, orig_input)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to hash input"));
      signing_abort();
      return false;
    }

    // Save the signature before script_sig is overwritten.
    if (!save_signature(orig_input)) {
      return false;
    }

    // Derive node.public_key and fill script_sig with the legacy
    // scriptPubKey which is what our code expects here in order to properly
    // compute the transaction digest.
    if (!input_derive_node(orig_input) || !fill_input_script_sig(orig_input)) {
      return false;
    }

    memcpy(pubkey, node.public_key, sizeof(pubkey));
    memcpy(&input, orig_input, sizeof(input));
  } else {
    if (orig_info.next_legacy_input == idx1 && idx2 > idx1 &&
        (orig_input->script_type == InputScriptType_SPENDADDRESS ||
         orig_input->script_type == InputScriptType_SPENDMULTISIG)) {
      orig_info.next_legacy_input = idx2;
    }
    orig_input->script_sig.size = 0;
  }

  // Add input to original legacy digest computation now that script_sig is
  // set.
  if (!tx_serialize_input_hash(&ti, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize input"));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_hash_orig_output(TxOutputType *orig_output) {
  if (!compile_output(orig_output, &bin_output, false)) {
    return false;
  }

  // Add the output to the inner transaction check.
  tx_output_hash(&orig_info.hasher_check, &bin_output, coin->decred);

  // Add the output to original legacy digest computation
  if (!tx_serialize_output_hash(&ti, &bin_output)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize output"));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_check_orig_tx(void) {
  uint8_t hash[32] = {0};

  // Finalize original TXID computation and ensure it matches orig_hash.
  tx_hash_final(&tp, hash, true);
  if (memcmp(hash, orig_hash, sizeof(orig_hash)) != 0) {
    // This may happen if incorrect information is supplied in the TXORIGINPUT
    // or TXORIGOUTPUT responses or if the device is loaded with the wrong seed,
    // because we derive the scriptPubKeys of change-outputs from the seed using
    // the provided path.
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Invalid original TXID."));
    signing_abort();
    return false;
  }

  return true;
}

static void phase1_finish(void) {
#if !BITCOIN_ONLY
  if (coin->decred) {
    // compute Decred hashPrefix
    tx_hash_final(&ti, decred_hash_prefix, false);
  }
#endif

  // Finish computation of BIP-143/BIP-341/ZIP-243 sub-hashes.
  tx_info_finish(&info);
  tx_info_finish(&orig_info);

  if (is_replacement) {
    if (!signing_check_orig_tx()) {
      return;
    }
  }

  if (!signing_confirm_tx()) {
    return;
  }

#if DEBUG_LINK
  if (!assert_progress_finished()) {
    return;
  }
#endif
  // Now phase 2 begins and the transaction is signed.
  init_signing_progress();

  if (taproot_only) {
    // All internal inputs are Taproot. We do not need to verify that their
    // parameters match previous transactions. We can trust the amounts and
    // scriptPubKeys, because if an invalid value is provided then all issued
    // signatures will be invalid.
    if (is_replacement) {
      // Verify original transaction.
      phase2_request_orig_input();
    } else {
      // Proceed directly to transaction signing.
      phase2_request_next_input(true);
    }
#if !BITCOIN_ONLY
  } else if (coin->overwintered && info.version == 5) {
    // ZIP-244 transactions are treated same as Taproot.
    phase2_request_next_input(true);
#endif
  } else {
    // There are internal non-Taproot inputs. We need to verify all inputs,
    // because we can't trust any amounts or scriptPubKeys. If we did, then an
    // attacker who provides invalid information about amounts, scriptPubKeys
    // and/or script types may still obtain valid signatures for legacy and
    // SegWit v0 inputs. These valid signatures could be exploited in subsequent
    // signing operations to falsely claim externality of the already signed
    // inputs or to falsely claim that a transaction is a replacement of an
    // already approved transaction or to construct a valid transaction by
    // combining signatures obtained in multiple rounds of the attack.
    send_req_3_input();
  }
}

static void phase1_request_next_output(void) {
  if (idx1 < info.outputs_count - 1) {
    idx1++;
    send_req_2_output();
  } else {
    idx1 = 0;
    if (is_replacement) {
      if (idx2 < orig_info.outputs_count) {
        send_req_2_orig_output();
#if !BITCOIN_ONLY
      } else if (coin->extra_data && tp.extra_data_len > 0) {  // has extra data
        send_req_2_orig_extradata(0, MIN(1024, tp.extra_data_len));
#endif
      } else {
        phase1_finish();
      }
    } else {
      phase1_finish();
    }
  }
}

static void phase1_request_orig_output(void) {
  if (!is_replacement ||
      memcmp(output.orig_hash.bytes, orig_hash, sizeof(orig_hash)) != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Unknown original transaction."));
    signing_abort();
    return;
  }

  if (output.orig_index >= orig_info.outputs_count) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Not enough outputs in original transaction."));
    signing_abort();
    return;
  }

  if (idx2 > output.orig_index) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Rearranging of original outputs is not supported."));
    signing_abort();
    return;
  }

  send_req_2_orig_output();
}

#if !BITCOIN_ONLY
static void signing_hash_decred(const TxInputType *txinput,
                                const uint8_t *hash_witness, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type(txinput);
  Hasher hasher_preimage = {0};
  hasher_Init(&hasher_preimage, coin->curve->hasher_sign);
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);
  hasher_Update(&hasher_preimage, decred_hash_prefix, 32);
  hasher_Update(&hasher_preimage, hash_witness, 32);
  hasher_Final(&hasher_preimage, hash);
}
#endif

static bool signing_sign_ecdsa(TxInputType *txinput, const uint8_t *private_key,
                               const uint8_t *public_key, const uint8_t *hash) {
  resp.has_serialized = true;
  resp.serialized.has_signature_index = true;
  resp.serialized.signature_index = idx1;
  resp.serialized.has_signature = true;

  if (!tx_sign_ecdsa(coin->curve->params, private_key, hash,
                     resp.serialized.signature.bytes,
                     &resp.serialized.signature.size)) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    signing_abort();
    return false;
  }

  uint8_t sighash = signing_hash_type(txinput) & 0xff;
  if (txinput->has_multisig) {
    // fill in the signature
    int pubkey_idx =
        cryptoMultisigPubkeyIndex(coin, &(txinput->multisig), public_key);
    if (pubkey_idx < 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Pubkey not found in multisig script"));
      signing_abort();
      return false;
    }
    memcpy(txinput->multisig.signatures[pubkey_idx].bytes,
           resp.serialized.signature.bytes, resp.serialized.signature.size);
    txinput->multisig.signatures[pubkey_idx].size =
        resp.serialized.signature.size;
    txinput->script_sig.size = serialize_script_multisig(
        coin, &(txinput->multisig), sighash, txinput->script_sig.bytes);
    if (txinput->script_sig.size == 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to serialize multisig script"));
      signing_abort();
      return false;
    }
  } else {  // SPENDADDRESS
    txinput->script_sig.size = serialize_script_sig(
        resp.serialized.signature.bytes, resp.serialized.signature.size,
        public_key, 33, sighash, txinput->script_sig.bytes);
  }
  return true;
}

static bool signing_sign_bip340(const uint8_t *private_key,
                                const uint8_t *hash) {
  resp.has_serialized = true;
  resp.serialized.has_signature_index = true;
  resp.serialized.signature_index = idx1;
  resp.serialized.has_signature = true;

  if (!tx_sign_bip340(private_key, hash, resp.serialized.signature.bytes,
                      &resp.serialized.signature.size)) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_sign_legacy_input(void) {
  // Finalize legacy digest computation.
  uint32_t hash_type = signing_hash_type(&input);
  hasher_Update(&ti.hasher, (const uint8_t *)&hash_type, 4);

  // Compute the digest and generate signature.
  uint8_t hash[32] = {0};
  tx_hash_final(&ti, hash, false);
  if (!signing_sign_ecdsa(&input, privkey, pubkey, hash)) return false;
  if (serialize) {
    resp.has_serialized = true;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.size =
        tx_serialize_input(&to, &input, resp.serialized.serialized_tx.bytes);
  }
  return true;
}

static bool signing_sign_segwit_input(TxInputType *txinput) {
  // idx1: index to sign
  uint8_t hash[32] = {0};

  if (is_external_input(idx1) !=
      (txinput->script_type == InputScriptType_EXTERNAL)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Transaction has changed during signing"));
    signing_abort();
    return false;
  }

  if (txinput->script_type == InputScriptType_SPENDTAPROOT) {
    signing_hash_bip341(&info, idx1, signing_hash_type(txinput), hash);

    if (!input_validate_path(txinput) || !tx_info_check_input(&info, txinput) ||
        !input_derive_node(txinput) ||
        !signing_sign_bip340(node.private_key, hash)) {
      return false;
    }

    if (serialize) {
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size = serialize_p2tr_witness(
          resp.serialized.signature.bytes, resp.serialized.signature.size, 0,
          resp.serialized.serialized_tx.bytes);
    }
  } else if (txinput->script_type == InputScriptType_SPENDP2SHWITNESS ||
             txinput->script_type == InputScriptType_SPENDWITNESS) {
    if (!txinput->has_amount) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Segwit input without amount"));
      signing_abort();
      return false;
    }

    if (taproot_only) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Transaction has changed during signing"));
      signing_abort();
      return false;
    }

    if (!input_validate_path(txinput) || !tx_info_check_input(&info, txinput) ||
        !input_derive_node(txinput) || !fill_input_script_sig(txinput)) {
      return false;
    }

    signing_hash_bip143(&info, txinput, hash);

    if (!signing_sign_ecdsa(txinput, node.private_key, node.public_key, hash))
      return false;

    if (serialize) {
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      uint8_t sighash = signing_hash_type(txinput) & 0xff;
      if (txinput->has_multisig) {
        uint32_t r = 1;  // skip number of items (filled in later)
        resp.serialized.serialized_tx.bytes[r] = 0;
        r++;
        int nwitnesses = 2;
        for (uint32_t i = 0; i < txinput->multisig.signatures_count; i++) {
          if (txinput->multisig.signatures[i].size == 0) {
            continue;
          }
          nwitnesses++;
          txinput->multisig.signatures[i]
              .bytes[txinput->multisig.signatures[i].size] = sighash;
          r += tx_serialize_script(txinput->multisig.signatures[i].size + 1,
                                   txinput->multisig.signatures[i].bytes,
                                   resp.serialized.serialized_tx.bytes + r);
        }
        uint32_t script_len =
            compile_script_multisig(coin, &txinput->multisig, 0);
        r += ser_length(script_len, resp.serialized.serialized_tx.bytes + r);
        r += compile_script_multisig(coin, &txinput->multisig,
                                     resp.serialized.serialized_tx.bytes + r);
        resp.serialized.serialized_tx.bytes[0] = nwitnesses;
        resp.serialized.serialized_tx.size = r;
      } else {  // single signature
        resp.serialized.serialized_tx.size = serialize_p2wpkh_witness(
            resp.serialized.signature.bytes, resp.serialized.signature.size,
            node.public_key, 33, sighash, resp.serialized.serialized_tx.bytes);
      }
    }
  } else {
    if (serialize) {
      // no signature to be generated
      resp.has_serialized = true;
      resp.serialized.has_signature_index = false;
      resp.serialized.has_signature = false;
      resp.serialized.has_serialized_tx = true;
      if (txinput->script_type == InputScriptType_EXTERNAL &&
          txinput->has_witness) {
        // fill in the provided witness
        memcpy(resp.serialized.serialized_tx.bytes, txinput->witness.bytes,
               txinput->witness.size);
        resp.serialized.serialized_tx.size = txinput->witness.size;
      } else {
        // empty witness
        resp.serialized.serialized_tx.bytes[0] = 0;
        resp.serialized.serialized_tx.size = 1;
      }
    }
  }

  //  if last witness add tx footer
  if (serialize && idx1 == info.inputs_count - 1) {
    uint32_t r = resp.serialized.serialized_tx.size;
    r += tx_serialize_footer(&to, resp.serialized.serialized_tx.bytes + r);
    resp.serialized.serialized_tx.size = r;
  }
  return true;
}

#if !BITCOIN_ONLY

static bool signing_sign_decred_input(TxInputType *txinput) {
  uint8_t hash[32] = {}, hash_witness[32] = {};
  tx_hash_final(&ti, hash_witness, false);
  signing_hash_decred(txinput, hash_witness, hash);
  if (!signing_sign_ecdsa(txinput, node.private_key, node.public_key, hash))
    return false;
  if (serialize) {
    resp.has_serialized = true;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.size = tx_serialize_decred_witness(
        &to, txinput, resp.serialized.serialized_tx.bytes);
  }
  return true;
}

#endif

#define ENABLE_SEGWIT_NONSEGWIT_MIXING 1

void signing_txack(TransactionType *tx) {
  if (!signing) {
    fsm_sendFailure(FailureType_Failure_UnexpectedMessage,
                    _("Not in Signing mode"));
    layoutHome();
    return;
  }

  report_progress(false);

  memzero(&resp, sizeof(TxRequest));

  switch (signing_stage) {
    case STAGE_REQUEST_1_INPUT:
      progress_step++;
      if (!signing_validate_input(&tx->inputs[0]) ||
          !signing_add_input(&tx->inputs[0])) {
        return;
      }

      if (!tx->inputs[0].has_amount) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Expected input with amount"));
        signing_abort();
        return;
      }

      if (!add_amount(&total_in, tx->inputs[0].amount)) {
        return;
      }

      uint32_t input_weight = tx_input_weight(coin, &tx->inputs[0]);
#if !BITCOIN_ONLY
      if (coin->decred) {
        input_weight += tx_decred_witness_weight(&tx->inputs[0]);
      }
#endif
      tx_weight += input_weight;
      if (is_internal_input_script_type(tx->inputs[0].script_type)) {
        our_weight += input_weight;
        our_inputs_len += 1;
      }

      if (tx->inputs[0].script_type != InputScriptType_SPENDTAPROOT &&
          tx->inputs[0].script_type != InputScriptType_EXTERNAL) {
        taproot_only = false;
      }

      if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG ||
          tx->inputs[0].script_type == InputScriptType_SPENDADDRESS) {
#if !ENABLE_SEGWIT_NONSEGWIT_MIXING
        // don't mix segwit and non-segwit inputs
        if (idx1 > 0 && to.is_segwit == true) {
          fsm_sendFailure(
              FailureType_Failure_DataError,
              _("Mixing segwit and non-segwit inputs is not allowed"));
          signing_abort();
          return;
        }
#endif

        if (!coin->force_bip143 && !coin->overwintered) {
          // remember the first non-segwit input -- this is the first input
          // we need to sign during phase2
          if (info.next_legacy_input == 0xffffffff) {
            info.next_legacy_input = idx1;
          }
        }
      } else if (is_segwit_input_script_type(tx->inputs[0].script_type)) {
#if !ENABLE_SEGWIT_NONSEGWIT_MIXING
        // don't mix segwit and non-segwit inputs
        if (idx1 == 0) {
          to.is_segwit = true;
        } else if (to.is_segwit == false) {
          fsm_sendFailure(
              FailureType_Failure_DataError,
              _("Mixing segwit and non-segwit inputs is not allowed"));
          signing_abort();
          return;
        }
#else
        to.is_segwit = true;
#endif
      } else if (tx->inputs[0].script_type == InputScriptType_EXTERNAL) {
        if (tx->inputs[0].has_ownership_proof) {
          uint8_t ownership_id[OWNERSHIP_ID_SIZE] = {0};
          if (!fsm_getOwnershipId(tx->inputs[0].script_pubkey.bytes,
                                  tx->inputs[0].script_pubkey.size,
                                  ownership_id)) {
            signing_abort();
            return;
          }

          if (!tx_input_verify_nonownership(coin, tx->inputs, ownership_id)) {
            fsm_sendFailure(FailureType_Failure_DataError,
                            _("Invalid external input."));
            signing_abort();
            return;
          }

          if (!add_amount(&external_in, tx->inputs[0].amount)) {
            return;
          }

          if (tx->inputs[0].has_orig_hash) {
            if (!add_amount(&orig_external_in, tx->inputs[0].amount)) {
              return;
            }
          }
        } else {
          has_unverified_external_input = true;
          if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
            fsm_sendFailure(FailureType_Failure_ProcessError,
                            _("Unverifiable external input."));
            signing_abort();
            return;
          }
        }
        set_external_input(idx1);
      } else {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Wrong input script type"));
        signing_abort();
        return;
      }

      if (tx->inputs[0].has_orig_hash) {
#if !BITCOIN_ONLY
        if (coin->overwintered && info.version != 4) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Replacement transactions are not supported."));
          signing_abort();
          return;
        }
#endif

        memcpy(&input, &tx->inputs[0], sizeof(input));
        phase1_request_orig_input();
      } else {
        phase1_request_next_input();
      }

      return;
    case STAGE_REQUEST_1_ORIG_META:
      if (!tx_info_init(&orig_info, tx->inputs_cnt, tx->outputs_cnt,
                        tx->version, tx->lock_time, tx->has_expiry, tx->expiry,
                        tx->has_branch_id, tx->branch_id,
                        tx->has_version_group_id, tx->version_group_id,
                        tx->has_timestamp, tx->timestamp)) {
        return;
      }

      if (coin->decred) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Replacement transactions not supported"));
        signing_abort();
        return;
      }

      if (!coin->extra_data && tx->extra_data_len > 0) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Extra data not enabled on this coin."));
        signing_abort();
        return;
      }

      // Initialize computation of original TXID.
      tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time,
              tx->expiry, tx->branch_id, tx->extra_data_len,
              coin->curve->hasher_sign, coin->overwintered,
              tx->version_group_id, tx->timestamp);

      phase1_request_orig_input();
      return;
    case STAGE_REQUEST_1_ORIG_INPUT:
      if (!signing_validate_input(tx->inputs) ||
          !signing_add_orig_input(tx->inputs)) {
        return;
      }

      idx2++;
      phase1_request_next_input();
      return;
    case STAGE_REQUEST_2_OUTPUT:
      progress_step++;
      if (!signing_validate_output(&tx->outputs[0]) ||
          !signing_add_output(&tx->outputs[0])) {
        return;
      }

      if (tx->outputs[0].has_orig_hash) {
        memcpy(&output, &tx->outputs[0], sizeof(output));
        phase1_request_orig_output();
      } else {
        phase1_request_next_output();
      }
      return;
    case STAGE_REQUEST_2_ORIG_OUTPUT:
      if (!signing_validate_output(tx->outputs) ||
          !signing_add_orig_output(tx->outputs)) {
        return;
      }

      idx2++;

      if (idx2 == output.orig_index + 1) {
        phase1_request_next_output();
      } else if (idx2 < orig_info.outputs_count) {
        send_req_2_orig_output();
#if !BITCOIN_ONLY
      } else if (coin->extra_data && tp.extra_data_len > 0) {  // has extra data
        send_req_2_orig_extradata(0, MIN(1024, tp.extra_data_len));
#endif
      } else {
        phase1_finish();
      }
      return;
#if !BITCOIN_ONLY
    case STAGE_REQUEST_2_ORIG_EXTRADATA:
      // Add extra data to original TXID computation.
      if (!tx_serialize_extra_data_hash(&tp, tx->extra_data.bytes,
                                        tx->extra_data.size)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize extra data"));
        signing_abort();
        return;
      }
      if (tp.extra_data_received < tp.extra_data_len) {
        // Still some data remaining.
        send_req_2_orig_extradata(
            tp.extra_data_received,
            MIN(1024, tp.extra_data_len - tp.extra_data_received));
      } else {
        phase1_finish();
      }
      return;
#endif
    case STAGE_REQUEST_3_INPUT:
      if (idx1 == 0) {
        hasher_Reset(&info.hasher_check);
      }

      if (!signing_validate_input(tx->inputs)) {
        return;
      }

      if (!tx_input_check_hash(&info.hasher_check, tx->inputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to hash input"));
        signing_abort();
        return;
      }

      if (!tx->inputs[0].has_amount) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Expected input with amount"));
        signing_abort();
        return;
      }

      memcpy(&input, tx->inputs, sizeof(TxInputType));

      if (input.script_type != InputScriptType_EXTERNAL) {
        // External inputs should have scriptPubKey set by the host.
        if (!input_derive_node(&input) || !fill_input_script_pubkey(&input)) {
          return;
        }
      }

      send_req_3_prev_meta();
      return;
    case STAGE_REQUEST_3_PREV_META:
      if (tx->outputs_cnt <= input.prev_index) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Not enough outputs in previous transaction."));
        signing_abort();
        return;
      }
      if (!coin->extra_data && tx->extra_data_len > 0) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Extra data not enabled on this coin."));
        signing_abort();
        return;
      }
      if (!coin->decred && !coin->overwintered && tx->has_expiry) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Expiry not enabled on this coin."));
        signing_abort();
        return;
      }
      if (!coin->timestamp && tx->has_timestamp) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Timestamp not enabled on this coin."));
        signing_abort();
        return;
      }
      if (coin->timestamp && !tx->timestamp) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Timestamp must be set."));
        signing_abort();
        return;
      }
      if (coin->overwintered) {
        if (tx->version >= 3 && !tx->has_version_group_id) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Version group ID must be set when version >= 3."));
          signing_abort();
          return;
        }
        if (tx->version < 3 && tx->has_version_group_id) {
          fsm_sendFailure(
              FailureType_Failure_DataError,
              _("Version group ID must be unset when version < 3."));
          signing_abort();
          return;
        }
      } else {  // !coin->overwintered
        if (tx->has_version_group_id) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Version group ID not enabled on this coin."));
          signing_abort();
          return;
        }
        if (tx->has_branch_id) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Branch ID not enabled on this coin."));
          signing_abort();
          return;
        }
      }
      if (tx->inputs_cnt + tx->outputs_cnt < tx->inputs_cnt) {
        fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
        signing_abort();
        return;
      }
      tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time,
              tx->expiry, tx->branch_id, tx->extra_data_len,
              coin->curve->hasher_sign, coin->overwintered,
              tx->version_group_id, tx->timestamp);
#if !BITCOIN_ONLY
      if (coin->decred) {
        tp.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
        tp.is_decred = true;
      }
#endif
      progress_substeps = tp.inputs_len + tp.outputs_len;
      idx2 = 0;
      if (tp.inputs_len > 0) {
        send_req_3_prev_input();
      } else {
        tx_serialize_header_hash(&tp);
        send_req_3_prev_output();
      }
      return;
    case STAGE_REQUEST_3_PREV_INPUT:
      if (!signing_validate_prev_input(&tx->inputs[0])) {
        return;
      }
      progress_substep++;
      if (!tx_serialize_input_hash(&tp, tx->inputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize input"));
        signing_abort();
        return;
      }
      if (idx2 < tp.inputs_len - 1) {
        idx2++;
        send_req_3_prev_input();
      } else {
        idx2 = 0;
        send_req_3_prev_output();
      }
      return;
    case STAGE_REQUEST_3_PREV_OUTPUT:
      if (!signing_validate_bin_output(&tx->bin_outputs[0])) {
        return;
      }
      progress_substep++;
      if (!tx_serialize_output_hash(&tp, tx->bin_outputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize output"));
        signing_abort();
        return;
      }
      if (idx2 == input.prev_index) {
        if (input.amount != tx->bin_outputs[0].amount) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Invalid amount specified"));
          signing_abort();
          return;
        }
        if (input.script_pubkey.size != tx->bin_outputs[0].script_pubkey.size ||
            memcmp(input.script_pubkey.bytes,
                   tx->bin_outputs[0].script_pubkey.bytes,
                   input.script_pubkey.size) != 0) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Input does not match scriptPubKey"));
          signing_abort();
          return;
        }
#if !BITCOIN_ONLY
        if (coin->decred && tx->bin_outputs[0].decred_script_version > 0) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Decred script version does "
                            "not match previous output"));
          signing_abort();
          return;
        }
#endif
      }
      if (idx2 < tp.outputs_len - 1) {
        /* Check next output of prevtx */
        idx2++;
        send_req_3_prev_output();
#if !BITCOIN_ONLY
      } else if (coin->extra_data && tp.extra_data_len > 0) {  // has extra data
        send_req_3_prev_extradata(0, MIN(1024, tp.extra_data_len));
        return;
#endif
      } else {
        /* prevtx is done */
        if (!signing_check_prevtx_hash()) {
          return;
        }
      }
      return;
#if !BITCOIN_ONLY
    case STAGE_REQUEST_3_PREV_EXTRADATA:
      if (!tx_serialize_extra_data_hash(&tp, tx->extra_data.bytes,
                                        tx->extra_data.size)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize extra data"));
        signing_abort();
        return;
      }
      if (tp.extra_data_received <
          tp.extra_data_len) {  // still some data remaining
        send_req_3_prev_extradata(
            tp.extra_data_received,
            MIN(1024, tp.extra_data_len - tp.extra_data_received));
      } else {
        if (!signing_check_prevtx_hash()) {
          return;
        }
      }
      return;
#endif

    case STAGE_REQUEST_3_ORIG_NONLEGACY_INPUT:
      if (!signing_validate_input(tx->inputs)) {
        return;
      }
      progress_step++;

      // Add input to the outer transaction check.
      if (!tx_input_check_hash(&hasher_check, tx->inputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to hash input"));
        signing_abort();
        return;
      }

      if (!signing_verify_orig_nonlegacy_input(tx->inputs)) {
        return;
      }

      idx1++;
      phase2_request_orig_input();
      return;

    case STAGE_REQUEST_3_ORIG_INPUT:
      if (!signing_validate_input(tx->inputs) ||
          !signing_hash_orig_input(tx->inputs)) {
        return;
      }
      progress_step++;

      idx2++;
      if (idx2 < orig_info.inputs_count) {
        send_req_3_orig_input();
      } else {
        // Ensure that the original transaction inputs haven't changed for the
        // inner transaction check.
        if (!tx_info_check_inputs_hash(&orig_info)) {
          return;
        }

        // Reset the inner transaction check.
        hasher_Reset(&orig_info.hasher_check);
        idx2 = 0;
        send_req_3_orig_output();
      }

      return;

    case STAGE_REQUEST_3_ORIG_OUTPUT:
      if (!signing_validate_output(tx->outputs) ||
          !signing_hash_orig_output(tx->outputs)) {
        return;
      }
      progress_step++;

      idx2++;
      if (idx2 < orig_info.outputs_count) {
        send_req_3_orig_output();
      } else {
        // Ensure that the original transaction outputs haven't changed for the
        // inner transaction check.
        if (!tx_info_check_outputs_hash(&orig_info)) {
          return;
        }

        // Verify original signature.
        if (!signing_verify_orig_legacy_input()) {
          return;
        }

        idx1++;
        phase2_request_orig_input();
      }

      return;

    case STAGE_REQUEST_4_INPUT:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      progress_step++;

      if (idx2 == 0) {
        tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
                info.lock_time, info.expiry, tx->branch_id, 0,
                coin->curve->hasher_sign, coin->overwintered,
                info.version_group_id, info.timestamp);
        hasher_Reset(&info.hasher_check);
      }
      // check inputs are the same as those in phase 1
      if (!tx_input_check_hash(&info.hasher_check, tx->inputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to hash input"));
        signing_abort();
        return;
      }
      if (idx2 == idx1) {
        if (!tx_info_check_input(&info, &tx->inputs[0]) ||
            !input_derive_node(&tx->inputs[0]) ||
            !fill_input_script_sig(&tx->inputs[0])) {
          return;
        }
        memcpy(&input, &tx->inputs[0], sizeof(input));
        memcpy(privkey, node.private_key, 32);
        memcpy(pubkey, node.public_key, 33);
      } else {
        if (info.next_legacy_input == idx1 && idx2 > idx1 &&
            (tx->inputs[0].script_type == InputScriptType_SPENDADDRESS ||
             tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG)) {
          info.next_legacy_input = idx2;
        }
        tx->inputs[0].script_sig.size = 0;
      }
      if (!tx_serialize_input_hash(&ti, tx->inputs)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize input"));
        signing_abort();
        return;
      }
      if (idx2 < info.inputs_count - 1) {
        idx2++;
        send_req_4_input();
      } else {
        if (!tx_info_check_inputs_hash(&info)) {
          return;
        }

        hasher_Reset(&info.hasher_check);
        idx2 = 0;
        send_req_4_output();
      }
      return;
    case STAGE_REQUEST_4_OUTPUT:
      if (!signing_validate_output(&tx->outputs[0])) {
        return;
      }
      progress_step++;

      if (!compile_output(tx->outputs, &bin_output, false)) {
        return;
      }
      //  check hashOutputs
      tx_output_hash(&info.hasher_check, &bin_output, coin->decred);
      if (!tx_serialize_output_hash(&ti, &bin_output)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize output"));
        signing_abort();
        return;
      }
      if (idx2 < info.outputs_count - 1) {
        idx2++;
        send_req_4_output();
      } else {
        if (!tx_info_check_outputs_hash(&info) ||
            !signing_sign_legacy_input()) {
          return;
        }
        signatures++;
        // since this took a longer time, update progress
        report_progress(true);
        phase2_request_next_input(false);
      }
      return;

    case STAGE_REQUEST_NONLEGACY_INPUT:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      progress_step++;

      if (is_external_input(idx1) !=
          (tx->inputs[0].script_type == InputScriptType_EXTERNAL)) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Transaction has changed during signing"));
        signing_abort();
        return;
      }

      resp.has_serialized = true;
      resp.serialized.has_signature_index = false;
      resp.serialized.has_signature = false;
      if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG ||
          tx->inputs[0].script_type == InputScriptType_SPENDADDRESS) {
        if (!(coin->force_bip143 || coin->overwintered) || taproot_only) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Transaction has changed during signing"));
          signing_abort();
          return;
        }
        if (!tx_info_check_input(&info, &tx->inputs[0]) ||
            !input_derive_node(&tx->inputs[0]) ||
            !fill_input_script_sig(&tx->inputs[0])) {
          return;
        }
        if (!tx->inputs[0].has_amount) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Expected input with amount"));
          signing_abort();
          return;
        }

        uint8_t hash[32] = {0};
#if !BITCOIN_ONLY
        if (coin->overwintered) {
          if (info.version == 4) {
            signing_hash_zip243(&info, &tx->inputs[0], hash);
          } else if (info.version == 5) {
            if (!fill_input_script_pubkey(&tx->inputs[0])) {
              return;
            }
            signing_hash_zip244(&info, &tx->inputs[0], hash);
          } else {
            fsm_sendFailure(
                FailureType_Failure_DataError,
                _("Unsupported version for overwintered transaction"));
            signing_abort();
            return;
          }
        } else
#endif
        {
          signing_hash_bip143(&info, &tx->inputs[0], hash);
        }
        if (!signing_sign_ecdsa(&tx->inputs[0], node.private_key,
                                node.public_key, hash))
          return;
        signatures++;
        // since this took a longer time, update progress
        report_progress(true);
      } else if (tx->inputs[0].script_type ==
                     InputScriptType_SPENDP2SHWITNESS &&
                 !tx->inputs[0].has_multisig) {
        if (!tx_info_check_input(&info, &tx->inputs[0]) ||
            !input_derive_node(&tx->inputs[0]) ||
            !fill_input_script_sig(&tx->inputs[0])) {
          return;
        }
        // fixup normal p2pkh script into witness 0 p2wpkh script for p2sh
        // we convert 76 A9 14 <digest> 88 AC  to 16 00 14 <digest>
        // P2SH input pushes witness 0 script
        tx->inputs[0].script_sig.size = 0x17;  // drops last 2 bytes.
        tx->inputs[0].script_sig.bytes[0] =
            0x16;  // push 22 bytes; replaces OP_DUP
        tx->inputs[0].script_sig.bytes[1] =
            0x00;  // witness 0 script ; replaces OP_HASH160
                   // digest is already in right place.
      } else if (tx->inputs[0].script_type ==
                 InputScriptType_SPENDP2SHWITNESS) {
        // Prepare P2SH witness script.
        tx->inputs[0].script_sig.size = 0x23;  // 35 bytes long:
        tx->inputs[0].script_sig.bytes[0] =
            0x22;  // push 34 bytes (full witness script)
        tx->inputs[0].script_sig.bytes[1] = 0x00;  // witness 0 script
        tx->inputs[0].script_sig.bytes[2] = 0x20;  // push 32 bytes (digest)
        // compute digest of multisig script
        if (!compile_script_multisig_hash(coin, &tx->inputs[0].multisig,
                                          tx->inputs[0].script_sig.bytes + 3)) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Failed to compile input"));
          signing_abort();
          return;
        }
      } else if (tx->inputs[0].script_type == InputScriptType_EXTERNAL &&
                 tx->inputs[0].has_script_sig) {
        // use the provided script_sig
      } else {
        // direct witness scripts require zero scriptSig
        tx->inputs[0].script_sig.size = 0;
      }
      if (serialize) {
        resp.has_serialized = true;
        resp.serialized.has_serialized_tx = true;
        resp.serialized.serialized_tx.size = tx_serialize_input(
            &to, &tx->inputs[0], resp.serialized.serialized_tx.bytes);
      }
      phase2_request_next_input(false);
      return;

    case STAGE_REQUEST_5_OUTPUT:
      if (!signing_validate_output(&tx->outputs[0])) {
        return;
      }
      progress_step++;

      if (!compile_output(tx->outputs, &bin_output, false)) {
        return;
      }
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size = tx_serialize_output(
          &to, &bin_output, resp.serialized.serialized_tx.bytes);
      phase2_request_next_output(false);
      return;

    case STAGE_REQUEST_SEGWIT_WITNESS:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      if (!signing_sign_segwit_input(&tx->inputs[0])) {
        return;
      }
      signatures++;
      progress_step++;
      report_progress(true);
      phase2_request_next_witness(false);
      return;

#if !BITCOIN_ONLY

    case STAGE_REQUEST_DECRED_WITNESS:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      if (idx1 == 0) {
        // witness
        tx_init(&to, info.inputs_count, info.outputs_count, info.version,
                info.lock_time, info.expiry, tx->branch_id, 0,
                coin->curve->hasher_sign, coin->overwintered,
                info.version_group_id, info.timestamp);
        to.is_decred = true;
      }

      // witness hash
      tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
              info.lock_time, info.expiry, tx->branch_id, 0,
              coin->curve->hasher_sign, coin->overwintered,
              info.version_group_id, info.timestamp);
      ti.version |= (DECRED_SERIALIZE_WITNESS_SIGNING << 16);
      ti.is_decred = true;
      if (!tx_info_check_input(&info, &tx->inputs[0]) ||
          !input_derive_node(&tx->inputs[0]) ||
          !fill_input_script_sig(&tx->inputs[0])) {
        return;
      }

      for (idx2 = 0; idx2 < info.inputs_count; idx2++) {
        uint32_t r = 0;
        if (idx2 == idx1) {
          r = tx_serialize_decred_witness_hash(&ti, &tx->inputs[0]);
        } else {
          r = tx_serialize_decred_witness_hash(&ti, NULL);
        }

        if (!r) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Failed to serialize input"));
          signing_abort();
          return;
        }
      }

      if (!signing_sign_decred_input(&tx->inputs[0])) {
        return;
      }
      signatures++;
      progress_step++;
      // since this took a longer time, update progress
      report_progress(true);
      if (idx1 < info.inputs_count - 1) {
        idx1++;
        send_req_decred_witness();
      } else {
        send_req_finished();
        signing_abort();
      }
      return;

#endif
  }

  fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing error"));
  signing_abort();
}

void signing_abort(void) {
  if (signing) {
    layoutHome();
    signing = false;
  }
  memzero(&root, sizeof(root));
  memzero(&node, sizeof(node));
}

bool signing_is_preauthorized(void) {
  return signing && (is_coinjoin == sectrue);
}
