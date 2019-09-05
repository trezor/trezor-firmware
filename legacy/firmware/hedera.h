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

#ifndef __HEDERA_H__
#define __HEDERA_H__

#include <stdbool.h>
#include "bip32.h"
#include "messages-hedera.pb.h"

void hedera_sign_tx(const HDNode *node, const HederaSignTx *msg,
                    HederaSignedTx *resp);

#define MAX_HEDERA_ADDRESS_SIZE 23

// Layout
void layoutHederaPublicKey(const uint8_t *pubkey);
void layoutHederaRequireConfirmAccountID(const char *account_id);
void layoutHederaRequireConfirmSendHbars(const char *account_id,
                                         uint64_t amount);
void layoutHederaRequireConfirmCreateAccount(uint64_t initial_balance);

#endif
