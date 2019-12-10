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

static uint32_t inputs_count;
static uint32_t outputs_count;
static const CoinInfo *coin;
static CONFIDENTIAL HDNode root;
static CONFIDENTIAL HDNode node;
static bool signing = false;
enum {
  STAGE_REQUEST_1_INPUT,
  STAGE_REQUEST_2_PREV_META,
  STAGE_REQUEST_2_PREV_INPUT,
  STAGE_REQUEST_2_PREV_OUTPUT,
  STAGE_REQUEST_2_PREV_EXTRADATA,
  STAGE_REQUEST_3_OUTPUT,
  STAGE_REQUEST_4_INPUT,
  STAGE_REQUEST_4_OUTPUT,
  STAGE_REQUEST_SEGWIT_INPUT,
  STAGE_REQUEST_5_OUTPUT,
  STAGE_REQUEST_SEGWIT_WITNESS,
#if !BITCOIN_ONLY
  STAGE_REQUEST_DECRED_WITNESS,
#endif
} signing_stage;
static uint32_t idx1, idx2;
static uint32_t signatures;
static TxRequest resp;
static TxInputType input;
static TxOutputBinType bin_output;
static TxStruct to, tp, ti;
static Hasher hasher_prevouts, hasher_sequence, hasher_outputs, hasher_check;
static uint8_t CONFIDENTIAL privkey[32];
static uint8_t pubkey[33], sig[64];
static uint8_t hash_prevouts[32], hash_sequence[32], hash_outputs[32];
#if !BITCOIN_ONLY
static uint8_t decred_hash_prefix[32];
#endif
static uint8_t hash_check[32];
static uint64_t to_spend, authorized_amount, spending, change_spend;
static uint32_t version = 1;
static uint32_t lock_time = 0;
static uint32_t expiry = 0;
static bool overwintered = false;
static uint32_t version_group_id = 0;
static uint32_t timestamp = 0;
#if !BITCOIN_ONLY
static uint32_t branch_id = 0;
#endif
static uint32_t next_nonsegwit_input;
static uint32_t progress, progress_step, progress_meta_step;
static bool multisig_fp_set, multisig_fp_mismatch;
static uint8_t multisig_fp[32];
static uint32_t in_address_n[8];
static size_t in_address_n_count;
static uint32_t tx_weight;

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

Phase1 - check inputs, previous transactions, and outputs
       - ask for confirmations
       - check fee
=========================================================

foreach I (idx1):
    Request I                                                 STAGE_REQUEST_1_INPUT
    Add I to segwit hash_prevouts, hash_sequence
    Add I to Decred decred_hash_prefix
    Add I to TransactionChecksum (prevout and type)
    if (Decred)
        Return I
    If not segwit, Calculate amount of I:
        Request prevhash I, META                              STAGE_REQUEST_2_PREV_META
        foreach prevhash I (idx2):
            Request prevhash I                                STAGE_REQUEST_2_PREV_INPUT
        foreach prevhash O (idx2):
            Request prevhash O                                STAGE_REQUEST_2_PREV_OUTPUT
            Add amount of prevhash O (which is amount of I)
        Request prevhash extra data (if applicable)           STAGE_REQUEST_2_PREV_EXTRADATA
        Calculate hash of streamed tx, compare to prevhash I
foreach O (idx1):
    Request O                                                 STAGE_REQUEST_3_OUTPUT
    Add O to Decred decred_hash_prefix
    Add O to TransactionChecksum
    if (Decred)
        Return O
    Display output
    Ask for confirmation

Check tx fee
Ask for confirmation

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

void send_req_1_input(void) {
  signing_stage = STAGE_REQUEST_1_INPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXINPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_prev_meta(void) {
  signing_stage = STAGE_REQUEST_2_PREV_META;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXMETA;
  resp.has_details = true;
  resp.details.has_tx_hash = true;
  resp.details.tx_hash.size = input.prev_hash.size;
  memcpy(resp.details.tx_hash.bytes, input.prev_hash.bytes,
         input.prev_hash.size);
  msg_write(MessageType_MessageType_TxRequest, &resp);
}

void send_req_2_prev_input(void) {
  signing_stage = STAGE_REQUEST_2_PREV_INPUT;
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

void send_req_2_prev_output(void) {
  signing_stage = STAGE_REQUEST_2_PREV_OUTPUT;
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

void send_req_2_prev_extradata(uint32_t chunk_offset, uint32_t chunk_len) {
  signing_stage = STAGE_REQUEST_2_PREV_EXTRADATA;
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

void send_req_3_output(void) {
  signing_stage = STAGE_REQUEST_3_OUTPUT;
  resp.has_request_type = true;
  resp.request_type = RequestType_TXOUTPUT;
  resp.has_details = true;
  resp.details.has_request_index = true;
  resp.details.request_index = idx1;
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
  if (idx1 < inputs_count - 1) {
    idx1++;
    send_req_1_input();
  } else {
    //  compute segwit hashPrevouts & hashSequence
    hasher_Final(&hasher_prevouts, hash_prevouts);
    hasher_Final(&hasher_sequence, hash_sequence);
    hasher_Final(&hasher_check, hash_check);
    // init hashOutputs
    hasher_Reset(&hasher_outputs);
    idx1 = 0;
    send_req_3_output();
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

void extract_input_bip32_path(const TxInputType *tinput) {
  if (in_address_n_count == BIP32_NOCHANGEALLOWED) {
    return;
  }
  size_t count = tinput->address_n_count;
  if (count < BIP32_WALLET_DEPTH) {
    // no change address allowed
    in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
  if (in_address_n_count == 0) {
    // initialize in_address_n on first input seen
    in_address_n_count = count;
    // store the bip32 path up to the account
    memcpy(in_address_n, tinput->address_n,
           (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t));
    return;
  }
  // check that all addresses use a path of same length
  if (in_address_n_count != count) {
    in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
  // check that the bip32 path up to the account matches
  if (memcmp(in_address_n, tinput->address_n,
             (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t)) != 0) {
    // mismatch -> no change address allowed
    in_address_n_count = BIP32_NOCHANGEALLOWED;
    return;
  }
}

bool check_change_bip32_path(const TxOutputType *toutput) {
  size_t count = toutput->address_n_count;

  // Check that the change path has the same bip32 path length,
  // the same path up to the account, and that the wallet components
  // (chain id and address) are as expected.
  // Note: count >= BIP32_WALLET_DEPTH and count == in_address_n_count
  // imply that in_address_n_count != BIP32_NOCHANGEALLOWED
  return (count >= BIP32_WALLET_DEPTH && count == in_address_n_count &&
          0 == memcmp(in_address_n, toutput->address_n,
                      (count - BIP32_WALLET_DEPTH) * sizeof(uint32_t)) &&
          toutput->address_n[count - 2] <= BIP32_CHANGE_CHAIN &&
          toutput->address_n[count - 1] <= BIP32_MAX_LAST_ELEMENT);
}

bool compile_input_script_sig(TxInputType *tinput) {
  if (!multisig_fp_mismatch) {
    // check that this is still multisig
    uint8_t h[32] = {0};
    if (!tinput->has_multisig ||
        cryptoMultisigFingerprint(&(tinput->multisig), h) == 0 ||
        memcmp(multisig_fp, h, 32) != 0) {
      // Transaction has changed during signing
      return false;
    }
  }
  if (in_address_n_count != BIP32_NOCHANGEALLOWED) {
    // check that input address didn't change
    size_t count = tinput->address_n_count;
    if (count < 2 || count != in_address_n_count ||
        0 != memcmp(in_address_n, tinput->address_n,
                    (count - 2) * sizeof(uint32_t))) {
      return false;
    }
  }
  memcpy(&node, &root, sizeof(HDNode));
  if (hdnode_private_ckd_cached(&node, tinput->address_n,
                                tinput->address_n_count, NULL) == 0) {
    // Failed to derive private key
    return false;
  }
  hdnode_fill_public_key(&node);
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

void signing_init(const SignTx *msg, const CoinInfo *_coin,
                  const HDNode *_root) {
  inputs_count = msg->inputs_count;
  outputs_count = msg->outputs_count;
  coin = _coin;
  memcpy(&root, _root, sizeof(HDNode));
  version = msg->version;
  lock_time = msg->lock_time;
  expiry = msg->expiry;
#if !BITCOIN_ONLY
  overwintered = msg->has_overwintered && msg->overwintered;
  version_group_id = msg->version_group_id;
  timestamp = msg->timestamp;
  branch_id = msg->branch_id;
  // set default values for Zcash if branch_id is unset
  if (overwintered && (branch_id == 0)) {
    switch (version) {
      case 3:
        branch_id = 0x5BA81B19;  // Overwinter
        break;
      case 4:
        branch_id = 0x76B809BB;  // Sapling
        break;
    }
  }
#endif

  uint32_t size = TXSIZE_HEADER + TXSIZE_FOOTER +
                  ser_length_size(inputs_count) +
                  ser_length_size(outputs_count);
#if !BITCOIN_ONLY
  if (coin->decred) {
    size += 4;                              // Decred expiry
    size += ser_length_size(inputs_count);  // Witness inputs count
  }
#endif

  tx_weight = 4 * size;

  signatures = 0;
  idx1 = 0;
  to_spend = 0;
  spending = 0;
  change_spend = 0;
  authorized_amount = 0;
  memzero(&input, sizeof(TxInputType));
  memzero(&resp, sizeof(TxRequest));

  signing = true;
  progress = 0;
  // we step by 500/inputs_count per input in phase1 and phase2
  // this means 50 % per phase.
  progress_step = (500 << PROGRESS_PRECISION) / inputs_count;

  in_address_n_count = 0;
  multisig_fp_set = false;
  multisig_fp_mismatch = false;
  next_nonsegwit_input = 0xffffffff;

  tx_init(&to, inputs_count, outputs_count, version, lock_time, expiry, 0,
          coin->curve->hasher_sign, overwintered, version_group_id, timestamp);

#if !BITCOIN_ONLY
  if (coin->decred) {
    to.version |= (DECRED_SERIALIZE_FULL << 16);
    to.is_decred = true;

    tx_init(&ti, inputs_count, outputs_count, version, lock_time, expiry, 0,
            coin->curve->hasher_sign, overwintered, version_group_id,
            timestamp);
    ti.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
    ti.is_decred = true;
  }
#endif

  // segwit hashes for hashPrevouts and hashSequence
#if !BITCOIN_ONLY
  if (overwintered) {
    hasher_InitParam(&hasher_prevouts, HASHER_BLAKE2B_PERSONAL,
                     "ZcashPrevoutHash", 16);
    hasher_InitParam(&hasher_sequence, HASHER_BLAKE2B_PERSONAL,
                     "ZcashSequencHash", 16);
    hasher_InitParam(&hasher_outputs, HASHER_BLAKE2B_PERSONAL,
                     "ZcashOutputsHash", 16);
    hasher_Init(&hasher_check, coin->curve->hasher_sign);
  } else
#endif
  {
    hasher_Init(&hasher_prevouts, coin->curve->hasher_sign);
    hasher_Init(&hasher_sequence, coin->curve->hasher_sign);
    hasher_Init(&hasher_outputs, coin->curve->hasher_sign);
    hasher_Init(&hasher_check, coin->curve->hasher_sign);
  }

  layoutProgressSwipe(_("Signing transaction"), 0);

  send_req_1_input();
}

#define MIN(a, b) (((a) < (b)) ? (a) : (b))

static bool signing_check_input(const TxInputType *txinput) {
  /* compute multisig fingerprint */
  /* (if all input share the same fingerprint, outputs having the same
   * fingerprint will be considered as change outputs) */
  if (txinput->has_multisig && !multisig_fp_mismatch) {
    uint8_t h[32] = {0};
    if (cryptoMultisigFingerprint(&txinput->multisig, h) == 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Error computing multisig fingerprint"));
      signing_abort();
      return false;
    }
    if (multisig_fp_set) {
      if (memcmp(multisig_fp, h, 32) != 0) {
        multisig_fp_mismatch = true;
      }
    } else {
      memcpy(multisig_fp, h, 32);
      multisig_fp_set = true;
    }
  } else {  // single signature
    multisig_fp_mismatch = true;
  }
  // remember the input bip32 path
  // change addresses must use the same bip32 path as all inputs
  extract_input_bip32_path(txinput);
  // compute segwit hashPrevouts & hashSequence
  tx_prevout_hash(&hasher_prevouts, txinput);
  tx_sequence_hash(&hasher_sequence, txinput);
#if !BITCOIN_ONLY
  if (coin->decred) {
    if (txinput->decred_script_version > 0) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Decred v1+ scripts are not supported"));
      signing_abort();
      return false;
    }

    // serialize Decred prefix in Phase 1
    resp.has_serialized = true;
    resp.serialized.has_serialized_tx = true;
    resp.serialized.serialized_tx.size =
        tx_serialize_input(&to, txinput, resp.serialized.serialized_tx.bytes);

    // compute Decred hashPrefix
    tx_serialize_input_hash(&ti, txinput);
  }
#endif
  // hash prevout and script type to check it later (relevant for fee
  // computation)
  tx_prevout_hash(&hasher_check, txinput);
  hasher_Update(&hasher_check, (const uint8_t *)&txinput->script_type,
                sizeof(&txinput->script_type));
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
  phase1_request_next_input();
  return true;
}

static bool signing_check_output(TxOutputType *txoutput) {
  // Phase1: Check outputs
  //   add it to hash_outputs
  //   ask user for permission

  // check for change address
  bool is_change = false;
  if (txoutput->address_n_count > 0) {
    if (txoutput->has_address) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Address in change output"));
      signing_abort();
      return false;
    }
    /*
     * For multisig check that all inputs are multisig
     */
    if (txoutput->has_multisig) {
      uint8_t h[32] = {0};
      if (multisig_fp_set && !multisig_fp_mismatch &&
          cryptoMultisigFingerprint(&(txoutput->multisig), h) &&
          memcmp(multisig_fp, h, 32) == 0) {
        is_change = check_change_bip32_path(txoutput);
      }
    } else {
      is_change = check_change_bip32_path(txoutput);
    }
    /*
     * only allow segwit change if amount is smaller than what segwit inputs
     * paid. this was added during the times segwit was not yet fully activated
     * to make sure the user is not tricked to use witness change output
     * instead of regular one therefore creating ANYONECANSPEND output
     */
    if ((txoutput->script_type == OutputScriptType_PAYTOWITNESS ||
         txoutput->script_type == OutputScriptType_PAYTOP2SHWITNESS) &&
        txoutput->amount > authorized_amount) {
      is_change = false;
    }
  }

  if (is_change) {
    if (change_spend == 0) {  // not set
      change_spend = txoutput->amount;
    } else {
      /* We only skip confirmation for the first change output */
      is_change = false;
    }
  }

  if (spending + txoutput->amount < spending) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
    signing_abort();
    return false;
  }
  spending += txoutput->amount;
  int co = compile_output(coin, &root, txoutput, &bin_output, !is_change);
  if (!is_change) {
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
  //  compute segwit hashOuts
  tx_output_hash(&hasher_outputs, &bin_output, coin->decred);
  return true;
}

static bool signing_check_fee(void) {
  if (coin->negative_fee) {
    // bypass check for negative fee coins, required for reward TX
  } else {
    // check fees
    if (spending > to_spend) {
      fsm_sendFailure(FailureType_Failure_NotEnoughFunds,
                      _("Not enough funds"));
      signing_abort();
      return false;
    }
  }
  uint64_t fee = 0;
  if (spending <= to_spend) {
    fee = to_spend - spending;
    if (fee > ((uint64_t)tx_weight * coin->maxfee_kb) / 4000) {
      layoutFeeOverThreshold(coin, fee);
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
  // last confirmation
  layoutConfirmTx(coin, to_spend - change_spend, fee);
  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    signing_abort();
    return false;
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

static void phase1_request_next_output(void) {
  if (idx1 < outputs_count - 1) {
    idx1++;
    send_req_3_output();
  } else {
#if !BITCOIN_ONLY
    if (coin->decred) {
      // compute Decred hashPrefix
      tx_hash_final(&ti, decred_hash_prefix, false);
    }
#endif
    hasher_Final(&hasher_outputs, hash_outputs);
    if (!signing_check_fee()) {
      return;
    }
    // Everything was checked, now phase 2 begins and the transaction is signed.
    progress_meta_step = progress_step / (inputs_count + outputs_count);
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
}

static void signing_hash_bip143(const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
  Hasher hasher_preimage = {0};
  hasher_Init(&hasher_preimage, coin->curve->hasher_sign);
  hasher_Update(&hasher_preimage, (const uint8_t *)&version, 4);  // nVersion
  hasher_Update(&hasher_preimage, hash_prevouts, 32);  // hashPrevouts
  hasher_Update(&hasher_preimage, hash_sequence, 32);  // hashSequence
  tx_prevout_hash(&hasher_preimage, txinput);          // outpoint
  tx_script_hash(&hasher_preimage, txinput->script_sig.size,
                 txinput->script_sig.bytes);  // scriptCode
  hasher_Update(&hasher_preimage, (const uint8_t *)&txinput->amount,
                8);                                   // amount
  tx_sequence_hash(&hasher_preimage, txinput);        // nSequence
  hasher_Update(&hasher_preimage, hash_outputs, 32);  // hashOutputs
  hasher_Update(&hasher_preimage, (const uint8_t *)&lock_time, 4);  // nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type, 4);  // nHashType
  hasher_Final(&hasher_preimage, hash);
}

#if !BITCOIN_ONLY

static void signing_hash_zip143(const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
  uint8_t personal[16] = {0};
  memcpy(personal, "ZcashSigHash", 12);
  memcpy(personal + 12, &branch_id, 4);
  Hasher hasher_preimage = {0};
  hasher_InitParam(&hasher_preimage, HASHER_BLAKE2B_PERSONAL, personal,
                   sizeof(personal));
  uint32_t ver = version | TX_OVERWINTERED;  // 1. nVersion | fOverwintered
  hasher_Update(&hasher_preimage, (const uint8_t *)&ver, 4);
  hasher_Update(&hasher_preimage, (const uint8_t *)&version_group_id,
                4);                                    // 2. nVersionGroupId
  hasher_Update(&hasher_preimage, hash_prevouts, 32);  // 3. hashPrevouts
  hasher_Update(&hasher_preimage, hash_sequence, 32);  // 4. hashSequence
  hasher_Update(&hasher_preimage, hash_outputs, 32);   // 5. hashOutputs
                                                       // 6. hashJoinSplits
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  hasher_Update(&hasher_preimage, (const uint8_t *)&lock_time,
                4);  // 7. nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&expiry,
                4);  // 8. expiryHeight
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type,
                4);  // 9. nHashType

  tx_prevout_hash(&hasher_preimage, txinput);  // 10a. outpoint
  tx_script_hash(&hasher_preimage, txinput->script_sig.size,
                 txinput->script_sig.bytes);  // 10b. scriptCode
  hasher_Update(&hasher_preimage, (const uint8_t *)&txinput->amount,
                8);                             // 10c. value
  tx_sequence_hash(&hasher_preimage, txinput);  // 10d. nSequence

  hasher_Final(&hasher_preimage, hash);
}

static void signing_hash_zip243(const TxInputType *txinput, uint8_t *hash) {
  uint32_t hash_type = signing_hash_type();
  uint8_t personal[16] = {0};
  memcpy(personal, "ZcashSigHash", 12);
  memcpy(personal + 12, &branch_id, 4);
  Hasher hasher_preimage = {0};
  hasher_InitParam(&hasher_preimage, HASHER_BLAKE2B_PERSONAL, personal,
                   sizeof(personal));
  uint32_t ver = version | TX_OVERWINTERED;  // 1. nVersion | fOverwintered
  hasher_Update(&hasher_preimage, (const uint8_t *)&ver, 4);
  hasher_Update(&hasher_preimage, (const uint8_t *)&version_group_id,
                4);                                    // 2. nVersionGroupId
  hasher_Update(&hasher_preimage, hash_prevouts, 32);  // 3. hashPrevouts
  hasher_Update(&hasher_preimage, hash_sequence, 32);  // 4. hashSequence
  hasher_Update(&hasher_preimage, hash_outputs, 32);   // 5. hashOutputs
                                                       // 6. hashJoinSplits
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  // 7. hashShieldedSpends
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  // 8. hashShieldedOutputs
  hasher_Update(&hasher_preimage, (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32);
  hasher_Update(&hasher_preimage, (const uint8_t *)&lock_time,
                4);  // 9. nLockTime
  hasher_Update(&hasher_preimage, (const uint8_t *)&expiry,
                4);  // 10. expiryHeight
  hasher_Update(&hasher_preimage,
                (const uint8_t *)"\x00\x00\x00\x00\x00\x00\x00\x00",
                8);  // 11. valueBalance
  hasher_Update(&hasher_preimage, (const uint8_t *)&hash_type,
                4);  // 12. nHashType

  tx_prevout_hash(&hasher_preimage, txinput);  // 13a. outpoint
  tx_script_hash(&hasher_preimage, txinput->script_sig.size,
                 txinput->script_sig.bytes);  // 13b. scriptCode
  hasher_Update(&hasher_preimage, (const uint8_t *)&txinput->amount,
                8);                             // 13c. value
  tx_sequence_hash(&hasher_preimage, txinput);  // 13d. nSequence

  hasher_Final(&hasher_preimage, hash);
}

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
  if (ecdsa_sign_digest(coin->curve->params, private_key, hash, sig, NULL,
                        NULL) != 0) {
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
  if (memcmp(hash, hash_outputs, 32) != 0) {
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

  if (txinput->script_type == InputScriptType_SPENDWITNESS ||
      txinput->script_type == InputScriptType_SPENDP2SHWITNESS) {
    if (!compile_input_script_sig(txinput)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to compile input"));
      signing_abort();
      return false;
    }
    if (txinput->amount > authorized_amount) {
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Transaction has changed during signing"));
      signing_abort();
      return false;
    }
    authorized_amount -= txinput->amount;

    signing_hash_bip143(txinput, hash);

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
  if (idx1 == inputs_count - 1) {
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
      signing_check_input(&tx->inputs[0]);

      tx_weight += tx_input_weight(coin, &tx->inputs[0]);
#if !BITCOIN_ONLY
      if (coin->decred) {
        tx_weight += tx_decred_witness_weight(&tx->inputs[0]);
      }
#endif

      if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG ||
          tx->inputs[0].script_type == InputScriptType_SPENDADDRESS) {
        memcpy(&input, tx->inputs, sizeof(TxInputType));
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

        if (coin->force_bip143 || overwintered) {
          if (!tx->inputs[0].has_amount) {
            fsm_sendFailure(FailureType_Failure_DataError,
                            _("Expected input with amount"));
            signing_abort();
            return;
          }
          if (to_spend + tx->inputs[0].amount < to_spend) {
            fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
            signing_abort();
            return;
          }
          to_spend += tx->inputs[0].amount;
          authorized_amount += tx->inputs[0].amount;
          phase1_request_next_input();
        } else {
          // remember the first non-segwit input -- this is the first input
          // we need to sign during phase2
          if (next_nonsegwit_input == 0xffffffff) next_nonsegwit_input = idx1;
          send_req_2_prev_meta();
        }
      } else if (tx->inputs[0].script_type == InputScriptType_SPENDWITNESS ||
                 tx->inputs[0].script_type ==
                     InputScriptType_SPENDP2SHWITNESS) {
#if !BITCOIN_ONLY
        if (coin->decred) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Decred does not support Segwit"));
          signing_abort();
          return;
        }
#endif
        if (!coin->has_segwit) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Segwit not enabled on this coin"));
          signing_abort();
          return;
        }
        if (!tx->inputs[0].has_amount) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Segwit input without amount"));
          signing_abort();
          return;
        }
        if (to_spend + tx->inputs[0].amount < to_spend) {
          fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
          signing_abort();
          return;
        }
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
        to_spend += tx->inputs[0].amount;
        authorized_amount += tx->inputs[0].amount;
        phase1_request_next_input();
      } else {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Wrong input script type"));
        signing_abort();
        return;
      }
      return;
    case STAGE_REQUEST_2_PREV_META:
      if (tx->outputs_cnt <= input.prev_index) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Not enough outputs in previous transaction."));
        signing_abort();
        return;
      }
      if (tx->inputs_cnt + tx->outputs_cnt < tx->inputs_cnt) {
        fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
        signing_abort();
        return;
      }
      tx_init(&tp, tx->inputs_cnt, tx->outputs_cnt, tx->version, tx->lock_time,
              tx->expiry, tx->extra_data_len, coin->curve->hasher_sign,
              tx->overwintered, tx->version_group_id, tx->timestamp);
#if !BITCOIN_ONLY
      if (coin->decred) {
        tp.version |= (DECRED_SERIALIZE_NO_WITNESS << 16);
        tp.is_decred = true;
      }
#endif
      progress_meta_step = progress_step / (tp.inputs_len + tp.outputs_len);
      idx2 = 0;
      if (tp.inputs_len > 0) {
        send_req_2_prev_input();
      } else {
        tx_serialize_header_hash(&tp);
        send_req_2_prev_output();
      }
      return;
    case STAGE_REQUEST_2_PREV_INPUT:
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
        send_req_2_prev_input();
      } else {
        idx2 = 0;
        send_req_2_prev_output();
      }
      return;
    case STAGE_REQUEST_2_PREV_OUTPUT:
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
        if (to_spend + tx->bin_outputs[0].amount < to_spend) {
          fsm_sendFailure(FailureType_Failure_DataError, _("Value overflow"));
          signing_abort();
          return;
        }
#if !BITCOIN_ONLY
        if (coin->decred && tx->bin_outputs[0].decred_script_version > 0) {
          fsm_sendFailure(
              FailureType_Failure_DataError,
              _("Decred script version does not match previous output"));
          signing_abort();
          return;
        }
#endif
        to_spend += tx->bin_outputs[0].amount;
      }
      if (idx2 < tp.outputs_len - 1) {
        /* Check prevtx of next input */
        idx2++;
        send_req_2_prev_output();
      } else if (tp.extra_data_len > 0) {  // has extra data
        send_req_2_prev_extradata(0, MIN(1024, tp.extra_data_len));
        return;
      } else {
        /* prevtx is done */
        signing_check_prevtx_hash();
      }
      return;
    case STAGE_REQUEST_2_PREV_EXTRADATA:
      if (!tx_serialize_extra_data_hash(&tp, tx->extra_data.bytes,
                                        tx->extra_data.size)) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to serialize extra data"));
        signing_abort();
        return;
      }
      if (tp.extra_data_received <
          tp.extra_data_len) {  // still some data remanining
        send_req_2_prev_extradata(
            tp.extra_data_received,
            MIN(1024, tp.extra_data_len - tp.extra_data_received));
      } else {
        signing_check_prevtx_hash();
      }
      return;
    case STAGE_REQUEST_3_OUTPUT:
      if (!signing_check_output(&tx->outputs[0])) {
        return;
      }
      tx_weight += tx_output_weight(coin, &tx->outputs[0]);
      phase1_request_next_output();
      return;
    case STAGE_REQUEST_4_INPUT:
      progress =
          500 + ((signatures * progress_step + idx2 * progress_meta_step) >>
                 PROGRESS_PRECISION);
      if (idx2 == 0) {
        tx_init(&ti, inputs_count, outputs_count, version, lock_time, expiry, 0,
                coin->curve->hasher_sign, overwintered, version_group_id,
                timestamp);
        hasher_Reset(&hasher_check);
      }
      // check prevouts and script type
      tx_prevout_hash(&hasher_check, tx->inputs);
      hasher_Update(&hasher_check, (const uint8_t *)&tx->inputs[0].script_type,
                    sizeof(&tx->inputs[0].script_type));
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
      if (idx2 < inputs_count - 1) {
        idx2++;
        send_req_4_input();
      } else {
        uint8_t hash[32] = {0};
        hasher_Final(&hasher_check, hash);
        if (memcmp(hash, hash_check, 32) != 0) {
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
      progress = 500 + ((signatures * progress_step +
                         (inputs_count + idx2) * progress_meta_step) >>
                        PROGRESS_PRECISION);
      if (compile_output(coin, &root, tx->outputs, &bin_output, false) <= 0) {
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
      if (idx2 < outputs_count - 1) {
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
        if (idx1 < inputs_count - 1) {
          idx1++;
          phase2_request_next_input();
        } else {
          idx1 = 0;
          send_req_5_output();
        }
      }
      return;

    case STAGE_REQUEST_SEGWIT_INPUT:
      resp.has_serialized = true;
      resp.serialized.has_signature_index = false;
      resp.serialized.has_signature = false;
      resp.serialized.has_serialized_tx = true;
      if (tx->inputs[0].script_type == InputScriptType_SPENDMULTISIG ||
          tx->inputs[0].script_type == InputScriptType_SPENDADDRESS) {
        if (!(coin->force_bip143 || overwintered)) {
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
        if (tx->inputs[0].amount > authorized_amount) {
          fsm_sendFailure(FailureType_Failure_DataError,
                          _("Transaction has changed during signing"));
          signing_abort();
          return;
        }
        authorized_amount -= tx->inputs[0].amount;

        uint8_t hash[32] = {0};
#if !BITCOIN_ONLY
        if (overwintered) {
          switch (version) {
            case 3:
              signing_hash_zip143(&tx->inputs[0], hash);
              break;
            case 4:
              signing_hash_zip243(&tx->inputs[0], hash);
              break;
            default:
              fsm_sendFailure(
                  FailureType_Failure_DataError,
                  _("Unsupported version for overwintered transaction"));
              signing_abort();
              return;
          }
        } else
#endif
        {
          signing_hash_bip143(&tx->inputs[0], hash);
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
      if (idx1 < inputs_count - 1) {
        idx1++;
        phase2_request_next_input();
      } else {
        idx1 = 0;
        send_req_5_output();
      }
      return;

    case STAGE_REQUEST_5_OUTPUT:
      if (compile_output(coin, &root, tx->outputs, &bin_output, false) <= 0) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to compile output"));
        signing_abort();
        return;
      }
      resp.has_serialized = true;
      resp.serialized.has_serialized_tx = true;
      resp.serialized.serialized_tx.size = tx_serialize_output(
          &to, &bin_output, resp.serialized.serialized_tx.bytes);
      if (idx1 < outputs_count - 1) {
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
      if (!signing_sign_segwit_input(&tx->inputs[0])) {
        return;
      }
      signatures++;
      progress = 500 + ((signatures * progress_step) >> PROGRESS_PRECISION);
      layoutProgress(_("Signing transaction"), progress);
      update_ctr = 0;
      if (idx1 < inputs_count - 1) {
        idx1++;
        send_req_segwit_witness();
      } else {
        send_req_finished();
        signing_abort();
      }
      return;

#if !BITCOIN_ONLY

    case STAGE_REQUEST_DECRED_WITNESS:
      progress =
          500 + ((signatures * progress_step + idx2 * progress_meta_step) >>
                 PROGRESS_PRECISION);
      if (idx1 == 0) {
        // witness
        tx_init(&to, inputs_count, outputs_count, version, lock_time, expiry, 0,
                coin->curve->hasher_sign, overwintered, version_group_id,
                timestamp);
        to.is_decred = true;
      }

      // witness hash
      tx_init(&ti, inputs_count, outputs_count, version, lock_time, expiry, 0,
              coin->curve->hasher_sign, overwintered, version_group_id,
              timestamp);
      ti.version |= (DECRED_SERIALIZE_WITNESS_SIGNING << 16);
      ti.is_decred = true;
      if (!compile_input_script_sig(&tx->inputs[0])) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to compile input"));
        signing_abort();
        return;
      }

      for (idx2 = 0; idx2 < inputs_count; idx2++) {
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
      if (idx1 < inputs_count - 1) {
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
