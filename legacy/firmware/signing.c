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
#ifdef USE_SECP256K1_ZKP_ECDSA
#include "zkp_ecdsa.h"
#endif

static uint32_t change_count;
static const CoinInfo *coin;
static AmountUnit amount_unit;
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
  STAGE_REQUEST_4_INPUT,
  STAGE_REQUEST_4_OUTPUT,
  STAGE_REQUEST_SEGWIT_INPUT,
  STAGE_REQUEST_5_OUTPUT,
  STAGE_REQUEST_SEGWIT_WITNESS,
#if !BITCOIN_ONLY
  STAGE_REQUEST_DECRED_WITNESS,
#endif
} signing_stage;
static uint32_t idx1;  // The index of the input or output in the current tx
                       // which is being processed, signed or serialized.
static uint32_t idx2;  // The index of the input or output in the original tx
                       // (Phase 1), in the previous tx (Phase 2) or in the
                       // current tx when computing the legacy digest (Phase 2).
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
static uint8_t hash_inputs_check[32];
static uint64_t total_in, total_out, change_out;
static uint64_t orig_total_in, orig_total_out, orig_change_out;
static uint32_t next_nonsegwit_input;
static uint32_t progress, progress_step, progress_meta_step;
static uint32_t tx_weight;

typedef struct {
  uint32_t inputs_count;
  uint32_t outputs_count;
  uint32_t min_sequence;
  bool multisig_fp_set;
  bool multisig_fp_mismatch;
  uint8_t multisig_fp[32];
  uint32_t in_address_n[8];
  size_t in_address_n_count;
  uint32_t version;
  uint32_t lock_time;
  uint32_t expiry;
  uint32_t version_group_id;
  uint32_t timestamp;
#if !BITCOIN_ONLY
  uint32_t branch_id;
#endif
  Hasher hasher_prevouts;
  Hasher hasher_sequence;
  Hasher hasher_outputs;
  uint8_t hash_prevouts[32];
  uint8_t hash_sequence[32];
  uint8_t hash_outputs[32];
} TxInfo;

static TxInfo info;

/* Variables specific to replacement transactions. */
static bool is_replacement;           // Is this a replacement transaction?
static bool have_orig_verif_input;    // Is orig_verif_input, sig and node set?
static TxInputType orig_verif_input;  // The input for signature verification.
static TxInfo orig_info;
static uint8_t orig_hash[32];  // TXID of the original transaction.

/* A marker for in_address_n_count to indicate a mismatch in bip32 paths in
   input */
#define BIP32_NOCHANGEALLOWED 1
/* The number of bip32 levels used in a wallet (chain and address) */
#define BIP32_WALLET_DEPTH 2
/* The chain id used for change */
#define BIP32_CHANGE_CHAIN 1
/* The maximum allowed change address.  This should be large enough for normal
   use and still allow to quickly brute-force the correct bip32 path. */
#define BIP32_MAX_LAST_ELEMENT 1000000

/* transaction header size: 4 byte version */
#define TXSIZE_HEADER 4
/* transaction footer size: 4 byte lock time */
#define TXSIZE_FOOTER 4
/* transaction segwit overhead 2 marker */
#define TXSIZE_SEGWIT_OVERHEAD 2

/* The maximum number of change-outputs allowed without user confirmation. */
#define MAX_SILENT_CHANGE_COUNT 2

/* Setting nSequence to this value for every input in a transaction disables
   nLockTime. */
#define SEQUENCE_FINAL 0xffffffff

/* Setting nSequence to a value greater than this for every input in a
   transaction disables replace-by-fee opt-in. */
#define MAX_BIP125_RBF_SEQUENCE 0xFFFFFFFD

enum {
  SIGHASH_ALL = 1,
  SIGHASH_FORKID = 0x40,
};

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

foreach I (idx1):
    Request I                                                 STAGE_REQUEST_1_INPUT
    Add I to segwit hash_prevouts, hash_sequence
    Add I to Decred decred_hash_prefix
    Add I to TransactionChecksum (prevout and type)
    if (I has orig_hash)
        Request input I2 orig_hash, orig_index                STAGE_REQUEST_1_ORIG_INPUT
        Check I matches I2
        Add I2 to orig_hash_prevouts, orig_hash_sequence
    if (Decred)
        Return I

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

Phase2: sign inputs, check that nothing changed
===============================================

if (Decred)
    Skip to STAGE_REQUEST_DECRED_WITNESS

foreach I (idx1):  // input to sign
    if (idx1 is segwit)
        Request I                                             STAGE_REQUEST_SEGWIT_INPUT
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
  resp.details.tx_hash.size = input.orig_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.orig_hash.bytes,
         resp.details.tx_hash.size);
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
  resp.details.tx_hash.size = input.orig_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.orig_hash.bytes,
         resp.details.tx_hash.size);
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
  resp.details.tx_hash.size = output.orig_hash.size;
  memcpy(resp.details.tx_hash.bytes, output.orig_hash.bytes,
         resp.details.tx_hash.size);
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

void send_req_segwit_input(void) {
  signing_stage = STAGE_REQUEST_SEGWIT_INPUT;
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
  resp.has_request_type = true;
  resp.request_type = RequestType_TXFINISHED;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void phase1_request_next_input(void) {
  if (idx1 < info.inputs_count - 1) {
    idx1++;
    send_req_1_input();
  } else {
    hasher_Final(&hasher_check, hash_inputs_check);
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

void phase2_request_next_input(void) {
  if (idx1 == next_nonsegwit_input) {
    idx2 = 0;
    send_req_4_input();
  } else {
    send_req_segwit_input();
  }
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
          toutput->address_n[count - 2] <= BIP32_CHANGE_CHAIN &&
          toutput->address_n[count - 1] <= BIP32_MAX_LAST_ELEMENT);
}

static bool fill_input_script_sig(TxInputType *tinput) {
  memcpy(&node, &root, sizeof(HDNode));
  if (hdnode_private_ckd_cached(&node, tinput->address_n,
                                tinput->address_n_count, NULL) == 0) {
    // Failed to derive private key
    return false;
  }
  if (hdnode_fill_public_key(&node) != 0) {
    // Failed to derive public key
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
  return tinput->script_sig.size > 0;
}

bool compile_input_script_sig(TxInputType *tinput) {
  if (!info.multisig_fp_mismatch) {
    // check that this is still multisig
    uint8_t h[32] = {0};
    if (!tinput->has_multisig ||
        cryptoMultisigFingerprint(&(tinput->multisig), h) == 0 ||
        memcmp(info.multisig_fp, h, 32) != 0) {
      // Transaction has changed during signing
      return false;
    }
  }
  if (info.in_address_n_count != BIP32_NOCHANGEALLOWED) {
    // check that input address didn't change
    size_t count = tinput->address_n_count;
    if (count < 2 || count != info.in_address_n_count ||
        0 != memcmp(info.in_address_n, tinput->address_n,
                    (count - 2) * sizeof(uint32_t))) {
      return false;
    }
  }
  if (!coin_path_check(coin, tinput->script_type, tinput->address_n_count,
                       tinput->address_n, tinput->has_multisig,
                       CoinPathCheckLevel_BASIC)) {
    if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
      return false;
    }

    layoutDialogSwipe(&bmp_icon_warning, _("Abort"), _("Continue"), NULL,
                      _("Wrong address path"), _("for selected coin."), NULL,
                      _("Continue at your"), _("own risk!"), NULL);
    if (!protectButton(ButtonRequestType_ButtonRequest_UnknownDerivationPath,
                       false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return false;
    }
  }
  return fill_input_script_sig(tinput);
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
  tx_info->min_sequence = SEQUENCE_FINAL;
  tx_info->multisig_fp_set = false;
  tx_info->multisig_fp_mismatch = false;
  tx_info->in_address_n_count = 0;
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

    if (tx_info->version != 4) {
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

#if !BITCOIN_ONLY
  if (coin->overwintered) {
    // ZIP-243
    hasher_InitParam(&tx_info->hasher_prevouts, HASHER_BLAKE2B_PERSONAL,
                     "ZcashPrevoutHash", 16);
    hasher_InitParam(&tx_info->hasher_sequence, HASHER_BLAKE2B_PERSONAL,
                     "ZcashSequencHash", 16);
    hasher_InitParam(&tx_info->hasher_outputs, HASHER_BLAKE2B_PERSONAL,
                     "ZcashOutputsHash", 16);
  } else
#endif
  {
    // BIP-143
    hasher_Init(&tx_info->hasher_prevouts, coin->curve->hasher_sign);
    hasher_Init(&tx_info->hasher_sequence, coin->curve->hasher_sign);
    hasher_Init(&tx_info->hasher_outputs, coin->curve->hasher_sign);
  }

  return true;
}

void signing_init(const SignTx *msg, const CoinInfo *_coin,
                  const HDNode *_root) {
  coin = _coin;
  amount_unit = msg->has_amount_unit ? msg->amount_unit : AmountUnit_BITCOIN;
  memcpy(&root, _root, sizeof(HDNode));

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

  tx_weight = 4 * size;

  signatures = 0;
  idx1 = 0;
  total_in = 0;
  total_out = 0;
  change_out = 0;
  change_count = 0;
  orig_total_in = 0;
  orig_total_out = 0;
  orig_change_out = 0;
  memzero(&input, sizeof(TxInputType));
  memzero(&output, sizeof(TxOutputType));
  memzero(&resp, sizeof(TxRequest));
  is_replacement = false;
  have_orig_verif_input = false;
  signing = true;
  progress = 0;
  // we step by 500/inputs_count per input in phase1 and phase2
  // this means 50 % per phase.
  progress_step = (500 << PROGRESS_PRECISION) / info.inputs_count;

  next_nonsegwit_input = 0xffffffff;

  tx_init(&to, info.inputs_count, info.outputs_count, info.version,
          info.lock_time, info.expiry, 0, coin->curve->hasher_sign,
          coin->overwintered, info.version_group_id, info.timestamp);

#if !BITCOIN_ONLY
  if (coin->decred) {
    to.version |= (DECRED_SERIALIZE_FULL << 16);
    to.is_decred = true;

    tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
            info.lock_time, info.expiry, 0, coin->curve->hasher_sign,
            coin->overwintered, info.version_group_id, info.timestamp);
    ti.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
    ti.is_decred = true;
  }
#endif

  hasher_Init(&hasher_check, coin->curve->hasher_sign);

  layoutProgressSwipe(_("Signing transaction"), 0);

  send_req_1_input();
}

#define MIN(a, b) (((a) < (b)) ? (a) : (b))

static bool is_multisig_input_script_type(const TxInputType *txinput) {
  if (txinput->script_type == InputScriptType_SPENDMULTISIG ||
      txinput->script_type == InputScriptType_SPENDP2SHWITNESS ||
      txinput->script_type == InputScriptType_SPENDWITNESS) {
    return true;
  }
  return false;
}

static bool is_multisig_output_script_type(const TxOutputType *txoutput) {
  if (txoutput->script_type == OutputScriptType_PAYTOMULTISIG ||
      txoutput->script_type == OutputScriptType_PAYTOP2SHWITNESS ||
      txoutput->script_type == OutputScriptType_PAYTOWITNESS) {
    return true;
  }
  return false;
}

static bool is_internal_input_script_type(const TxInputType *txinput) {
  if (txinput->script_type == InputScriptType_SPENDADDRESS ||
      txinput->script_type == InputScriptType_SPENDMULTISIG ||
      txinput->script_type == InputScriptType_SPENDP2SHWITNESS ||
      txinput->script_type == InputScriptType_SPENDWITNESS) {
    return true;
  }
  return false;
}

static bool is_change_output_script_type(const TxOutputType *txoutput) {
  if (txoutput->script_type == OutputScriptType_PAYTOADDRESS ||
      txoutput->script_type == OutputScriptType_PAYTOMULTISIG ||
      txoutput->script_type == OutputScriptType_PAYTOP2SHWITNESS ||
      txoutput->script_type == OutputScriptType_PAYTOWITNESS) {
    return true;
  }
  return false;
}

static bool is_segwit_input_script_type(const TxInputType *txinput) {
  if (txinput->script_type == InputScriptType_SPENDP2SHWITNESS ||
      txinput->script_type == InputScriptType_SPENDWITNESS) {
    return true;
  }
  return false;
}

static bool signing_validate_input(const TxInputType *txinput) {
  if (txinput->prev_hash.size != 32) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Encountered invalid prevhash"));
    signing_abort();
    return false;
  }

  if (txinput->has_multisig && !is_multisig_input_script_type(txinput)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Multisig field provided but not expected."));
    signing_abort();
    return false;
  }

  if (txinput->address_n_count > 0 && !is_internal_input_script_type(txinput)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    "Input's address_n provided but not expected.");
    signing_abort();
    return false;
  }

  if (is_segwit_input_script_type(txinput)) {
    if (!coin->has_segwit) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Segwit not enabled on this coin"));
      signing_abort();
      return false;
    }
  }

  if (txinput->has_orig_hash) {
    if (!txinput->has_orig_index) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing orig_index field."));
      signing_abort();
      return false;
    }

    if (txinput->orig_hash.size != 32) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Encountered invalid orig_hash"));
      signing_abort();
      return false;
    }
  }

  return true;
}

static bool signing_validate_output(TxOutputType *txoutput) {
  if (txoutput->has_multisig && !is_multisig_output_script_type(txoutput)) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Multisig field provided but not expected."));
    signing_abort();
    return false;
  }

  if (txoutput->address_n_count > 0 &&
      !is_change_output_script_type(txoutput)) {
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
  // Compute multisig fingerprint for change-output detection. In order for an
  // output to be considered a change-output, it must have the same fingerprint
  // as all inputs.
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

  // Remember the input's BIP-32 path. Change-outputs must use the same path
  // as all inputs.
  extract_input_bip32_path(tx_info, txinput);

  // Remember the minimum nSequence value.
  if (txinput->sequence < tx_info->min_sequence) {
    tx_info->min_sequence = txinput->sequence;
  }

  // Add input to BIP-143 hashPrevouts and hashSequence.
  tx_prevout_hash(&tx_info->hasher_prevouts, txinput);
  tx_sequence_hash(&tx_info->hasher_sequence, txinput);

  return true;
}

static bool tx_info_add_output(TxInfo *tx_info,
                               const TxOutputBinType *tx_bin_output) {
  // Add output to BIP-143 hashOutputs.
  tx_output_hash(&tx_info->hasher_outputs, tx_bin_output, coin->decred);
  return true;
}

static void tx_info_finish(TxInfo *tx_info) {
  hasher_Final(&tx_info->hasher_prevouts, tx_info->hash_prevouts);
  hasher_Final(&tx_info->hasher_sequence, tx_info->hash_sequence);
  hasher_Final(&tx_info->hasher_outputs, tx_info->hash_outputs);
}

static bool signing_check_input(const TxInputType *txinput) {
  // Add input to BIP143 computation.
  if (!tx_info_add_input(&info, txinput)) {
    return false;
  }

#if !BITCOIN_ONLY
  if (coin->decred) {
    // serialize Decred prefix in Phase 1
    resp.has_serialized = true;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.size =
        tx_serialize_input(&to, txinput, resp.serialized.serialized_tx.bytes);

    // compute Decred hashPrefix
    tx_serialize_input_hash(&ti, txinput);
  }
#endif
  // hash all input data to check it later (relevant for fee computation)
  tx_input_check_hash(&hasher_check, txinput);
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

  if (idx1 < info.inputs_count - 1) {
    idx1++;
    send_req_3_input();
  } else {
    hasher_Final(&hasher_check, hash);
    if (memcmp(hash, hash_inputs_check, 32) != 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Transaction has changed during signing"));
      signing_abort();
      return false;
    }

    // Everything was checked, now phase 2 begins and the transaction is signed.
    progress_meta_step =
        progress_step / (info.inputs_count + info.outputs_count);
    layoutProgress(_("Signing transaction"), progress);
    idx1 = 0;
#if !BITCOIN_ONLY
    if (coin->decred) {
      // Decred prefix serialized in Phase 1, skip Phase 2
      send_req_decred_witness();
    } else
#endif
    {
      phase2_request_next_input();
    }
  }

  return true;
}

static bool is_change_output(const TxInfo *tx_info,
                             const TxOutputType *txoutput) {
  if (!is_change_output_script_type(txoutput)) {
    return false;
  }

  if (txoutput->address_n_count == 0) {
    return false;
  }

  /*
   * For multisig check that all inputs are multisig
   */
  if (txoutput->has_multisig) {
    uint8_t h[32] = {0};
    if (!tx_info->multisig_fp_set || tx_info->multisig_fp_mismatch ||
        !cryptoMultisigFingerprint(&(txoutput->multisig), h) ||
        memcmp(tx_info->multisig_fp, h, 32) != 0) {
      return false;
    }
  }

  return check_change_bip32_path(tx_info, txoutput);
}

static bool signing_check_output(TxOutputType *txoutput) {
  // Phase1: Check outputs
  //   add it to hash_outputs
  //   ask user for permission

  bool is_change = is_change_output(&info, txoutput);

  // Don't allow adding new external outputs in replacement transactions. There
  // is actually nothing wrong with adding new external outputs, but the only
  // way to pay for them would be by supplying a new external input, which is
  // currently not supported.
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

  // Skip confirmation of change-outputs and skip output confirmation altogether
  // in replacement transactions.
  bool skip_confirm = is_change || is_replacement;
  int co = compile_output(coin, amount_unit, &root, txoutput, &bin_output,
                          !skip_confirm);
  if (!skip_confirm) {
    layoutProgress(_("Signing transaction"), progress);
  }
  if (co < 0) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    signing_abort();
    return false;
  } else if (co == 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to compile output"));
    signing_abort();
    return false;
  }
#if !BITCOIN_ONLY
  if (coin->decred) {
    // serialize Decred prefix in Phase 1
    resp.has_serialized = true;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.size = tx_serialize_output(
        &to, &bin_output, resp.serialized.serialized_tx.bytes);

    // compute Decred hashPrefix
    tx_serialize_output_hash(&ti, &bin_output);
  }
#endif
  // Add output to BIP143 computation.
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

  // Decode the DER-encoded signature and store in sig.
  if (bytes[size - 1] != SIGHASH_ALL ||
      ecdsa_sig_from_der(bytes, size - 1, sig) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Unsupported signature script."));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_check_orig_input(TxInputType *orig_input) {
  // Verify that the original input matches the current input.
  // An input is characterized by its prev_hash and prev_index. We also
  // check that the amounts match, so that we don't have to stream the
  // prevtx twice for the same prevtx output. Verifying that script_type
  // matches is just a sanity check.
  if (orig_input->prev_hash.size != input.prev_hash.size ||
      memcmp(orig_input->prev_hash.bytes, input.prev_hash.bytes,
             input.prev_hash.size) != 0 ||
      orig_input->prev_index != input.prev_index ||
      orig_input->amount != input.amount ||
      orig_input->script_type != input.script_type) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Original input does not match current input."));
    signing_abort();
    return false;
  }

  // Add input to original BIP143 computation.
  if (!tx_info_add_input(&orig_info, orig_input)) {
    return false;
  }

  if (!add_amount(&orig_total_in, orig_input->amount)) {
    return false;
  }

  // Add input to original TXID computation before script_sig is overwritten.
  if (!tx_serialize_input_hash(&tp, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize input"));
    signing_abort();
    return false;
  }

  // The first original input that has address_n set and a signature gets chosen
  // as the verification input. Set script_sig for legacy digest computation.
  if (!have_orig_verif_input && orig_input->address_n_count != 0 &&
      !orig_input->has_multisig &&
      ((orig_input->has_script_sig && orig_input->script_sig.size != 0) ||
       (orig_input->has_witness && orig_input->witness.size > 1))) {
    // Save the signature before script_sig is overwritten.
    if (!save_signature(orig_input)) {
      return false;
    }

    // Derive node.public_key and fill script_sig with the legacy scriptPubKey
    // (aka BIP-143 script code), which is what our code expects here in order
    // to properly compute the legacy transaction digest or BIP-143 transaction
    // digest.
    if (!fill_input_script_sig(orig_input)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to derive public key."));
      signing_abort();
      return false;
    }

    // Save the verification input with script_sig set to scriptPubKey.
    memcpy(&orig_verif_input, orig_input, sizeof(TxInputType));
    have_orig_verif_input = true;
  } else {
    orig_input->script_sig.size = 0;
  }

  // Add input to original legacy digest computation now that script_sig is set.
  if (!tx_serialize_input_hash(&ti, orig_input)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to serialize input"));
    signing_abort();
    return false;
  }

  return true;
}

static bool signing_check_orig_output(TxOutputType *orig_output) {
  // Compute scriptPubKey.
  TxOutputBinType orig_bin_output;
  if (compile_output(coin, amount_unit, &root, orig_output, &orig_bin_output,
                     false) <= 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to compile output"));
    signing_abort();
    return false;
  }

  // Add output to original BIP143 computation.
  if (!tx_info_add_output(&orig_info, &orig_bin_output)) {
    return false;
  }

  // Add output to the original legacy digest computation (ti) and to the
  // original TXID computation (tp).
  if (!tx_serialize_output_hash(&ti, &orig_bin_output) ||
      !tx_serialize_output_hash(&tp, &orig_bin_output)) {
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
        // by supplying an external input. However, external inputs are
        // currently not supported.
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

static bool signing_confirm_tx(void) {
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

    // Sanity check. Replacement transactions are only allowed to make
    // amendments which do not increase the amount that we are spending on
    // external outputs. Additional funds can only go towards the fee, which is
    // confirmed by the user. The check may fail if the replacement transaction
    // starts mixing accounts and breaks change-output identification.
    if (total_out - change_out > orig_total_out - orig_change_out) {
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
      layoutConfirmModifyFee(coin, amount_unit, orig_fee, fee);
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
    layoutConfirmTx(coin, amount_unit, total_in, total_out, change_out);
    if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      signing_abort();
      return false;
    }
  }

  return true;
}

static uint32_t signing_hash_type(void) {
  uint32_t hash_type = SIGHASH_ALL;

  if (coin->has_fork_id) {
    hash_type |= (coin->fork_id << 8) | SIGHASH_FORKID;
  }

  return hash_type;
}

static void signing_hash_bip143(const TxInfo *tx_info,
                                const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
  Hasher hasher_preimage = {0};
  hasher_Init(&hasher_preimage, coin->curve->hasher_sign);

  // nVersion
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->version, 4);
  // hashPrevouts
  hasher_Update(&hasher_preimage, tx_info->hash_prevouts, 32);
  // hashSequence
  hasher_Update(&hasher_preimage, tx_info->hash_sequence, 32);
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
  hasher_Update(&hasher_preimage, tx_info->hash_outputs, 32);
  // nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->lock_time, 4);
  // nHashType
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);

  hasher_Final(&hasher_preimage, hash);
}

#if !BITCOIN_ONLY
static void signing_hash_zip243(const TxInfo *tx_info,
                                const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
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
  hasher_Update(&hasher_preimage, tx_info->hash_sequence, 32);
  // 5. hashOutputs
  hasher_Update(&hasher_preimage, tx_info->hash_outputs, 32);
  // 6. hashJoinSplits
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  // 7. hashShieldedSpends
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  // 8. hashShieldedOutputs
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  // 9. nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->lock_time, 4);
  // 10. expiryHeight
  hasher_Update(&hasher_preimage, (const uint8_t *)&tx_info->expiry, 4);
  // 11. valueBalance
  hasher_Update(&hasher_preimage,
                (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00", 8);
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

  if (!have_orig_verif_input) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("The original transaction must specify address_n for at "
                      "least one input."));
    signing_abort();
    return false;
  }

  // Compute the signed digest.
#if !BITCOIN_ONLY
  if (coin->overwintered) {
    tx_info_finish(&orig_info);
    signing_hash_zip243(&orig_info, &orig_verif_input, hash);
  } else
#endif
  {
    if (is_segwit_input_script_type(&orig_verif_input) || coin->force_bip143) {
      tx_info_finish(&orig_info);
      signing_hash_bip143(&orig_info, &orig_verif_input, hash);
    } else {
      // Finalize legacy digest computation.
      uint32_t hash_type = signing_hash_type();
      hasher_Update(&ti.hasher, (const uint8_t *)&hash_type, 4);
      tx_hash_final(&ti, hash, false);
    }
  }

  int ret = 0;
#ifdef USE_SECP256K1_ZKP_ECDSA
  if (coin->curve->params == &secp256k1) {
    ret = zkp_ecdsa_verify_digest(coin->curve->params, node.public_key, sig,
                                  hash);
  } else
#endif
  {
    ret = ecdsa_verify_digest(coin->curve->params, node.public_key, sig, hash);
  }
  if (ret != 0) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature."));
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

  // Compute BIP143 hashPrevouts, hashSequence and hashOutputs.
  tx_info_finish(&info);

  if (is_replacement) {
    if (!signing_check_orig_tx()) {
      return;
    }
  }

  if (!signing_confirm_tx()) {
    return;
  }

  send_req_3_input();
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
static void signing_hash_decred(const uint8_t *hash_witness, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
  Hasher hasher_preimage = {0};
  hasher_Init(&hasher_preimage, coin->curve->hasher_sign);
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);
  hasher_Update(&hasher_preimage, decred_hash_prefix, 32);
  hasher_Update(&hasher_preimage, hash_witness, 32);
  hasher_Final(&hasher_preimage, hash);
}
#endif

static bool signing_sign_hash(TxInputType *txinput, const uint8_t *private_key,
                              const uint8_t *public_key, const uint8_t *hash) {
  resp.serialized.has_signature_index = true;
  resp.serialized.signature_index = idx1;
  resp.serialized.has_signature = true;
  resp.serialized.has_serialized_tx = true;

  int ret = 0;
#ifdef USE_SECP256K1_ZKP_ECDSA
  if (coin->curve->params == &secp256k1) {
    ret = zkp_ecdsa_sign_digest(coin->curve->params, private_key, hash, sig,
                                NULL, NULL);
  } else
#endif
  {
    ret = ecdsa_sign_digest(coin->curve->params, private_key, hash, sig, NULL,
                            NULL);
  }
  if (ret != 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Signing failed"));
    signing_abort();
    return false;
  }

  resp.serialized.signature.size =
      ecdsa_sig_to_der(sig, resp.serialized.signature.bytes);

  uint8_t sighash = signing_hash_type() & 0xff;
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

static bool signing_sign_input(void) {
  uint8_t hash[32] = {0};
  hasher_Final(&hasher_check, hash);
  if (memcmp(hash, info.hash_outputs, 32) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Transaction has changed during signing"));
    signing_abort();
    return false;
  }

  uint32_t hash_type = signing_hash_type();
  hasher_Update(&ti.hasher, (const uint8_t *)&hash_type, 4);
  tx_hash_final(&ti, hash, false);
  resp.has_serialized = true;
  if (!signing_sign_hash(&input, privkey, pubkey, hash)) return false;
  resp.serialized.serialized_tx.size =
      tx_serialize_input(&to, &input, resp.serialized.serialized_tx.bytes);
  return true;
}

static bool signing_sign_segwit_input(TxInputType *txinput) {
  // idx1: index to sign
  uint8_t hash[32] = {0};

  if (is_segwit_input_script_type(txinput)) {
    if (!txinput->has_amount) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Segwit input without amount"));
      signing_abort();
      return false;
    }
    if (!compile_input_script_sig(txinput)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to compile input"));
      signing_abort();
      return false;
    }

    signing_hash_bip143(&info, txinput, hash);

    resp.has_serialized = true;
    if (!signing_sign_hash(txinput, node.private_key, node.public_key, hash))
      return false;

    uint8_t sighash = signing_hash_type() & 0xff;
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
      uint32_t r = 0;
      r += ser_length(2, resp.serialized.serialized_tx.bytes + r);
      resp.serialized.signature.bytes[resp.serialized.signature.size] = sighash;
      r += tx_serialize_script(resp.serialized.signature.size + 1,
                               resp.serialized.signature.bytes,
                               resp.serialized.serialized_tx.bytes + r);
      r += tx_serialize_script(33, node.public_key,
                               resp.serialized.serialized_tx.bytes + r);
      resp.serialized.serialized_tx.size = r;
    }
  } else {
    // empty witness
    resp.has_serialized = true;
    resp.serialized.has_signature_index = false;
    resp.serialized.has_signature = false;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.bytes[0] = 0;
    resp.serialized.serialized_tx.size = 1;
  }
  //  if last witness add tx footer
  if (idx1 == info.inputs_count - 1) {
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
  signing_hash_decred(hash_witness, hash);
  resp.has_serialized = true;
  if (!signing_sign_hash(txinput, node.private_key, node.public_key, hash))
    return false;
  resp.serialized.serialized_tx.size = tx_serialize_decred_witness(
      &to, txinput, resp.serialized.serialized_tx.bytes);
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

  static int update_ctr = 0;
  if (update_ctr++ == 20) {
    layoutProgress(_("Signing transaction"), progress);
    update_ctr = 0;
  }

  memzero(&resp, sizeof(TxRequest));

  switch (signing_stage) {
    case STAGE_REQUEST_1_INPUT:
      if (!signing_validate_input(&tx->inputs[0]) ||
          !signing_check_input(&tx->inputs[0])) {
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

      tx_weight += tx_input_weight(coin, &tx->inputs[0]);
#if !BITCOIN_ONLY
      if (coin->decred) {
        tx_weight += tx_decred_witness_weight(&tx->inputs[0]);
      }
#endif

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
          if (next_nonsegwit_input == 0xffffffff) next_nonsegwit_input = idx1;
        }
      } else if (is_segwit_input_script_type(&tx->inputs[0])) {
        if (!to.is_segwit) {
          tx_weight += TXSIZE_SEGWIT_OVERHEAD + to.inputs_len;
        }
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
      } else {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Wrong input script type"));
        signing_abort();
        return;
      }

      if (tx->inputs[0].has_orig_hash) {
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

      // Initialize computation of original legacy digest.
      tx_init(&ti, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time,
              tx->expiry, 0, coin->curve->hasher_sign, coin->overwintered,
              tx->version_group_id, tx->timestamp);

      // Initialize computation of original TXID.
      tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time,
              tx->expiry, tx->extra_data_len, coin->curve->hasher_sign,
              coin->overwintered, tx->version_group_id, tx->timestamp);

      phase1_request_orig_input();
      return;
    case STAGE_REQUEST_1_ORIG_INPUT:
      if (!signing_validate_input(tx->inputs) ||
          !signing_check_orig_input(tx->inputs)) {
        return;
      }

      idx2++;
      phase1_request_next_input();
      return;
    case STAGE_REQUEST_2_OUTPUT:
      if (!signing_validate_output(&tx->outputs[0]) ||
          !signing_check_output(&tx->outputs[0])) {
        return;
      }
      tx_weight += tx_output_weight(coin, &tx->outputs[0]);

      if (tx->outputs[0].has_orig_hash) {
        memcpy(&output, &tx->outputs[0], sizeof(output));
        phase1_request_orig_output();
      } else {
        phase1_request_next_output();
      }
      return;
    case STAGE_REQUEST_2_ORIG_OUTPUT:
      if (!signing_validate_output(tx->outputs) ||
          !signing_check_orig_output(tx->outputs)) {
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
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }

      if (!tx->inputs[0].has_amount) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Expected input with amount"));
        signing_abort();
        return;
      }

      if (idx1 == 0) {
        hasher_Reset(&hasher_check);
      }
      tx_input_check_hash(&hasher_check, tx->inputs);

      memcpy(&input, tx->inputs, sizeof(TxInputType));

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
              tx->expiry, tx->extra_data_len, coin->curve->hasher_sign,
              coin->overwintered, tx->version_group_id, tx->timestamp);
#if !BITCOIN_ONLY
      if (coin->decred) {
        tp.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
        tp.is_decred = true;
      }
#endif
      progress_meta_step = progress_step / (tp.inputs_len + tp.outputs_len);
      idx2 = 0;
      if (tp.inputs_len > 0) {
        send_req_3_prev_input();
      } else {
        tx_serialize_header_hash(&tp);
        send_req_3_prev_output();
      }
      return;
    case STAGE_REQUEST_3_PREV_INPUT:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      progress = (idx1 * progress_step + idx2 * progress_meta_step) >>
                 PROGRESS_PRECISION;
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
      progress = (idx1 * progress_step +
                  (tp.inputs_len + idx2) * progress_meta_step) >>
                 PROGRESS_PRECISION;
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
        /* Check prevtx of next input */
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
    case STAGE_REQUEST_4_INPUT:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      progress =
          500 + ((signatures * progress_step + idx2 * progress_meta_step) >>
                 PROGRESS_PRECISION);
      if (idx2 == 0) {
        tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
                info.lock_time, info.expiry, 0, coin->curve->hasher_sign,
                coin->overwintered, info.version_group_id, info.timestamp);
        hasher_Reset(&hasher_check);
      }
      // check inputs are the same as those in phase 1
      tx_input_check_hash(&hasher_check, tx->inputs);
      if (idx2 == idx1) {
        if (!compile_input_script_sig(&tx->inputs[0])) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Failed to compile input"));
          signing_abort();
          return;
        }
        memcpy(&input, &tx->inputs[0], sizeof(input));
        memcpy(privkey, node.private_key, 32);
        memcpy(pubkey, node.public_key, 33);
      } else {
        if (next_nonsegwit_input == idx1 && idx2 > idx1 &&
            (tx->inputs[0].script_type == InputScriptType_SPENDADDRESS ||
             tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG)) {
          next_nonsegwit_input = idx2;
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
        uint8_t hash[32] = {0};
        hasher_Final(&hasher_check, hash);
        if (memcmp(hash, hash_inputs_check, 32) != 0) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Transaction has changed during signing"));
          signing_abort();
          return;
        }
        hasher_Reset(&hasher_check);
        idx2 = 0;
        send_req_4_output();
      }
      return;
    case STAGE_REQUEST_4_OUTPUT:
      if (!signing_validate_output(&tx->outputs[0])) {
        return;
      }
      progress = 500 + ((signatures * progress_step +
                         (info.inputs_count + idx2) * progress_meta_step) >>
                        PROGRESS_PRECISION);
      if (compile_output(coin, amount_unit, &root, tx->outputs, &bin_output,
                         false) <= 0) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to compile output"));
        signing_abort();
        return;
      }
      //  check hashOutputs
      tx_output_hash(&hasher_check, &bin_output, coin->decred);
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
        if (!signing_sign_input()) {
          return;
        }
        // since this took a longer time, update progress
        signatures++;
        progress = 500 + ((signatures * progress_step) >> PROGRESS_PRECISION);
        layoutProgress(_("Signing transaction"), progress);
        update_ctr = 0;
        if (idx1 < info.inputs_count - 1) {
          idx1++;
          phase2_request_next_input();
        } else {
          idx1 = 0;
          send_req_5_output();
        }
      }
      return;

    case STAGE_REQUEST_SEGWIT_INPUT:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      resp.has_serialized = true;
      resp.serialized.has_signature_index = false;
      resp.serialized.has_signature = false;
      resp.serialized.has_serialized_tx = true;
      if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG ||
          tx->inputs[0].script_type == InputScriptType_SPENDADDRESS) {
        if (!(coin->force_bip143 || coin->overwintered)) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Transaction has changed during signing"));
          signing_abort();
          return;
        }
        if (!compile_input_script_sig(&tx->inputs[0])) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Failed to compile input"));
          signing_abort();
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
          if (info.version != 4) {
            fsm_sendFailure(
                FailureType_Failure_DataError,
                _("Unsupported version for overwintered transaction"));
            signing_abort();
            return;
          }
          signing_hash_zip243(&info, &tx->inputs[0], hash);
        } else
#endif
        {
          signing_hash_bip143(&info, &tx->inputs[0], hash);
        }
        if (!signing_sign_hash(&tx->inputs[0], node.private_key,
                               node.public_key, hash))
          return;
        // since this took a longer time, update progress
        signatures++;
        progress = 500 + ((signatures * progress_step) >> PROGRESS_PRECISION);
        layoutProgress(_("Signing transaction"), progress);
        update_ctr = 0;
      } else if (tx->inputs[0].script_type ==
                     InputScriptType_SPENDP2SHWITNESS &&
                 !tx->inputs[0].has_multisig) {
        if (!compile_input_script_sig(&tx->inputs[0])) {
          fsm_sendFailure(FailureType_Failure_ProcessError,
                          _("Failed to compile input"));
          signing_abort();
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
      } else {
        // direct witness scripts require zero scriptSig
        tx->inputs[0].script_sig.size = 0;
      }
      resp.serialized.serialized_tx.size = tx_serialize_input(
          &to, &tx->inputs[0], resp.serialized.serialized_tx.bytes);
      if (idx1 < info.inputs_count - 1) {
        idx1++;
        phase2_request_next_input();
      } else {
        idx1 = 0;
        send_req_5_output();
      }
      return;

    case STAGE_REQUEST_5_OUTPUT:
      if (!signing_validate_output(&tx->outputs[0])) {
        return;
      }
      if (compile_output(coin, amount_unit, &root, tx->outputs, &bin_output,
                         false) <= 0) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to compile output"));
        signing_abort();
        return;
      }
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size = tx_serialize_output(
          &to, &bin_output, resp.serialized.serialized_tx.bytes);
      if (idx1 < info.outputs_count - 1) {
        idx1++;
        send_req_5_output();
      } else if (to.is_segwit) {
        idx1 = 0;
        send_req_segwit_witness();
      } else {
        send_req_finished();
        signing_abort();
      }
      return;

    case STAGE_REQUEST_SEGWIT_WITNESS:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      if (!signing_sign_segwit_input(&tx->inputs[0])) {
        return;
      }
      signatures++;
      progress = 500 + ((signatures * progress_step) >> PROGRESS_PRECISION);
      layoutProgress(_("Signing transaction"), progress);
      update_ctr = 0;
      if (idx1 < info.inputs_count - 1) {
        idx1++;
        send_req_segwit_witness();
      } else {
        send_req_finished();
        signing_abort();
      }
      return;

#if !BITCOIN_ONLY

    case STAGE_REQUEST_DECRED_WITNESS:
      if (!signing_validate_input(&tx->inputs[0])) {
        return;
      }
      progress =
          500 + ((signatures * progress_step + idx2 * progress_meta_step) >>
                 PROGRESS_PRECISION);
      if (idx1 == 0) {
        // witness
        tx_init(&to, info.inputs_count, info.outputs_count, info.version,
                info.lock_time, info.expiry, 0, coin->curve->hasher_sign,
                coin->overwintered, info.version_group_id, info.timestamp);
        to.is_decred = true;
      }

      // witness hash
      tx_init(&ti, info.inputs_count, info.outputs_count, info.version,
              info.lock_time, info.expiry, 0, coin->curve->hasher_sign,
              coin->overwintered, info.version_group_id, info.timestamp);
      ti.version |= (DECRED_SERIALIZE_WITNESS_SIGNING << 16);
      ti.is_decred = true;
      if (!compile_input_script_sig(&tx->inputs[0])) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to compile input"));
        signing_abort();
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
      // since this took a longer time, update progress
      signatures++;
      progress = 500 + ((signatures * progress_step) >> PROGRESS_PRECISION);
      layoutProgress(_("Signing transaction"), progress);
      update_ctr = 0;
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
