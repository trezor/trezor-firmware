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

#ifndef __VSYS_H__
#define __VSYS_H__

#include <stdbool.h>
#include <string.h>
#include "bip32.h"
#include "messages-vsys.pb.h"

#define PROTOCOL "v.systems"

#define OPC_ACCOUNT "account"
#define OPC_TX "transaction"
#define OPC_SIGN "signature"

#define SUPPORT_API_VER 4
#define ACCOUNT_API_VER 1
#define SIGN_API_VER 1

#define PAYMENT_TX_TYPE 2
#define LEASE_TX_TYPE 3
#define LEASE_CANCEL_TX_TYPE 4

bool vsys_sign_tx(HDNode *node, VsysSignTx *msg, VsysSignedTx *resp);

// Helpers
bool vsys_get_address_from_public_key(const uint8_t *public_key,
                                      char network_byte, char *address);
char get_network_byte(const uint32_t *address_n, size_t address_n_count);
uint64_t convert_to_nano_sec(uint64_t timestamp);

// Encode
void encode_payment_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len);
void encode_lease_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len);
void encode_cancel_lease_tx_to_bytes(VsysSignTx *msg, uint8_t *ctx, size_t *ctx_len);

// Layout
void layoutVsysPublicKey(const uint8_t *pubkey);
void layoutVsysVerifyAddress(const char *address);
bool layoutVsysRequireConfirmTx(VsysSignTx *msg);
void layoutVsysRequireConfirmPaymentOrLeaseTx(VsysSignTx *msg, char* title);
void layoutVsysRequireConfirmCancelLeaseTx(VsysSignTx *msg);

#endif
