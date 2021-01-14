/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 ZuluCrypto <zulucrypto@protonmail.com>
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

// Stellar signing workflow:
//
// 1.  Client sends a StellarSignTx method to the device with transaction header
// information
// 2.  Device confirms transaction details with the user and requests first
// operation
// 3.  Client sends protobuf message with details about the operation to sign
// 4.  Device confirms operation with user
// 5a. If there are more operations in the transaction, device responds with
// StellarTxOpRequest. Go to 3 5b. If the operation is the last one, device
// responds with StellarSignedTx

#include "stellar.h"
#include <stdbool.h>
#include <time.h>
#include "base32.h"
#include "bignum.h"
#include "bip32.h"
#include "config.h"
#include "crypto.h"
#include "fonts.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "oled.h"
#include "protect.h"
#include "util.h"

static bool stellar_signing = false;
static StellarTransaction stellar_activeTx;

/*
 * Starts the signing process and parses the transaction header
 */
bool stellar_signingInit(const StellarSignTx *msg) {
  memzero(&stellar_activeTx, sizeof(StellarTransaction));
  stellar_signing = true;
  // Initialize signing context
  sha256_Init(&(stellar_activeTx.sha256_ctx));

  // Calculate sha256 for network passphrase
  // max length defined in messages.options
  uint8_t network_hash[32] = {0};
  sha256_Raw((uint8_t *)msg->network_passphrase,
             strnlen(msg->network_passphrase, 1024), network_hash);

  uint8_t tx_type_bytes[4] = {0x00, 0x00, 0x00, 0x02};

  // Copy some data into the active tx
  stellar_activeTx.num_operations = msg->num_operations;

  // Start building what will be signed:
  // sha256 of:
  //  sha256(network passphrase)
  //  4-byte unsigned big-endian int type constant (2 for tx)
  //  remaining bytes are operations added in subsequent messages
  stellar_hashupdate_bytes(network_hash, sizeof(network_hash));
  stellar_hashupdate_bytes(tx_type_bytes, sizeof(tx_type_bytes));

  // Public key comes from deriving the specified account path
  const HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
  if (!node) {
    return false;
  }
  memcpy(&(stellar_activeTx.signing_pubkey), node->public_key + 1,
         sizeof(stellar_activeTx.signing_pubkey));

  stellar_activeTx.address_n_count = msg->address_n_count;
  // todo: fix sizeof check
  memcpy(&(stellar_activeTx.address_n), &(msg->address_n),
         sizeof(stellar_activeTx.address_n));

  // Hash: public key
  stellar_hashupdate_address(node->public_key + 1);

  // Hash: fee
  stellar_hashupdate_uint32(msg->fee);

  // Hash: sequence number
  stellar_hashupdate_uint64(msg->sequence_number);

  // Timebounds are only present if timebounds_start or timebounds_end is
  // non-zero
  uint8_t has_timebounds =
      (msg->timebounds_start > 0 || msg->timebounds_end > 0);
  if (has_timebounds) {
    // Hash: the "has timebounds?" boolean
    stellar_hashupdate_bool(true);

    // Timebounds are sent as uint32s since that's all we can display, but they
    // must be hashed as 64-bit values
    stellar_hashupdate_uint32(0);
    stellar_hashupdate_uint32(msg->timebounds_start);

    stellar_hashupdate_uint32(0);
    stellar_hashupdate_uint32(msg->timebounds_end);
  }
  // No timebounds, hash a false boolean
  else {
    stellar_hashupdate_bool(false);
  }

  // Hash: memo
  stellar_hashupdate_uint32(msg->memo_type);
  switch (msg->memo_type) {
    // None, nothing else to do
    case 0:
      break;
    // Text: 4 bytes (size) + up to 28 bytes
    case 1:
      stellar_hashupdate_string((unsigned char *)&(msg->memo_text),
                                strnlen(msg->memo_text, 28));
      break;
    // ID (8 bytes, uint64)
    case 2:
      stellar_hashupdate_uint64(msg->memo_id);
      break;
    // Hash and return are the same data structure (32 byte tx hash)
    case 3:
    case 4:
      stellar_hashupdate_bytes(msg->memo_hash.bytes, msg->memo_hash.size);
      break;
    default:
      break;
  }

  // Hash: number of operations
  stellar_hashupdate_uint32(msg->num_operations);

  // Determine what type of network this transaction is for
  if (strncmp("Public Global Stellar Network ; September 2015",
              msg->network_passphrase, 1024) == 0) {
    stellar_activeTx.network_type = 1;
  } else if (strncmp("Test SDF Network ; September 2015",
                     msg->network_passphrase, 1024) == 0) {
    stellar_activeTx.network_type = 2;
  } else {
    stellar_activeTx.network_type = 3;
  }

  return true;
}

bool stellar_confirmSourceAccount(bool has_source_account,
                                  const char *str_account) {
  if (!has_source_account) {
    stellar_hashupdate_bool(false);
    return true;
  }

  // Convert account string to public key bytes
  uint8_t bytes[32] = {0};
  if (!stellar_getAddressBytes(str_account, bytes)) {
    return false;
  }

  const char **str_addr_rows = stellar_lineBreakAddress(bytes);

  stellar_layoutTransactionDialog(_("Op src account OK?"), NULL,
                                  str_addr_rows[0], str_addr_rows[1],
                                  str_addr_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: source account
  stellar_hashupdate_address(bytes);

  return true;
}

bool stellar_confirmCreateAccountOp(const StellarCreateAccountOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(0);

  // Validate new account and convert to bytes
  uint8_t new_account_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->new_account, new_account_bytes)) {
    stellar_signingAbort(_("Invalid new account address"));
    return false;
  }

  const char **str_addr_rows = stellar_lineBreakAddress(new_account_bytes);

  // Amount being funded
  char str_amount_line[32] = {0};
  char str_amount[32] = {0};
  stellar_format_stroops(msg->starting_balance, str_amount, sizeof(str_amount));

  strlcpy(str_amount_line, _("With "), sizeof(str_amount_line));
  strlcat(str_amount_line, str_amount, sizeof(str_amount_line));
  strlcat(str_amount_line, _(" XLM"), sizeof(str_amount_line));

  stellar_layoutTransactionDialog(_("Create account: "), str_addr_rows[0],
                                  str_addr_rows[1], str_addr_rows[2],
                                  str_amount_line);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: address
  stellar_hashupdate_address(new_account_bytes);
  // Hash: starting amount
  stellar_hashupdate_uint64(msg->starting_balance);

  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmPaymentOp(const StellarPaymentOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(1);

  // Validate destination account and convert to bytes
  uint8_t destination_account_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->destination_account,
                               destination_account_bytes)) {
    stellar_signingAbort(_("Invalid destination account"));
    return false;
  }

  const char **str_addr_rows =
      stellar_lineBreakAddress(destination_account_bytes);

  // To: G...
  char str_to[32] = {0};
  strlcpy(str_to, _("To: "), sizeof(str_to));
  strlcat(str_to, str_addr_rows[0], sizeof(str_to));

  char str_asset_row[32] = {0};
  memzero(str_asset_row, sizeof(str_asset_row));
  stellar_format_asset(&(msg->asset), str_asset_row, sizeof(str_asset_row));

  char str_pay_amount[32] = {0};
  char str_amount[32] = {0};
  stellar_format_stroops(msg->amount, str_amount, sizeof(str_amount));

  strlcpy(str_pay_amount, _("Pay "), sizeof(str_pay_amount));
  strlcat(str_pay_amount, str_amount, sizeof(str_pay_amount));

  stellar_layoutTransactionDialog(str_pay_amount, str_asset_row, str_to,
                                  str_addr_rows[1], str_addr_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash destination
  stellar_hashupdate_address(destination_account_bytes);
  // asset
  stellar_hashupdate_asset(&(msg->asset));
  // amount (even though amount is signed it doesn't matter for hashing)
  stellar_hashupdate_uint64(msg->amount);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmPathPaymentOp(const StellarPathPaymentOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(2);

  // Validate destination account and convert to bytes
  uint8_t destination_account_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->destination_account,
                               destination_account_bytes)) {
    stellar_signingAbort(_("Invalid destination account"));
    return false;
  }
  const char **str_dest_rows =
      stellar_lineBreakAddress(destination_account_bytes);

  // To: G...
  char str_to[32] = {0};
  strlcpy(str_to, _("To: "), sizeof(str_to));
  strlcat(str_to, str_dest_rows[0], sizeof(str_to));

  char str_send_asset[32] = {0};
  char str_dest_asset[32] = {0};
  stellar_format_asset(&(msg->send_asset), str_send_asset,
                       sizeof(str_send_asset));
  stellar_format_asset(&(msg->destination_asset), str_dest_asset,
                       sizeof(str_dest_asset));

  char str_pay_amount[32] = {0};
  char str_amount[32] = {0};
  stellar_format_stroops(msg->destination_amount, str_amount,
                         sizeof(str_amount));

  strlcpy(str_pay_amount, _("Path Pay "), sizeof(str_pay_amount));
  strlcat(str_pay_amount, str_amount, sizeof(str_pay_amount));

  // Confirm what the receiver will get
  /*
  Path Pay 100
  JPY (G1234ABCDEF)
  To: G....
  ....
  ....
  */
  stellar_layoutTransactionDialog(str_pay_amount, str_dest_asset, str_to,
                                  str_dest_rows[1], str_dest_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Confirm what the sender is using to pay
  char str_source_amount[32] = {0};
  char str_source_number[32] = {0};
  stellar_format_stroops(msg->send_max, str_source_number,
                         sizeof(str_source_number));

  strlcpy(str_source_amount, _("Pay Using "), sizeof(str_source_amount));
  strlcat(str_source_amount, str_source_number, sizeof(str_source_amount));

  stellar_layoutTransactionDialog(str_source_amount, str_send_asset, NULL,
                                  _("This is the amount debited"),
                                  _("from your account."));
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }
  // Note: no confirmation for intermediate steps since they don't impact the
  // user

  // Hash send asset
  stellar_hashupdate_asset(&(msg->send_asset));
  // send max (signed vs. unsigned doesn't matter wrt hashing)
  stellar_hashupdate_uint64(msg->send_max);
  // destination account
  stellar_hashupdate_address(destination_account_bytes);
  // destination asset
  stellar_hashupdate_asset(&(msg->destination_asset));
  // destination amount
  stellar_hashupdate_uint64(msg->destination_amount);

  // paths are stored as an array so hash the number of elements as a uint32
  stellar_hashupdate_uint32(msg->paths_count);
  for (uint8_t i = 0; i < msg->paths_count; i++) {
    stellar_hashupdate_asset(&(msg->paths[i]));
  }

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmManageOfferOp(const StellarManageOfferOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(3);

  // New Offer / Delete #123 / Update #123
  char str_offer[32] = {0};
  if (msg->offer_id == 0) {
    strlcpy(str_offer, _("New Offer"), sizeof(str_offer));
  } else {
    char str_offer_id[20] = {0};
    stellar_format_uint64(msg->offer_id, str_offer_id, sizeof(str_offer_id));

    if (msg->amount == 0) {
      strlcpy(str_offer, _("Delete #"), sizeof(str_offer));
    } else {
      strlcpy(str_offer, _("Update #"), sizeof(str_offer));
    }

    strlcat(str_offer, str_offer_id, sizeof(str_offer));
  }

  char str_selling[32] = {0};
  char str_sell_amount[32] = {0};
  char str_selling_asset[32] = {0};

  stellar_format_asset(&(msg->selling_asset), str_selling_asset,
                       sizeof(str_selling_asset));
  stellar_format_stroops(msg->amount, str_sell_amount, sizeof(str_sell_amount));

  /*
   Sell 200
   XLM (Native Asset)
  */
  strlcpy(str_selling, _("Sell "), sizeof(str_selling));
  strlcat(str_selling, str_sell_amount, sizeof(str_selling));

  char str_buying[32] = {0};
  char str_buying_asset[32] = {0};
  char str_price[32] = {0};

  stellar_format_asset(&(msg->buying_asset), str_buying_asset,
                       sizeof(str_buying_asset));
  stellar_format_price(msg->price_n, msg->price_d, str_price,
                       sizeof(str_price));

  /*
   For 0.675952 Per
   USD (G12345678)
   */
  strlcpy(str_buying, _("For "), sizeof(str_buying));
  strlcat(str_buying, str_price, sizeof(str_buying));
  strlcat(str_buying, _(" Per"), sizeof(str_buying));

  stellar_layoutTransactionDialog(str_offer, str_selling, str_selling_asset,
                                  str_buying, str_buying_asset);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash selling asset
  stellar_hashupdate_asset(&(msg->selling_asset));
  // buying asset
  stellar_hashupdate_asset(&(msg->buying_asset));
  // amount to sell (signed vs. unsigned doesn't matter wrt hashing)
  stellar_hashupdate_uint64(msg->amount);
  // numerator
  stellar_hashupdate_uint32(msg->price_n);
  // denominator
  stellar_hashupdate_uint32(msg->price_d);
  // offer ID
  stellar_hashupdate_uint64(msg->offer_id);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmCreatePassiveOfferOp(
    const StellarCreatePassiveOfferOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(4);

  // New Offer / Delete #123 / Update #123
  char str_offer[32] = {0};
  if (msg->amount == 0) {
    strlcpy(str_offer, _("Delete Passive Offer"), sizeof(str_offer));
  } else {
    strlcpy(str_offer, _("New Passive Offer"), sizeof(str_offer));
  }

  char str_selling[32] = {0};
  char str_sell_amount[32] = {0};
  char str_selling_asset[32] = {0};

  stellar_format_asset(&(msg->selling_asset), str_selling_asset,
                       sizeof(str_selling_asset));
  stellar_format_stroops(msg->amount, str_sell_amount, sizeof(str_sell_amount));

  /*
   Sell 200
   XLM (Native Asset)
  */
  strlcpy(str_selling, _("Sell "), sizeof(str_selling));
  strlcat(str_selling, str_sell_amount, sizeof(str_selling));

  char str_buying[32] = {0};
  char str_buying_asset[32] = {0};
  char str_price[32] = {0};

  stellar_format_asset(&(msg->buying_asset), str_buying_asset,
                       sizeof(str_buying_asset));
  stellar_format_price(msg->price_n, msg->price_d, str_price,
                       sizeof(str_price));

  /*
   For 0.675952 Per
   USD (G12345678)
   */
  strlcpy(str_buying, _("For "), sizeof(str_buying));
  strlcat(str_buying, str_price, sizeof(str_buying));
  strlcat(str_buying, _(" Per"), sizeof(str_buying));

  stellar_layoutTransactionDialog(str_offer, str_selling, str_selling_asset,
                                  str_buying, str_buying_asset);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash selling asset
  stellar_hashupdate_asset(&(msg->selling_asset));
  // buying asset
  stellar_hashupdate_asset(&(msg->buying_asset));
  // amount to sell (signed vs. unsigned doesn't matter wrt hashing)
  stellar_hashupdate_uint64(msg->amount);
  // numerator
  stellar_hashupdate_uint32(msg->price_n);
  // denominator
  stellar_hashupdate_uint32(msg->price_d);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmSetOptionsOp(const StellarSetOptionsOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(5);

  // Something like Set Inflation Destination
  char str_title[32] = {0};
  char rows[4][32] = {0};
  int row_idx = 0;
  memzero(rows, sizeof(rows));

  // Inflation destination
  stellar_hashupdate_bool(msg->has_inflation_destination_account);
  if (msg->has_inflation_destination_account) {
    strlcpy(str_title, _("Set Inflation Destination"), sizeof(str_title));

    // Validate account and convert to bytes
    uint8_t inflation_destination_account_bytes[STELLAR_KEY_SIZE] = {0};
    if (!stellar_getAddressBytes(msg->inflation_destination_account,
                                 inflation_destination_account_bytes)) {
      stellar_signingAbort(_("Invalid inflation destination account"));
      return false;
    }
    const char **str_addr_rows =
        stellar_lineBreakAddress(inflation_destination_account_bytes);

    stellar_layoutTransactionDialog(str_title, NULL, str_addr_rows[0],
                                    str_addr_rows[1], str_addr_rows[2]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }

    // address
    stellar_hashupdate_address(inflation_destination_account_bytes);
  }

  // Clear flags
  stellar_hashupdate_bool(msg->has_clear_flags);
  if (msg->has_clear_flags) {
    strlcpy(str_title, _("Clear Flag(s)"), sizeof(str_title));

    // Auth required
    if (msg->clear_flags > 7) {
      stellar_signingAbort(_("Invalid flags"));
      return false;
    }
    if (msg->clear_flags & 0x01) {
      strlcpy(rows[row_idx], _("AUTH_REQUIRED"), sizeof(rows[row_idx]));
      row_idx++;
    }
    // Auth revocable
    if (msg->clear_flags & 0x02) {
      strlcpy(rows[row_idx], _("AUTH_REVOCABLE"), sizeof(rows[row_idx]));
      row_idx++;
    }
    // Auth immutable
    if (msg->clear_flags & 0x04) {
      strlcpy(rows[row_idx], _("AUTH_IMMUTABLE"), sizeof(rows[row_idx]));
      row_idx++;
    }

    stellar_layoutTransactionDialog(str_title, rows[0], rows[1], rows[2],
                                    rows[3]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }
    memzero(rows, sizeof(rows));
    row_idx = 0;

    // Hash flags
    stellar_hashupdate_uint32(msg->clear_flags);
  }

  // Set flags
  stellar_hashupdate_bool(msg->has_set_flags);
  if (msg->has_set_flags) {
    strlcpy(str_title, _("Set Flag(s)"), sizeof(str_title));

    // Auth required
    if (msg->set_flags > 7) {
      stellar_signingAbort(_("Invalid flags"));
      return false;
    }
    if (msg->set_flags & 0x01) {
      strlcpy(rows[row_idx], _("AUTH_REQUIRED"), sizeof(rows[row_idx]));
      row_idx++;
    }
    // Auth revocable
    if (msg->set_flags & 0x02) {
      strlcpy(rows[row_idx], _("AUTH_REVOCABLE"), sizeof(rows[row_idx]));
      row_idx++;
    }
    // Auth immutable
    if (msg->set_flags & 0x04) {
      strlcpy(rows[row_idx], _("AUTH_IMMUTABLE"), sizeof(rows[row_idx]));
      row_idx++;
    }

    stellar_layoutTransactionDialog(str_title, rows[0], rows[1], rows[2],
                                    rows[3]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }
    memzero(rows, sizeof(rows));
    row_idx = 0;

    // Hash flags
    stellar_hashupdate_uint32(msg->set_flags);
  }

  // Account thresholds
  bool show_thresholds_confirm = false;
  row_idx = 0;
  stellar_hashupdate_bool(msg->has_master_weight);
  if (msg->has_master_weight) {
    char str_master_weight[10 + 1] = {0};
    show_thresholds_confirm = true;
    stellar_format_uint32(msg->master_weight, str_master_weight,
                          sizeof(str_master_weight));
    strlcpy(rows[row_idx], _("Master Weight: "), sizeof(rows[row_idx]));
    strlcat(rows[row_idx], str_master_weight, sizeof(rows[row_idx]));
    row_idx++;

    // Hash master weight
    stellar_hashupdate_uint32(msg->master_weight);
  }

  stellar_hashupdate_bool(msg->has_low_threshold);
  if (msg->has_low_threshold) {
    char str_low_threshold[10 + 1] = {0};
    show_thresholds_confirm = true;
    stellar_format_uint32(msg->low_threshold, str_low_threshold,
                          sizeof(str_low_threshold));
    strlcpy(rows[row_idx], _("Low: "), sizeof(rows[row_idx]));
    strlcat(rows[row_idx], str_low_threshold, sizeof(rows[row_idx]));
    row_idx++;

    // Hash low threshold
    stellar_hashupdate_uint32(msg->low_threshold);
  }
  stellar_hashupdate_bool(msg->has_medium_threshold);
  if (msg->has_medium_threshold) {
    char str_med_threshold[10 + 1] = {0};
    show_thresholds_confirm = true;
    stellar_format_uint32(msg->medium_threshold, str_med_threshold,
                          sizeof(str_med_threshold));
    strlcpy(rows[row_idx], _("Medium: "), sizeof(rows[row_idx]));
    strlcat(rows[row_idx], str_med_threshold, sizeof(rows[row_idx]));
    row_idx++;

    // Hash medium threshold
    stellar_hashupdate_uint32(msg->medium_threshold);
  }
  stellar_hashupdate_bool(msg->has_high_threshold);
  if (msg->has_high_threshold) {
    char str_high_threshold[10 + 1] = {0};
    show_thresholds_confirm = true;
    stellar_format_uint32(msg->high_threshold, str_high_threshold,
                          sizeof(str_high_threshold));
    strlcpy(rows[row_idx], _("High: "), sizeof(rows[row_idx]));
    strlcat(rows[row_idx], str_high_threshold, sizeof(rows[row_idx]));
    row_idx++;

    // Hash high threshold
    stellar_hashupdate_uint32(msg->high_threshold);
  }

  if (show_thresholds_confirm) {
    strlcpy(str_title, _("Account Thresholds"), sizeof(str_title));
    stellar_layoutTransactionDialog(str_title, rows[0], rows[1], rows[2],
                                    rows[3]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }
    memzero(rows, sizeof(rows));
    row_idx = 0;
  }

  // Home domain
  stellar_hashupdate_bool(msg->has_home_domain);
  if (msg->has_home_domain) {
    strlcpy(str_title, _("Home Domain"), sizeof(str_title));

    // Split home domain if longer than 22 characters
    int home_domain_len = strnlen(msg->home_domain, 32);
    if (home_domain_len > 22) {
      strlcpy(rows[0], msg->home_domain, 22);
      strlcpy(rows[1], msg->home_domain + 21, sizeof(rows[1]));
    } else {
      strlcpy(rows[0], msg->home_domain, sizeof(rows[0]));
    }

    stellar_layoutTransactionDialog(str_title, rows[0], rows[1], NULL, NULL);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }
    memzero(rows, sizeof(rows));
    row_idx = 0;

    stellar_hashupdate_string((unsigned char *)&(msg->home_domain),
                              strnlen(msg->home_domain, 32));
  }

  // Signer
  stellar_hashupdate_bool(msg->has_signer_type);
  if (msg->has_signer_type) {
    if (msg->signer_weight > 0) {
      strlcpy(str_title, _("Add Signer: "), sizeof(str_title));
    } else {
      strlcpy(str_title, _("REMOVE Signer: "), sizeof(str_title));
    }

    // Format weight as a string
    char str_weight[16] = {0};
    stellar_format_uint32(msg->signer_weight, str_weight, sizeof(str_weight));
    char str_weight_row[32] = {0};
    strlcpy(str_weight_row, _("Weight: "), sizeof(str_weight_row));
    strlcat(str_weight_row, str_weight, sizeof(str_weight_row));

    // 0 = account, 1 = pre-auth, 2 = hash(x)
    char str_signer_type[16] = {0};
    bool needs_hash_confirm = false;
    if (msg->signer_type == 0) {
      strlcpy(str_signer_type, _("account"), sizeof(str_signer_type));
      strlcat(str_title, str_signer_type, sizeof(str_title));

      const char **str_addr_rows =
          stellar_lineBreakAddress(msg->signer_key.bytes);
      stellar_layoutTransactionDialog(str_title, str_weight_row,
                                      str_addr_rows[0], str_addr_rows[1],
                                      str_addr_rows[2]);
      if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
        stellar_signingAbort(_("User canceled"));
        return false;
      }
    }
    if (msg->signer_type == 1) {
      needs_hash_confirm = true;
      strlcpy(str_signer_type, _("pre-auth hash"), sizeof(str_signer_type));
      strlcat(str_title, str_signer_type, sizeof(str_title));

      stellar_layoutTransactionDialog(str_title, str_weight_row, NULL,
                                      _("(confirm hash on next"), _("screen)"));
      if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
        stellar_signingAbort(_("User canceled"));
        return false;
      }
    }
    if (msg->signer_type == 2) {
      needs_hash_confirm = true;
      strlcpy(str_signer_type, _("hash(x)"), sizeof(str_signer_type));
      strlcat(str_title, str_signer_type, sizeof(str_title));

      stellar_layoutTransactionDialog(str_title, str_weight_row, NULL,
                                      _("(confirm hash on next"), _("screen)"));
      if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
        stellar_signingAbort(_("User canceled"));
        return false;
      }
    }

    // Extra confirmation step for hash signers
    if (needs_hash_confirm) {
      data2hex(msg->signer_key.bytes + 0, 8, rows[row_idx++]);
      data2hex(msg->signer_key.bytes + 8, 8, rows[row_idx++]);
      data2hex(msg->signer_key.bytes + 16, 8, rows[row_idx++]);
      data2hex(msg->signer_key.bytes + 24, 8, rows[row_idx++]);

      stellar_layoutTransactionDialog(_("Confirm Hash"), rows[0], rows[1],
                                      rows[2], rows[3]);
      if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
        stellar_signingAbort(_("User canceled"));
        return false;
      }
      memzero(rows, sizeof(rows));
      row_idx = 0;
    }

    // Hash: signer type
    stellar_hashupdate_uint32(msg->signer_type);
    // key
    stellar_hashupdate_bytes(msg->signer_key.bytes, msg->signer_key.size);
    // weight
    stellar_hashupdate_uint32(msg->signer_weight);
  }

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmChangeTrustOp(const StellarChangeTrustOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(6);

  // Add Trust: USD
  char str_title[32] = {0};
  if (msg->limit == 0) {
    strlcpy(str_title, _("DELETE Trust: "), sizeof(str_title));
  } else {
    strlcpy(str_title, _("Add Trust: "), sizeof(str_title));
  }
  strlcat(str_title, msg->asset.code, sizeof(str_title));

  // Amount: MAX (or a number)
  char str_amount_row[32] = {0};
  strlcpy(str_amount_row, _("Amount: "), sizeof(str_amount_row));

  if (msg->limit == 9223372036854775807) {
    strlcat(str_amount_row, _("[Maximum]"), sizeof(str_amount_row));
  } else {
    char str_amount[32] = {0};
    stellar_format_stroops(msg->limit, str_amount, sizeof(str_amount));
    strlcat(str_amount_row, str_amount, sizeof(str_amount_row));
  }

  // Validate destination account and convert to bytes
  uint8_t asset_issuer_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->asset.issuer, asset_issuer_bytes)) {
    stellar_signingAbort(_("User canceled"));
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Invalid asset issuer"));
    return false;
  }

  // Display full issuer address
  const char **str_addr_rows = stellar_lineBreakAddress(asset_issuer_bytes);

  stellar_layoutTransactionDialog(str_title, str_amount_row, str_addr_rows[0],
                                  str_addr_rows[1], str_addr_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: asset
  stellar_hashupdate_asset(&(msg->asset));
  // limit
  stellar_hashupdate_uint64(msg->limit);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmAllowTrustOp(const StellarAllowTrustOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(7);

  // Add Trust: USD
  char str_title[32] = {0};
  if (msg->is_authorized) {
    strlcpy(str_title, _("Allow Trust of"), sizeof(str_title));
  } else {
    strlcpy(str_title, _("REVOKE Trust of"), sizeof(str_title));
  }

  // Asset code
  char str_asset_row[32] = {0};
  strlcpy(str_asset_row, msg->asset_code, sizeof(str_asset_row));

  // Validate account and convert to bytes
  uint8_t trusted_account_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->trusted_account, trusted_account_bytes)) {
    stellar_signingAbort(_("Invalid trusted account"));
    return false;
  }

  const char **str_trustor_rows =
      stellar_lineBreakAddress(trusted_account_bytes);

  // By: G...
  char str_by[32] = {0};
  strlcpy(str_by, _("By: "), sizeof(str_by));
  strlcat(str_by, str_trustor_rows[0], sizeof(str_by));

  stellar_layoutTransactionDialog(str_title, str_asset_row, str_by,
                                  str_trustor_rows[1], str_trustor_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: trustor account (the account being allowed to access the asset)
  stellar_hashupdate_address(trusted_account_bytes);
  // asset type
  stellar_hashupdate_uint32(msg->asset_type);
  // asset code
  if (msg->asset_type == 1) {
    char code4[4 + 1] = {0};
    memzero(code4, sizeof(code4));
    strlcpy(code4, msg->asset_code, sizeof(code4));
    stellar_hashupdate_bytes((uint8_t *)code4, 4);
  }
  if (msg->asset_type == 2) {
    char code12[12 + 1] = {0};
    memzero(code12, sizeof(code12));
    strlcpy(code12, msg->asset_code, sizeof(code12));
    stellar_hashupdate_bytes((uint8_t *)code12, 12);
  }
  // is authorized
  stellar_hashupdate_bool(msg->is_authorized);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmAccountMergeOp(const StellarAccountMergeOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(8);

  // Validate account and convert to bytes
  uint8_t destination_account_bytes[STELLAR_KEY_SIZE] = {0};
  if (!stellar_getAddressBytes(msg->destination_account,
                               destination_account_bytes)) {
    stellar_signingAbort(_("Invalid destination account"));
    return false;
  }

  const char **str_destination_rows =
      stellar_lineBreakAddress(destination_account_bytes);

  stellar_layoutTransactionDialog(
      _("Merge Account"), _("All XLM will be sent to:"),
      str_destination_rows[0], str_destination_rows[1],
      str_destination_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: destination account
  stellar_hashupdate_address(destination_account_bytes);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmManageDataOp(const StellarManageDataOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(10);

  char str_title[32] = {0};
  if (msg->has_value) {
    strlcpy(str_title, _("Set data value key:"), sizeof(str_title));
  } else {
    strlcpy(str_title, _("CLEAR data value key:"), sizeof(str_title));
  }

  // Confirm key
  const char **str_key_lines =
      split_message((const uint8_t *)(msg->key), strnlen(msg->key, 64), 16);

  stellar_layoutTransactionDialog(str_title, str_key_lines[0], str_key_lines[1],
                                  str_key_lines[2], str_key_lines[3]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Confirm value by displaying sha256 hash since this can contain
  // non-printable characters
  if (msg->has_value) {
    strlcpy(str_title, _("Confirm sha256 of value:"), sizeof(str_title));

    char str_hash_digest[SHA256_DIGEST_STRING_LENGTH] = {0};
    sha256_Data(msg->value.bytes, msg->value.size, str_hash_digest);
    const char **str_hash_lines = split_message(
        (const uint8_t *)str_hash_digest, sizeof(str_hash_digest), 16);

    stellar_layoutTransactionDialog(str_title, str_hash_lines[0],
                                    str_hash_lines[1], str_hash_lines[2],
                                    str_hash_lines[3]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return false;
    }
  }

  // Hash: key
  stellar_hashupdate_string((unsigned char *)&(msg->key),
                            strnlen(msg->key, 64));
  // value
  if (msg->has_value) {
    stellar_hashupdate_bool(true);
    stellar_hashupdate_string(msg->value.bytes, msg->value.size);
  } else {
    stellar_hashupdate_bool(false);
  }

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

bool stellar_confirmBumpSequenceOp(const StellarBumpSequenceOp *msg) {
  if (!stellar_signing) return false;

  if (!stellar_confirmSourceAccount(msg->has_source_account,
                                    msg->source_account)) {
    stellar_signingAbort(_("Source account error"));
    return false;
  }

  // Hash: operation type
  stellar_hashupdate_uint32(11);

  char str_bump_to[20] = {0};
  stellar_format_uint64(msg->bump_to, str_bump_to, sizeof(str_bump_to));

  stellar_layoutTransactionDialog(_("Bump Sequence"), _("Set sequence to:"),
                                  str_bump_to, NULL, NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return false;
  }

  // Hash: bump to
  stellar_hashupdate_uint64(msg->bump_to);

  // At this point, the operation is confirmed
  stellar_activeTx.confirmed_operations++;
  return true;
}

void stellar_signingAbort(const char *reason) {
  if (!reason) {
    reason = _("Unknown error");
  }

  stellar_signing = false;
  fsm_sendFailure(FailureType_Failure_ProcessError, reason);
  layoutHome();
}

/**
 * Populates the fields of resp with the signature of the active transaction
 */
void stellar_fillSignedTx(StellarSignedTx *resp) {
  // Finalize the transaction by hashing 4 null bytes representing a (currently
  // unused) empty union
  stellar_hashupdate_uint32(0);

  // Add the public key for verification that the right account was used for
  // signing
  memcpy(resp->public_key.bytes, stellar_activeTx.signing_pubkey, 32);
  resp->public_key.size = 32;

  // Add the signature (note that this does not include the 4-byte hint since it
  // can be calculated from the public key)
  uint8_t signature[64] = {0};
  // Note: this calls sha256_Final on the hash context
  stellar_getSignatureForActiveTx(signature);
  memcpy(resp->signature.bytes, signature, sizeof(signature));
  resp->signature.size = sizeof(signature);
}

bool stellar_allOperationsConfirmed() {
  return stellar_activeTx.confirmed_operations ==
         stellar_activeTx.num_operations;
}

/*
 * Calculates and sets the signature for the active transaction
 */
void stellar_getSignatureForActiveTx(uint8_t *out_signature) {
  const HDNode *node = stellar_deriveNode(stellar_activeTx.address_n,
                                          stellar_activeTx.address_n_count);
  if (!node) {
    // return empty signature when we can't derive node
    memzero(out_signature, 64);
    return;
  }

  // Signature is the ed25519 detached signature of the sha256 of all the bytes
  // that have been read so far
  uint8_t to_sign[32] = {0};
  sha256_Final(&(stellar_activeTx.sha256_ctx), to_sign);

  uint8_t signature[64] = {0};
  ed25519_sign(to_sign, sizeof(to_sign), node->private_key,
               node->public_key + 1, signature);

  memcpy(out_signature, signature, sizeof(signature));
}

/*
 * Returns number (representing stroops) formatted as XLM
 * For example, if number has value 1000000000 then it will be returned as
 * "100.0"
 */
void stellar_format_stroops(uint64_t number, char *out, size_t outlen) {
  bn_format_uint64(number, NULL, NULL, 7, 0, false, out, outlen);
}

/*
 * Formats a price represented as a uint32 numerator and uint32 denominator
 *
 * Note that there may be a loss of precision between the real price value and
 * what is shown to the user
 *
 * Smallest possible price is 1 / 4294967296 which is:
 *  0.00000000023283064365386962890625
 *
 * largest possible price is:
 *  4294967296
 */
void stellar_format_price(uint32_t numerator, uint32_t denominator, char *out,
                          size_t outlen) {
  memzero(out, outlen);

  // early exit for invalid denominator
  if (denominator == 0) {
    strlcpy(out, _("[Invalid Price]"), outlen);
    return;
  }

  // early exit for zero
  if (numerator == 0) {
    strlcpy(out, "0", outlen);
    return;
  }

  int scale = 0;
  uint64_t value = numerator;
  while (value < (UINT64_MAX / 10)) {
    value *= 10;
    scale++;
  }
  value /= denominator;
  while (value < (UINT64_MAX / 10)) {
    value *= 10;
    scale++;
  }

  // Format with bn_format_uint64
  bn_format_uint64(value, NULL, NULL, 6, 6 - scale, true, out, outlen);
}

/*
 * Returns a uint32 formatted as a string
 */
void stellar_format_uint32(uint32_t number, char *out, size_t outlen) {
  bignum256 bn_number = {0};
  bn_read_uint32(number, &bn_number);
  bn_format(&bn_number, NULL, NULL, 0, 0, false, out, outlen);
}

/*
 * Returns a uint64 formatted as a string
 */
void stellar_format_uint64(uint64_t number, char *out, size_t outlen) {
  bn_format_uint64(number, NULL, NULL, 0, 0, false, out, outlen);
}

/*
 * Breaks a 56 character address into 3 lines of lengths 16, 20, 20
 * This is to allow a small label to be prepended to the first line
 */
const char **stellar_lineBreakAddress(const uint8_t *addrbytes) {
  char str_fulladdr[56 + 1] = {0};
  static char rows[3][20 + 1];

  memzero(rows, sizeof(rows));

  // get full address string
  stellar_publicAddressAsStr(addrbytes, str_fulladdr, sizeof(str_fulladdr));

  // Break it into 3 lines
  strlcpy(rows[0], str_fulladdr + 0, 17);
  strlcpy(rows[1], str_fulladdr + 16, 21);
  strlcpy(rows[2], str_fulladdr + 16 + 20, 21);

  static const char *ret[3] = {rows[0], rows[1], rows[2]};
  return ret;
}

/*
 * Returns the asset formatted to fit in a single row
 *
 * Examples:
 *  XLM (Native Asset)
 *  MOBI (G123456789000)
 *  ALPHA12EXAMP (G0987)
 */
void stellar_format_asset(const StellarAssetType *asset, char *str_formatted,
                          size_t len) {
  char str_asset_code[12 + 1] = {0};
  // truncated asset issuer, final length depends on length of asset code
  char str_asset_issuer_trunc[13 + 1] = {0};

  memzero(str_formatted, len);
  memzero(str_asset_code, sizeof(str_asset_code));
  memzero(str_asset_issuer_trunc, sizeof(str_asset_issuer_trunc));

  // Validate issuer account for non-native assets
  if (asset->type != 0 && !stellar_validateAddress(asset->issuer)) {
    stellar_signingAbort(_("Invalid asset issuer"));
    return;
  }

  // Native asset
  if (asset->type == 0) {
    strlcpy(str_formatted, _("XLM (native asset)"), len);
  }
  // 4-character custom
  if (asset->type == 1) {
    memcpy(str_asset_code, asset->code, 4);
    strlcpy(str_formatted, str_asset_code, len);

    // Truncate issuer to 13 chars
    memcpy(str_asset_issuer_trunc, asset->issuer, 13);
  }
  // 12-character custom
  if (asset->type == 2) {
    memcpy(str_asset_code, asset->code, 12);
    strlcpy(str_formatted, str_asset_code, len);

    // Truncate issuer to 5 characters
    memcpy(str_asset_issuer_trunc, asset->issuer, 5);
  }
  // Issuer is read the same way for both types of custom assets
  if (asset->type == 1 || asset->type == 2) {
    strlcat(str_formatted, _(" ("), len);
    strlcat(str_formatted, str_asset_issuer_trunc, len);
    strlcat(str_formatted, _(")"), len);
  }
}

size_t stellar_publicAddressAsStr(const uint8_t *bytes, char *out,
                                  size_t outlen) {
  // version + key bytes + checksum
  uint8_t keylen = 1 + 32 + 2;
  uint8_t bytes_full[keylen];
  memset(bytes_full, 0, sizeof(bytes_full));

  bytes_full[0] = 6 << 3;  // 'G'

  memcpy(bytes_full + 1, bytes, 32);

  // Last two bytes are the checksum
  uint16_t checksum = stellar_crc16(bytes_full, 33);
  bytes_full[keylen - 2] = checksum & 0x00ff;
  bytes_full[keylen - 1] = (checksum >> 8) & 0x00ff;

  base32_encode(bytes_full, keylen, out, outlen, BASE32_ALPHABET_RFC4648);

  // Public key will always be 56 characters
  return 56;
}

/**
 * Stellar account string is a base32-encoded string that starts with "G"
 *
 * It decodes to the following format:
 *  Byte 0 - always 0x30 ("G" when base32 encoded), version byte indicating a
 * public key Bytes 1-33 - 32-byte public key bytes Bytes 34-35 - 2-byte CRC16
 * checksum of the version byte + public key bytes (first 33 bytes)
 *
 * Note that the stellar "seed" (private key) also uses this format except the
 * version byte is 0xC0 which encodes to "S" in base32
 */
bool stellar_validateAddress(const char *str_address) {
  bool valid = false;
  uint8_t decoded[STELLAR_ADDRESS_SIZE_RAW] = {0};
  memzero(decoded, sizeof(decoded));

  if (strlen(str_address) != STELLAR_ADDRESS_SIZE) {
    return false;
  }

  // Check that it decodes correctly
  uint8_t *ret = base32_decode(str_address, STELLAR_ADDRESS_SIZE, decoded,
                               sizeof(decoded), BASE32_ALPHABET_RFC4648);
  valid = (ret != NULL);

  // ... and that version byte is 0x30
  if (valid && decoded[0] != 0x30) {
    valid = false;
  }

  // ... and that checksums match
  uint16_t checksum_expected = stellar_crc16(decoded, 33);
  uint16_t checksum_actual =
      (decoded[34] << 8) | decoded[33];  // unsigned short (little endian)
  if (valid && checksum_expected != checksum_actual) {
    valid = false;
  }

  memzero(decoded, sizeof(decoded));
  return valid;
}

/**
 * Converts a string address (G...) to the 32-byte raw address
 */
bool stellar_getAddressBytes(const char *str_address, uint8_t *out_bytes) {
  uint8_t decoded[STELLAR_ADDRESS_SIZE_RAW] = {0};
  memzero(decoded, sizeof(decoded));

  // Ensure address is valid
  if (!stellar_validateAddress(str_address)) return false;

  base32_decode(str_address, STELLAR_ADDRESS_SIZE, decoded, sizeof(decoded),
                BASE32_ALPHABET_RFC4648);

  // The 32 bytes with offset 1-33 represent the public key
  memcpy(out_bytes, &decoded[1], 32);

  memzero(decoded, sizeof(decoded));
  return true;
}

/*
 * CRC16 implementation compatible with the Stellar version
 * Ported from this implementation:
 * http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html Initial
 * value changed to 0x0000 to match Stellar
 */
uint16_t stellar_crc16(uint8_t *bytes, uint32_t length) {
  // Calculate checksum for existing bytes
  uint16_t crc = 0x0000;
  uint16_t polynomial = 0x1021;
  uint32_t i = 0;
  uint8_t bit = 0;
  uint8_t byte = 0;
  uint8_t bitidx = 0;
  uint8_t c15 = 0;

  for (i = 0; i < length; i++) {
    byte = bytes[i];
    for (bitidx = 0; bitidx < 8; bitidx++) {
      bit = ((byte >> (7 - bitidx) & 1) == 1);
      c15 = ((crc >> 15 & 1) == 1);
      crc <<= 1;
      if (c15 ^ bit) crc ^= polynomial;
    }
  }

  return crc & 0xffff;
}

/*
 * Derives the HDNode at the given index
 * Standard Stellar prefix is m/44'/148'/ and the default account is
 * m/44'/148'/0'
 *
 * All paths must be hardened
 */
const HDNode *stellar_deriveNode(const uint32_t *address_n,
                                 size_t address_n_count) {
  static CONFIDENTIAL HDNode node;
  const char *curve = "ed25519";

  // Device not initialized, passphrase request cancelled, or unsupported curve
  if (!config_getRootNode(&node, curve)) {
    return 0;
  }
  // Failed to derive private key
  if (hdnode_private_ckd_cached(&node, address_n, address_n_count, NULL) == 0) {
    return 0;
  }

  hdnode_fill_public_key(&node);

  return &node;
}

void stellar_hashupdate_uint32(uint32_t value) {
  // Ensure uint32 is big endian
#if BYTE_ORDER == LITTLE_ENDIAN
  REVERSE32(value, value);
#endif

  // Byte values must be hashed as big endian
  uint8_t data[4] = {0};
  data[3] = (value >> 24) & 0xFF;
  data[2] = (value >> 16) & 0xFF;
  data[1] = (value >> 8) & 0xFF;
  data[0] = value & 0xFF;

  stellar_hashupdate_bytes(data, sizeof(data));
}

void stellar_hashupdate_uint64(uint64_t value) {
  // Ensure uint64 is big endian
#if BYTE_ORDER == LITTLE_ENDIAN
  REVERSE64(value, value);
#endif

  // Byte values must be hashed as big endian
  uint8_t data[8] = {0};
  data[7] = (value >> 56) & 0xFF;
  data[6] = (value >> 48) & 0xFF;
  data[5] = (value >> 40) & 0xFF;
  data[4] = (value >> 32) & 0xFF;
  data[3] = (value >> 24) & 0xFF;
  data[2] = (value >> 16) & 0xFF;
  data[1] = (value >> 8) & 0xFF;
  data[0] = value & 0xFF;

  stellar_hashupdate_bytes(data, sizeof(data));
}

void stellar_hashupdate_bool(bool value) {
  if (value) {
    stellar_hashupdate_uint32(1);
  } else {
    stellar_hashupdate_uint32(0);
  }
}

void stellar_hashupdate_string(const uint8_t *data, size_t len) {
  // Hash the length of the string
  stellar_hashupdate_uint32((uint32_t)len);

  // Hash the raw bytes of the string
  stellar_hashupdate_bytes(data, len);

  // If len isn't a multiple of 4, add padding bytes
  int remainder = len % 4;
  uint8_t null_byte[1] = {0x00};
  if (remainder) {
    while (remainder < 4) {
      stellar_hashupdate_bytes(null_byte, 1);
      remainder++;
    }
  }
}

void stellar_hashupdate_address(const uint8_t *address_bytes) {
  // First 4 bytes of an address are the type. There's only one type (0)
  stellar_hashupdate_uint32(0);

  // Remaining part of the address is 32 bytes
  stellar_hashupdate_bytes(address_bytes, 32);
}

/*
 * Note about string handling below: this field is an XDR "opaque" field and not
 * a typical string, so if "TEST" is the asset code then the hashed value needs
 * to be 4 bytes and not include the null at the end of the string
 */
void stellar_hashupdate_asset(const StellarAssetType *asset) {
  stellar_hashupdate_uint32(asset->type);

  // For non-native assets, validate issuer account and convert to bytes
  uint8_t issuer_bytes[STELLAR_KEY_SIZE] = {0};
  if (asset->type != 0 &&
      !stellar_getAddressBytes(asset->issuer, issuer_bytes)) {
    stellar_signingAbort(_("Invalid asset issuer"));
    return;
  }

  // 4-character asset code
  if (asset->type == 1) {
    char code4[4 + 1] = {0};
    memzero(code4, sizeof(code4));
    strlcpy(code4, asset->code, sizeof(code4));

    stellar_hashupdate_bytes((uint8_t *)code4, 4);
    stellar_hashupdate_address(issuer_bytes);
  }

  // 12-character asset code
  if (asset->type == 2) {
    char code12[12 + 1] = {0};
    memzero(code12, sizeof(code12));
    strlcpy(code12, asset->code, sizeof(code12));

    stellar_hashupdate_bytes((uint8_t *)code12, 12);
    stellar_hashupdate_address(issuer_bytes);
  }
}

void stellar_hashupdate_bytes(const uint8_t *data, size_t len) {
  sha256_Update(&(stellar_activeTx.sha256_ctx), data, len);
}

/*
 * Displays a summary of the overall transaction
 */
void stellar_layoutTransactionSummary(const StellarSignTx *msg) {
  char str_lines[5][32] = {0};
  memzero(str_lines, sizeof(str_lines));

  char str_fee[12] = {0};
  char str_num_ops[12] = {0};

  // Will be set to true for some large hashes that don't fit on one screen
  uint8_t needs_memo_hash_confirm = 0;

  // Format the fee
  stellar_format_stroops(msg->fee, str_fee, sizeof(str_fee));

  strlcpy(str_lines[0], _("Fee: "), sizeof(str_lines[0]));
  strlcat(str_lines[0], str_fee, sizeof(str_lines[0]));
  strlcat(str_lines[0], _(" XLM"), sizeof(str_lines[0]));

  // add in numOperations
  stellar_format_uint32(msg->num_operations, str_num_ops, sizeof(str_num_ops));

  strlcat(str_lines[0], _(" ("), sizeof(str_lines[0]));
  strlcat(str_lines[0], str_num_ops, sizeof(str_lines[0]));
  if (msg->num_operations == 1) {
    strlcat(str_lines[0], _(" op)"), sizeof(str_lines[0]));
  } else {
    strlcat(str_lines[0], _(" ops)"), sizeof(str_lines[0]));
  }

  // Display full address being used to sign transaction
  const char **str_addr_rows =
      stellar_lineBreakAddress(stellar_activeTx.signing_pubkey);

  stellar_layoutTransactionDialog(str_lines[0], _("Signing with:"),
                                  str_addr_rows[0], str_addr_rows[1],
                                  str_addr_rows[2]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return;
  }

  // Reset lines for displaying memo
  memzero(str_lines, sizeof(str_lines));

  // Memo: none
  if (msg->memo_type == 0) {
    strlcpy(str_lines[0], _("[No Memo Set]"), sizeof(str_lines[0]));
    strlcpy(str_lines[1], _("Important:"), sizeof(str_lines[0]));
    strlcpy(str_lines[2], _("Many exchanges require"), sizeof(str_lines[0]));
    strlcpy(str_lines[3], _("a memo when depositing."), sizeof(str_lines[0]));
  }
  // Memo: text
  if (msg->memo_type == 1) {
    strlcpy(str_lines[0], _("Memo (TEXT)"), sizeof(str_lines[0]));

    // Split 28-character string into two lines of 19 / 9
    // todo: word wrap method?
    strlcpy(str_lines[1], (const char *)msg->memo_text, 19 + 1);
    strlcpy(str_lines[2], (const char *)(msg->memo_text + 19), 9 + 1);
  }
  // Memo: ID
  if (msg->memo_type == 2) {
    strlcpy(str_lines[0], _("Memo (ID)"), sizeof(str_lines[0]));
    stellar_format_uint64(msg->memo_id, str_lines[1], sizeof(str_lines[1]));
  }
  // Memo: hash
  if (msg->memo_type == 3) {
    needs_memo_hash_confirm = 1;
    strlcpy(str_lines[0], _("Memo (HASH)"), sizeof(str_lines[0]));
  }
  // Memo: return
  if (msg->memo_type == 4) {
    needs_memo_hash_confirm = 1;
    strlcpy(str_lines[0], _("Memo (RETURN)"), sizeof(str_lines[0]));
  }

  if (needs_memo_hash_confirm) {
    data2hex(msg->memo_hash.bytes + 0, 8, str_lines[1]);
    data2hex(msg->memo_hash.bytes + 8, 8, str_lines[2]);
    data2hex(msg->memo_hash.bytes + 16, 8, str_lines[3]);
    data2hex(msg->memo_hash.bytes + 24, 8, str_lines[4]);
  }

  stellar_layoutTransactionDialog(str_lines[0], str_lines[1], str_lines[2],
                                  str_lines[3], str_lines[4]);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    stellar_signingAbort(_("User canceled"));
    return;
  }

  // Verify timebounds, if present
  memzero(str_lines, sizeof(str_lines));

  // Timebound: lower
  if (msg->timebounds_start || msg->timebounds_end) {
    time_t timebound;
    char str_timebound[32] = {0};
    const struct tm *tm = NULL;

    timebound = (time_t)msg->timebounds_start;
    strlcpy(str_lines[0], _("Valid from:"), sizeof(str_lines[0]));
    if (timebound) {
      tm = gmtime(&timebound);
      strftime(str_timebound, sizeof(str_timebound), "%F %T (UTC)", tm);
      strlcpy(str_lines[1], str_timebound, sizeof(str_lines[1]));
    } else {
      strlcpy(str_lines[1], _("[no restriction]"), sizeof(str_lines[1]));
    }

    // Reset for timebound_max
    memzero(str_timebound, sizeof(str_timebound));

    timebound = (time_t)msg->timebounds_end;
    strlcpy(str_lines[2], _("Valid to:"), sizeof(str_lines[2]));
    if (timebound) {
      tm = gmtime(&timebound);
      strftime(str_timebound, sizeof(str_timebound), "%F %T (UTC)", tm);
      strlcpy(str_lines[3], str_timebound, sizeof(str_lines[3]));
    } else {
      strlcpy(str_lines[3], _("[no restriction]"), sizeof(str_lines[3]));
    }
  }

  if (msg->timebounds_start || msg->timebounds_end) {
    stellar_layoutTransactionDialog(_("Confirm Time Bounds"), str_lines[0],
                                    str_lines[1], str_lines[2], str_lines[3]);
    if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
      stellar_signingAbort(_("User canceled"));
      return;
    }
  }
}

/*
 * Most basic dialog used for signing
 *  - Header indicating which key is being used for signing
 *  - 5 rows for content
 *  - Cancel / Next buttons
 *  - Warning message can appear between cancel/next buttons
 */
void stellar_layoutSigningDialog(const char *line1, const char *line2,
                                 const char *line3, const char *line4,
                                 const char *line5, uint32_t *address_n,
                                 size_t address_n_count, const char *warning,
                                 bool is_final_step) {
  // Start with some initial padding and use these to track position as
  // rendering moves down the screen
  int offset_x = 1;
  int offset_y = 1;
  int line_height = 9;

  const HDNode *node = stellar_deriveNode(address_n, address_n_count);
  if (!node) {
    // abort on error
    return;
  }

  char str_pubaddr_truncated[12];  // G???? + null
  memzero(str_pubaddr_truncated, sizeof(str_pubaddr_truncated));

  layoutLast = layoutDialogSwipe;
  layoutSwipe();
  oledClear();

  // Load up public address
  char str_pubaddr[56 + 1] = {0};
  memzero(str_pubaddr, sizeof(str_pubaddr));
  stellar_publicAddressAsStr(node->public_key + 1, str_pubaddr,
                             sizeof(str_pubaddr));
  memcpy(str_pubaddr_truncated, str_pubaddr, sizeof(str_pubaddr_truncated) - 1);

  // Header
  // Ends up as: Signing with GABCDEFGHIJKL
  char str_header[32] = {0};
  memzero(str_header, sizeof(str_header));
  strlcpy(str_header, _("Signing with "), sizeof(str_header));
  strlcat(str_header, str_pubaddr_truncated, sizeof(str_header));

  oledDrawString(offset_x, offset_y, str_header, FONT_STANDARD);
  offset_y += line_height;
  // Invert color on header
  oledInvert(0, 0, OLED_WIDTH, offset_y - 2);

  // Dialog contents begin
  if (line1) {
    oledDrawString(offset_x, offset_y, line1, FONT_STANDARD);
  }
  offset_y += line_height;
  if (line2) {
    oledDrawString(offset_x, offset_y, line2, FONT_STANDARD);
  }
  offset_y += line_height;
  if (line3) {
    oledDrawString(offset_x, offset_y, line3, FONT_STANDARD);
  }
  offset_y += line_height;
  if (line4) {
    oledDrawString(offset_x, offset_y, line4, FONT_STANDARD);
  }
  offset_y += line_height;
  if (line5) {
    oledDrawString(offset_x, offset_y, line5, FONT_STANDARD);
  }
  offset_y += line_height;

  // Cancel button
  layoutButtonNo(_("Cancel"), &bmp_btn_cancel);

  // Warnings (drawn centered between the buttons
  if (warning) {
    oledDrawStringCenter(OLED_WIDTH / 2, OLED_HEIGHT - 8, warning,
                         FONT_STANDARD);
  }

  // Next / sign button
  char str_next_label[8] = {0};
  if (is_final_step) {
    strlcpy(str_next_label, _("SIGN"), sizeof(str_next_label));
  } else {
    strlcpy(str_next_label, _("Next"), sizeof(str_next_label));
  }

  layoutButtonYes(str_next_label, &bmp_btn_confirm);

  oledRefresh();
}

/*
 * Main dialog helper method. Allows displaying 5 lines.
 * A title showing the account being used to sign is always displayed.
 */
void stellar_layoutTransactionDialog(const char *line1, const char *line2,
                                     const char *line3, const char *line4,
                                     const char *line5) {
  char str_warning[16] = {0};
  memzero(str_warning, sizeof(str_warning));

  if (stellar_activeTx.network_type == 2) {
    // Warning: testnet
    strlcpy(str_warning, _("WRN:TN"), sizeof(str_warning));
  }
  if (stellar_activeTx.network_type == 3) {
    // Warning: private network
    strlcpy(str_warning, _("WRN:PN"), sizeof(str_warning));
  }

  stellar_layoutSigningDialog(
      line1, line2, line3, line4, line5, stellar_activeTx.address_n,
      stellar_activeTx.address_n_count, str_warning, false);
}
