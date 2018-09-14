/*
 * This file is part of the TREZOR project.
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

#ifndef __LISK_H__
#define __LISK_H__

#include <stdbool.h>
#include "bip32.h"
#include "fsm.h"
#include "messages-lisk.pb.h"

// Main
int hdnode_get_lisk_address(HDNode *node, char *address);

void lisk_sign_message(HDNode *node, LiskSignMessage *msg, LiskMessageSignature *resp);
bool lisk_verify_message(LiskVerifyMessage *msg);
void lisk_sign_tx(HDNode *node, LiskSignTx *msg, LiskSignedTx *resp);

// Helpers
void lisk_get_address_from_public_key(const uint8_t *public_key, char *address);
void lisk_format_value(uint64_t value, char *formated_value);
void lisk_update_raw_tx(HDNode *node, LiskSignTx *msg);
void lisk_hashupdate_uint64(SHA256_CTX* ctx, uint64_t value, bool i);
void lisk_hashupdate_uint32(SHA256_CTX* ctx, uint32_t value);
void lisk_hashupdate_asset(SHA256_CTX* ctx, LiskTransactionType type, LiskTransactionAsset *asset);

// Layout
void layoutLiskPublicKey(const uint8_t *pubkey);
void layoutLiskVerifyAddress(const char *address);
void layoutRequireConfirmTx(char *recipient_id, uint64_t amount);
void layoutRequireConfirmDelegateRegistration(LiskTransactionAsset *asset);
void layoutRequireConfirmCastVotes(LiskTransactionAsset *asset);
void layoutRequireConfirmMultisig(LiskTransactionAsset *asset);
void layoutRequireConfirmFee(uint64_t fee, uint64_t amount);

#endif
