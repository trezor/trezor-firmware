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

#include "vsys.h"
#include "bitmaps.h"
#include "crypto.h"
#include "curves.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "messages.pb.h"
#include "protect.h"
#include "util.h"
#include "sha3.h"
#include "blake2b.h"
#include "base58.h"
#include "ed25519-donna/curve25519_sign.h"
#include "rand.h"
#include "bignum.h"

#define MAX_AMOUNT_SIZE 20
#define VSYS_ADDR_VER 5
#define MAX_TX_MSG_SIZE 512
#define MAX_ATTACHMENT_SIZE 140
#define VSYS_ADDR_BYTES 26
#define VSYS_TX_ID_BYTES 32


bool vsys_sign_tx(HDNode *node, VsysSignTx *msg, VsysSignedTx *resp) {
  if (strcmp(msg->tx.protocol, PROTOCOL) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Invalid protocol"));
    return false;
  }
  if (strcmp(msg->tx.opc, OPC_TX) != 0) {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Invalid OP Code"));
    return false;
  }
  if (msg->tx.api > SUPPORT_API_VER) {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Need upgrade firmware for signing this transaction"));
    return false;
  }
  if (!msg->tx.has_senderPublicKey) {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Missing sender public key"));
    return false;
  }
  size_t public_key_size = 45;
  char b58_public_key[45];
  b58enc(b58_public_key, &public_key_size, &node->public_key[1], 32);
  if (strcmp(b58_public_key, msg->tx.senderPublicKey) != 0) {
    char err_msg[180];
    strcpy(err_msg, "Public key mismatch (Trezor: ");
    strcat(err_msg, b58_public_key);
    strcat(err_msg, ". Sender: ");
    strcat(err_msg, msg->tx.senderPublicKey);
    strcat(err_msg, ").");
    fsm_sendFailure(FailureType_Failure_DataError, _(err_msg));
    return false;
  }

  size_t to_sign_bytes_len;
  uint8_t to_sign_bytes[MAX_TX_MSG_SIZE];

  if (msg->tx.transactionType == PAYMENT_TX_TYPE) {
    encode_payment_tx_to_bytes(msg, to_sign_bytes, &to_sign_bytes_len);
  } else if (msg->tx.transactionType == LEASE_TX_TYPE) {
    encode_lease_tx_to_bytes(msg, to_sign_bytes, &to_sign_bytes_len);
  } else if (msg->tx.transactionType == LEASE_CANCEL_TX_TYPE) {
    encode_cancel_lease_tx_to_bytes(msg, to_sign_bytes, &to_sign_bytes_len);
  } else {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Transaction type unsupported"));
    return false;
  }

  uint8_t signature[64];
  uint8_t random[64];
  random_buffer(random, 64);
  uint8_t *sk = node->private_key;
  sk[0] &= 248;
  sk[31] = (sk[31] & 127) | 64;
  curve25519_sign(signature, (const unsigned char*)sk, to_sign_bytes,
                  to_sign_bytes_len, random);
  char signature_b58[89];
  size_t signature_b58_size = 89;
  b58enc(signature_b58, &signature_b58_size, signature, 64);
  resp->has_signature = true;
  strcpy(resp->signature, signature_b58);
  return true;
}

// Helpers
static void vsys_secure_hash(const uint8_t *message, size_t message_len,
                             uint8_t output[32]) {
  uint8_t hash[32];
  blake2b(message, message_len, hash, 32);
  keccak_256(hash, 32, output);
}

char get_network_byte(const uint32_t *address_n, size_t address_n_count) {
  return address_n_count >= 3 && address_n[1] == 0x80000168 ? 'M' : 'T';
}

bool vsys_get_address_from_public_key(const uint8_t *public_key,
                                      char network_byte, char *address) {
  uint8_t public_key_hash[32];
  uint8_t checksum[32];
  uint8_t address_bytes[26];

  address_bytes[0] = VSYS_ADDR_VER;
  address_bytes[1] = network_byte;

  vsys_secure_hash(public_key, 32, public_key_hash);
  memcpy(address_bytes+2, public_key_hash, 20);

  vsys_secure_hash(address_bytes, 22, checksum);
  memcpy(address_bytes+22, checksum, 4);

  size_t address_size;
  return b58enc(address, &address_size, address_bytes, 26);
}

static void vsys_format_amount(uint64_t value, char *formated_value) {
  bn_format_uint64(value, NULL, " VSYS", 8, 0, false, formated_value,
                   MAX_AMOUNT_SIZE);
}

uint64_t convert_to_nano_sec(uint64_t timestamp) {
  if (timestamp < 10000000000) {
    return timestamp * 1000000000;
  } else if (timestamp < 10000000000000) {
    return timestamp * 1000000;
  } else if (timestamp < 10000000000000000) {
    return timestamp * 1000;
  } else {
    return timestamp;
  }
}

// Encode
void encode_payment_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len) {
  uint8_t* index = ctx;
  ctx[0] = msg->tx.transactionType;
  index += 1;
  write_uint64_be(index, convert_to_nano_sec(msg->tx.timestamp));
  index += 8;
  write_uint64_be(index, msg->tx.amount);
  index += 8;
  write_uint64_be(index, msg->tx.fee);
  index += 8;
  write_uint16_be(index, msg->tx.feeScale);
  index += 2;
  size_t recipient_size = VSYS_ADDR_BYTES;
  uint8_t recipient[VSYS_ADDR_BYTES];
  b58tobin(recipient, &recipient_size, msg->tx.recipient);
  memcpy(index, recipient, recipient_size);
  index += recipient_size;
  size_t attachment_bytes_len = MAX_ATTACHMENT_SIZE;
  uint8_t attachment_bytes[MAX_ATTACHMENT_SIZE];
  uint8_t* attachment_start = attachment_bytes;
  bool is_base58 = b58tobin(attachment_bytes, &attachment_bytes_len,
                            msg->tx.attachment);
  if (is_base58) {
    size_t offset = MAX_ATTACHMENT_SIZE - attachment_bytes_len;
    attachment_start += offset;
  } else {
    attachment_bytes_len = strlen(msg->tx.attachment);
    memcpy(attachment_bytes, msg->tx.attachment, attachment_bytes_len);
  }
  write_uint16_be(index, attachment_bytes_len);
  index += 2;
  memcpy(index, attachment_start, attachment_bytes_len);
  *ctx_len = 55 + attachment_bytes_len; // 55 = 1 + 8 * 3 + 2 + 26 + 2
}

void encode_lease_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len) {
  uint8_t* index = ctx;
  ctx[0] = msg->tx.transactionType;
  index += 1;
  size_t recipient_size = VSYS_ADDR_BYTES;
  uint8_t recipient[VSYS_ADDR_BYTES];
  b58tobin(recipient, &recipient_size, msg->tx.recipient);
  memcpy(index, recipient, recipient_size);
  index += recipient_size;
  write_uint64_be(index, msg->tx.amount);
  index += 8;
  write_uint64_be(index, msg->tx.fee);
  index += 8;
  write_uint16_be(index, msg->tx.feeScale);
  index += 2;
  write_uint64_be(index, convert_to_nano_sec(msg->tx.timestamp));
  index += 8;
  *ctx_len = 53; // 53 = 1 + 26 + 8 + 8 + 2 + 8
}

void encode_cancel_lease_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len) {
  uint8_t* index = ctx;
  ctx[0] = msg->tx.transactionType;
  index += 1;
  write_uint64_be(index, msg->tx.fee);
  index += 8;
  write_uint16_be(index, msg->tx.feeScale);
  index += 2;
  write_uint64_be(index, convert_to_nano_sec(msg->tx.timestamp));
  index += 8;
  size_t lease_id_size = VSYS_TX_ID_BYTES;
  uint8_t lease_id[VSYS_TX_ID_BYTES];
  b58tobin(lease_id, &lease_id_size, msg->tx.txId);
  memcpy(index, lease_id, lease_id_size);
  index += lease_id_size;
  *ctx_len = 51; // 51 = 1 + 8 + 2 + 8 + 32
}

// Layouts
void layoutVsysPublicKey(const uint8_t *pubkey) {
  const char **str = split_message_hex(pubkey, 32);
  layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
                    _("Public Key:"), str[0], str[1], str[2], str[3], NULL);
}

void layoutVsysVerifyAddress(const char *address) {
  const char **str =
      split_message((const uint8_t *)address, strlen(address), 10);
  layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
                    _("Confirm address?"), _("Message signed by:"), str[0],
                    str[1], NULL, NULL, NULL);
}

bool layoutVsysRequireConfirmTx(VsysSignTx *msg) {
  if (msg->tx.transactionType == PAYMENT_TX_TYPE) {
    layoutVsysRequireConfirmPaymentOrLeaseTx(msg, "Confirm sending");
  } else if (msg->tx.transactionType == LEASE_TX_TYPE) {
    layoutVsysRequireConfirmPaymentOrLeaseTx(msg, "Confirm lease");
  } else if (msg->tx.transactionType == LEASE_CANCEL_TX_TYPE) {
    layoutVsysRequireConfirmCancelLeaseTx(msg);
  } else {
    fsm_sendFailure(FailureType_Failure_DataError,
                      _("Transaction type unsupported"));
    return false;
  }
  return true;
}

void layoutVsysRequireConfirmPaymentOrLeaseTx(VsysSignTx *msg, char* title) {
  const uint8_t *recipient_id = (const uint8_t *)msg->tx.recipient;
  size_t recipient_len = strlen(msg->tx.recipient);
  uint64_t amount = msg->tx.amount;
  char formated_amount[MAX_AMOUNT_SIZE] = {0};
  const char **str = split_message(recipient_id, recipient_len, 18);
  vsys_format_amount(amount, formated_amount);
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _(title), formated_amount, _("to:"), str[0], str[1], NULL);
}

void layoutVsysRequireConfirmCancelLeaseTx(VsysSignTx *msg) {
  const uint8_t *tx_id = (const uint8_t *)msg->tx.txId;
  size_t len = strlen(msg->tx.txId);
  const char **str = split_message(tx_id, len, 16);
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm cancel lease"), str[0], str[1], str[2], NULL,
                    NULL);
}