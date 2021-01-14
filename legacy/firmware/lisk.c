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

#include "lisk.h"
#include "bitmaps.h"
#include "crypto.h"
#include "curves.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "messages.pb.h"
#include "protect.h"
#include "util.h"

void lisk_get_address_from_public_key(const uint8_t *public_key,
                                      char *address) {
  uint64_t digest[4] = {0};
  sha256_Raw(public_key, 32, (uint8_t *)digest);
  bn_format_uint64(digest[0], NULL, "L", 0, 0, false, address,
                   MAX_LISK_ADDRESS_SIZE);
}

void lisk_message_hash(const uint8_t *message, size_t message_len,
                       uint8_t hash[32]) {
  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);
  sha256_Update(&ctx, (const uint8_t *)"\x15" "Lisk Signed Message:\n", 22);
  uint8_t varint[5] = {0};
  uint32_t l = ser_length(message_len, varint);
  sha256_Update(&ctx, varint, l);
  sha256_Update(&ctx, message, message_len);
  sha256_Final(&ctx, hash);
  sha256_Raw(hash, 32, hash);
}

void lisk_sign_message(const HDNode *node, const LiskSignMessage *msg,
                       LiskMessageSignature *resp) {
  layoutSignMessage(msg->message.bytes, msg->message.size);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  layoutProgressSwipe(_("Signing"), 0);

  uint8_t signature[64] = {0};
  uint8_t hash[32] = {0};
  lisk_message_hash(msg->message.bytes, msg->message.size, hash);

  ed25519_sign(hash, 32, node->private_key, &node->public_key[1], signature);

  memcpy(resp->signature.bytes, signature, sizeof(signature));
  memcpy(resp->public_key.bytes, &node->public_key[1], 32);

  resp->signature.size = 64;
  resp->public_key.size = 32;
}

bool lisk_verify_message(const LiskVerifyMessage *msg) {
  uint8_t hash[32] = {0};
  lisk_message_hash(msg->message.bytes, msg->message.size, hash);
  return 0 == ed25519_sign_open(hash, 32, msg->public_key.bytes,
                                msg->signature.bytes);
}

static void lisk_update_raw_tx(const HDNode *node, LiskSignTx *msg) {
  if (!msg->transaction.has_sender_public_key) {
    memcpy(msg->transaction.sender_public_key.bytes, &node->public_key[1], 32);
  }

  // For CastVotes transactions, recipientId should be equal to transaction
  // creator address.
  if (msg->transaction.type == LiskTransactionType_CastVotes &&
      !msg->transaction.has_recipient_id) {
    msg->transaction.has_recipient_id = true;
    lisk_get_address_from_public_key(&node->public_key[1],
                                     msg->transaction.recipient_id);
  }
}

static void lisk_hashupdate_uint32(SHA256_CTX *ctx, uint32_t value) {
  uint8_t data[4] = {0};
  write_le(data, value);
  sha256_Update(ctx, data, sizeof(data));
}

static void lisk_hashupdate_uint64_le(SHA256_CTX *ctx, uint64_t value) {
  sha256_Update(ctx, (uint8_t *)&value, sizeof(uint64_t));
}

static void lisk_hashupdate_uint64_be(SHA256_CTX *ctx, uint64_t value) {
  uint8_t data[8] = {0};
  data[0] = value >> 56;
  data[1] = value >> 48;
  data[2] = value >> 40;
  data[3] = value >> 32;
  data[4] = value >> 24;
  data[5] = value >> 16;
  data[6] = value >> 8;
  data[7] = value;
  sha256_Update(ctx, data, sizeof(data));
}

static void lisk_hashupdate_asset(SHA256_CTX *ctx, LiskTransactionType type,
                                  LiskTransactionAsset *asset) {
  switch (type) {
    case LiskTransactionType_Transfer:
      if (asset->has_data) {
        sha256_Update(ctx, (const uint8_t *)asset->data, strlen(asset->data));
      }
      break;
    case LiskTransactionType_RegisterDelegate:
      if (asset->has_delegate && asset->delegate.has_username) {
        sha256_Update(ctx, (const uint8_t *)asset->delegate.username,
                      strlen(asset->delegate.username));
      }
      break;
    case LiskTransactionType_CastVotes: {
      for (int i = 0; i < asset->votes_count; i++) {
        sha256_Update(ctx, (uint8_t *)asset->votes[i], strlen(asset->votes[i]));
      }
      break;
    }
    case LiskTransactionType_RegisterSecondPassphrase:
      if (asset->has_signature && asset->signature.has_public_key) {
        sha256_Update(ctx, asset->signature.public_key.bytes,
                      asset->signature.public_key.size);
      }
      break;
    case LiskTransactionType_RegisterMultisignatureAccount:
      if (asset->has_multisignature) {
        sha256_Update(ctx, (uint8_t *)&(asset->multisignature.min), 1);
        sha256_Update(ctx, (uint8_t *)&(asset->multisignature.life_time), 1);
        for (int i = 0; i < asset->multisignature.keys_group_count; i++) {
          sha256_Update(ctx, (uint8_t *)asset->multisignature.keys_group[i],
                        strlen(asset->multisignature.keys_group[i]));
        };
      }
      break;
    default:
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Invalid transaction type"));
      break;
  }
}

#define MAX_LISK_VALUE_SIZE 20

static void lisk_format_value(uint64_t value, char *formated_value) {
  bn_format_uint64(value, NULL, " LSK", 8, 0, false, formated_value,
                   MAX_LISK_VALUE_SIZE);
}

void lisk_sign_tx(const HDNode *node, LiskSignTx *msg, LiskSignedTx *resp) {
  lisk_update_raw_tx(node, msg);

  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);

  switch (msg->transaction.type) {
    case LiskTransactionType_Transfer:
      layoutRequireConfirmTx(msg->transaction.recipient_id,
                             msg->transaction.amount);
      break;
    case LiskTransactionType_RegisterDelegate:
      layoutRequireConfirmDelegateRegistration(&msg->transaction.asset);
      break;
    case LiskTransactionType_CastVotes:
      layoutRequireConfirmCastVotes(&msg->transaction.asset);
      break;
    case LiskTransactionType_RegisterSecondPassphrase:
      layoutLiskPublicKey(msg->transaction.asset.signature.public_key.bytes);
      break;
    case LiskTransactionType_RegisterMultisignatureAccount:
      layoutRequireConfirmMultisig(&msg->transaction.asset);
      break;
    default:
      fsm_sendFailure(FailureType_Failure_DataError,
                      _("Invalid transaction type"));
      layoutHome();
      break;
  }
  if (!protectButton(
          (msg->transaction.type == LiskTransactionType_RegisterSecondPassphrase
               ? ButtonRequestType_ButtonRequest_PublicKey
               : ButtonRequestType_ButtonRequest_SignTx),
          false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled");
    layoutHome();
    return;
  }

  layoutRequireConfirmFee(msg->transaction.fee, msg->transaction.amount);
  if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmOutput, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, "Signing cancelled");
    layoutHome();
    return;
  }
  layoutProgressSwipe(_("Signing transaction"), 0);

  sha256_Update(&ctx, (const uint8_t *)&msg->transaction.type, 1);

  lisk_hashupdate_uint32(&ctx, msg->transaction.timestamp);

  sha256_Update(&ctx, msg->transaction.sender_public_key.bytes, 32);

  if (msg->transaction.has_requester_public_key) {
    sha256_Update(&ctx, msg->transaction.requester_public_key.bytes,
                  msg->transaction.requester_public_key.size);
  }

  uint64_t recipient_id = 0;
  if (msg->transaction.has_recipient_id &&
      msg->transaction.recipient_id[0] != 0) {
    // parse integer from lisk address ("123L" -> 123)
    for (size_t i = 0; i < strlen(msg->transaction.recipient_id) - 1; i++) {
      if (msg->transaction.recipient_id[i] < '0' ||
          msg->transaction.recipient_id[i] > '9') {
        fsm_sendFailure(FailureType_Failure_DataError,
                        _("Invalid recipient_id"));
        layoutHome();
        return;
      }
      recipient_id *= 10;
      recipient_id += (msg->transaction.recipient_id[i] - '0');
    }
  }
  lisk_hashupdate_uint64_be(&ctx, recipient_id);
  lisk_hashupdate_uint64_le(&ctx, msg->transaction.amount);

  lisk_hashupdate_asset(&ctx, msg->transaction.type, &msg->transaction.asset);

  // if signature exist calculate second signature
  if (msg->transaction.has_signature) {
    sha256_Update(&ctx, msg->transaction.signature.bytes,
                  msg->transaction.signature.size);
  }

  uint8_t hash[32] = {0};
  sha256_Final(&ctx, hash);
  ed25519_sign(hash, 32, node->private_key, &node->public_key[1],
               resp->signature.bytes);

  resp->signature.size = 64;
}

// Layouts
void layoutLiskPublicKey(const uint8_t *pubkey) {
  const char **str = split_message_hex(pubkey, 32);
  layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
                    _("Public Key:"), str[0], str[1], str[2], str[3], NULL);
}

void layoutLiskVerifyAddress(const char *address) {
  const char **str =
      split_message((const uint8_t *)address, strlen(address), 10);
  layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
                    _("Confirm address?"), _("Message signed by:"), str[0],
                    str[1], NULL, NULL, NULL);
}

void layoutRequireConfirmTx(char *recipient_id, uint64_t amount) {
  char formated_amount[MAX_LISK_VALUE_SIZE] = {0};
  const char **str =
      split_message((const uint8_t *)recipient_id, strlen(recipient_id), 16);
  lisk_format_value(amount, formated_amount);
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm sending"), formated_amount, _("to:"), str[0],
                    str[1], NULL);
}

void layoutRequireConfirmFee(uint64_t fee, uint64_t amount) {
  char formated_amount[MAX_LISK_VALUE_SIZE] = {0};
  char formated_fee[MAX_LISK_VALUE_SIZE] = {0};
  lisk_format_value(amount, formated_amount);
  lisk_format_value(fee, formated_fee);
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm transaction"), formated_amount, _("fee:"),
                    formated_fee, NULL, NULL);
}

void layoutRequireConfirmDelegateRegistration(LiskTransactionAsset *asset) {
  if (asset->has_delegate && asset->delegate.has_username) {
    const char **str = split_message((const uint8_t *)asset->delegate.username,
                                     strlen(asset->delegate.username), 20);
    layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                      _("Confirm transaction"), _("Do you really want to"),
                      _("register a delegate?"), str[0], str[1], NULL);
  }
}

void layoutRequireConfirmCastVotes(LiskTransactionAsset *asset) {
  uint8_t plus = 0;
  uint8_t minus = 0;
  char add_votes_txt[13] = {0};
  char remove_votes_txt[16] = {0};

  for (int i = 0; i < asset->votes_count; i++) {
    if (asset->votes[i][0] == '+') {
      plus += 1;
    } else {
      minus += 1;
    }
  }

  bn_format_uint64(plus, "Add ", NULL, 0, 0, false, add_votes_txt,
                   sizeof(add_votes_txt));
  bn_format_uint64(minus, "Remove ", NULL, 0, 0, false, remove_votes_txt,
                   sizeof(remove_votes_txt));

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm transaction"), add_votes_txt, remove_votes_txt,
                    NULL, NULL, NULL);
}

void layoutRequireConfirmMultisig(LiskTransactionAsset *asset) {
  char keys_group_str[25] = {0};
  char life_time_str[14] = {0};
  char min_str[8] = {0};

  bn_format_uint64(asset->multisignature.keys_group_count,
                   "Keys group length: ", NULL, 0, 0, false, keys_group_str,
                   sizeof(keys_group_str));
  bn_format_uint64(asset->multisignature.life_time, "Life time: ", NULL, 0, 0,
                   false, life_time_str, sizeof(life_time_str));
  bn_format_uint64(asset->multisignature.min, "Min: ", NULL, 0, 0, false,
                   min_str, sizeof(min_str));

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm transaction"), keys_group_str, life_time_str,
                    min_str, NULL, NULL);
}
