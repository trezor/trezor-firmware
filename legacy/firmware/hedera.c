/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 alepop <alepooop@gmail.com>
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

#include "hedera.h"
#include <pb_decode.h>
#include <stdio.h>
#include "bitmaps.h"
#include "crypto.h"
#include "curves.h"
#include "fsm.h"
#include "gettext.h"
#include "internal-hedera.pb.h"
#include "layout2.h"
#include "messages-hedera.pb.h"
#include "messages.pb.h"
#include "protect.h"
#include "util.h"

// Formatting

#define MAX_HEDERA_VALUE_SIZE 20

static void hedera_format_value(uint64_t value, char *out) {
  bn_format_uint64(value, NULL, " hbars", 9, 0, false, out,
                   MAX_HEDERA_VALUE_SIZE);
}

#define MAX_HEDERA_ID_SIZE 18 + 2 + 2

static void hedera_format_account_id(HederaAccountID id, char *out) {
  snprintf(out, MAX_HEDERA_ID_SIZE, "%lld.%lld.%lld", id.shardNum, id.realmNum,
           id.accountNum);
}

// Signing

void hedera_sign_tx(const HDNode *node, const HederaSignTx *msg,
                    HederaSignedTx *resp) {
  // Decode the proto3 transaction manually

  HederaTransactionBody body;

  pb_istream_t stream =
      pb_istream_from_buffer(msg->transaction.bytes, msg->transaction.size);
  bool decode_ok = pb_decode(&stream, HederaTransactionBody_fields, &body);

  if (!decode_ok) {
    fsm_sendFailure(FailureType_Failure_DataError,
                    "Failed to parse transaction");
    return;
  }

  // Determine what we are signing

  switch (body.which_data) {
    case HederaTransactionBody_cryptoCreateAccount_tag:
      layoutHederaRequireConfirmCreateAccount(
          body.data.cryptoCreateAccount.initialBalance);
      break;

    case HederaTransactionBody_cryptoTransfer_tag:
      if (body.data.cryptoTransfer.transfers.accountAmounts_count != 2) {
        fsm_sendFailure(FailureType_Failure_DataError,
                        "Only 2-party transfers are currently supported");
        return;
      }

      if (body.data.cryptoTransfer.transfers.accountAmounts[0].amount == 0) {
        // Trying to send 0 is special-cased as an account ID confirmation
        // The SENDER or the Id we are confirming is the first one
        HederaAccountID id =
            body.data.cryptoTransfer.transfers.accountAmounts[0].accountID;

        // Format the account ID that we are confirming
        char formatted_id[MAX_HEDERA_ID_SIZE];
        hedera_format_account_id(id, formatted_id);

        // Ask for confirmation to send hbars
        layoutHederaRequireConfirmAccountID(formatted_id);
      } else {
        int64_t transfer_amount = 0;
        HederaAccountID transfer_to = {};

        for (int i = 0;
             i < body.data.cryptoTransfer.transfers.accountAmounts_count; i++) {
          HederaAccountAmount amt =
              body.data.cryptoTransfer.transfers.accountAmounts[i];
          if (amt.amount > 0) {
            // Greater than 0 is the receipient of the transfer
            transfer_to = amt.accountID;
            transfer_amount = amt.amount;
            break;
          }
        }

        // Format the account ID that is the receipient
        char formatted_transfer_to[MAX_HEDERA_ID_SIZE];
        hedera_format_account_id(transfer_to, formatted_transfer_to);

        // Ask for confirmation to send hbars
        layoutHederaRequireConfirmSendHbars(formatted_transfer_to,
                                            transfer_amount);
      }

      break;

    default:
      fsm_sendFailure(FailureType_Failure_DataError, "Unsupported transaction");
      return;
  }

  if (!protectButton(ButtonRequestType_ButtonRequest_SignTx, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled");
    layoutHome();
    return;
  }

  layoutProgressSwipe(_("Signing"), 0);

  uint8_t signature[64];
  ed25519_sign(msg->transaction.bytes, msg->transaction.size, node->private_key,
               &node->public_key[1], signature);

  memcpy(resp->signature.bytes, signature, sizeof(signature));

  resp->has_signature = true;
  resp->signature.size = 64;
}

// Layouts

void layoutHederaPublicKey(const uint8_t *pubkey) {
  const char **str = split_message_hex(pubkey, 32);
  layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
                    _("Public Key:"), str[0], str[1], str[2], str[3], NULL);
}

void layoutHederaRequireConfirmSendHbars(const char *account_id,
                                         uint64_t amount) {
  char formated_amount[MAX_HEDERA_VALUE_SIZE];
  const char **str =
      split_message((const uint8_t *)account_id, strlen(account_id), 16);

  hedera_format_value(amount, formated_amount);

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm sending"), formated_amount, _("to:"), str[0],
                    str[1], NULL);
}

void layoutHederaRequireConfirmAccountID(const char *account_id) {
  const char **str =
      split_message((const uint8_t *)account_id, strlen(account_id), 16);

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm account id:"), str[0], NULL, NULL, NULL, NULL);
}

void layoutHederaRequireConfirmCreateAccount(uint64_t initial_balance) {
  char formated_amount[MAX_HEDERA_VALUE_SIZE];
  hedera_format_value(initial_balance, formated_amount);

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm creating acount with"), formated_amount, NULL,
                    NULL, NULL, NULL);
}
