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

#ifndef __STELLAR_H__
#define __STELLAR_H__

#include <stdbool.h>
#include "base32.h"
#include "bip32.h"
#include "crypto.h"
#include "fsm.h"
#include "messages.pb.h"

// 56 character base-32 encoded string
#define STELLAR_ADDRESS_SIZE 56
// Decodes to 35 bytes
#define STELLAR_ADDRESS_SIZE_RAW 35
// Raw key size is 32 bytes
#define STELLAR_KEY_SIZE 32

typedef struct {
  // BIP32 path to the address being used for signing
  uint32_t address_n[10];
  size_t address_n_count;
  uint8_t signing_pubkey[32];

  // 1 - public network, 2 - official testnet, 3 - other private network
  uint8_t network_type;

  // Total number of operations expected
  uint32_t num_operations;
  // Number that have been confirmed by the user
  uint32_t confirmed_operations;

  // sha256 context that will eventually be signed
  SHA256_CTX sha256_ctx;
} StellarTransaction;

// Signing process
bool stellar_signingInit(const StellarSignTx *tx);
void stellar_signingAbort(const char *reason);
bool stellar_confirmSourceAccount(bool has_source_account,
                                  const char *str_account);
bool stellar_confirmCreateAccountOp(const StellarCreateAccountOp *msg);
bool stellar_confirmPaymentOp(const StellarPaymentOp *msg);
bool stellar_confirmPathPaymentStrictReceiveOp(
    const StellarPathPaymentStrictReceiveOp *msg);
bool stellar_confirmPathPaymentStrictSendOp(
    const StellarPathPaymentStrictSendOp *msg);
bool stellar_confirmManageBuyOfferOp(const StellarManageBuyOfferOp *msg);
bool stellar_confirmManageSellOfferOp(const StellarManageSellOfferOp *msg);
bool stellar_confirmCreatePassiveSellOfferOp(
    const StellarCreatePassiveSellOfferOp *msg);
bool stellar_confirmSetOptionsOp(const StellarSetOptionsOp *msg);
bool stellar_confirmChangeTrustOp(const StellarChangeTrustOp *msg);
bool stellar_confirmAllowTrustOp(const StellarAllowTrustOp *msg);
bool stellar_confirmAccountMergeOp(const StellarAccountMergeOp *msg);
bool stellar_confirmManageDataOp(const StellarManageDataOp *msg);
bool stellar_confirmBumpSequenceOp(const StellarBumpSequenceOp *msg);

// Layout
void stellar_layoutTransactionDialog(const char *line1, const char *line2,
                                     const char *line3, const char *line4,
                                     const char *line5);
void stellar_layoutTransactionSummary(const StellarSignTx *msg);
void stellar_layoutSigningDialog(const char *line1, const char *line2,
                                 const char *line3, const char *line4,
                                 const char *line5, uint32_t *address_n,
                                 size_t address_n_count, const char *warning,
                                 bool is_final_step);

// Helpers
const HDNode *stellar_deriveNode(const uint32_t *address_n,
                                 size_t address_n_count);

size_t stellar_publicAddressAsStr(const uint8_t *bytes, char *out,
                                  size_t outlen);
const char **stellar_lineBreakAddress(const uint8_t *addrbytes);

void stellar_hashupdate_uint32(uint32_t value);
void stellar_hashupdate_uint64(uint64_t value);
void stellar_hashupdate_bool(bool value);
void stellar_hashupdate_string(const uint8_t *data, size_t len);
void stellar_hashupdate_address(const uint8_t *address_bytes);
void stellar_hashupdate_asset(const StellarAsset *asset);
void stellar_hashupdate_bytes(const uint8_t *data, size_t len);

void stellar_fillSignedTx(StellarSignedTx *resp);
bool stellar_allOperationsConfirmed(void);
void stellar_getSignatureForActiveTx(uint8_t *out_signature);

void stellar_format_uint32(uint32_t number, char *out, size_t outlen);
void stellar_format_uint64(uint64_t number, char *out, size_t outlen);
void stellar_format_stroops(uint64_t number, char *out, size_t outlen);
void stellar_format_asset(const StellarAsset *asset, char *str_formatted,
                          size_t len);
void stellar_format_price(uint32_t numerator, uint32_t denominator, char *out,
                          size_t outlen);

bool stellar_validateAddress(const char *str_address);
bool stellar_getAddressBytes(const char *str_address, uint8_t *out_bytes);
uint16_t stellar_crc16(uint8_t *bytes, uint32_t length);

#endif
