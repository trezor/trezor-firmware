/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2016 Alex Beregszaszi <alex@rtfs.hu>
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

#include "ethereum.h"
#include "fsm.h"
#include "layout2.h"
#include "messages.h"
#include "transaction.h"
#include "ecdsa.h"
#include "protect.h"
#include "crypto.h"
#include "secp256k1.h"
#include "sha3.h"

static bool signing = false;

void ethereum_signing_init(EthereumSignTx *msg, const HDNode *node)
{
	(void)node;

	signing = true;

	fsm_sendFailure(FailureType_Failure_Other, "Unsupported feature");
}

void ethereum_signing_txack(EthereumTxAck *tx)
{
	(void)tx;

	if (!signing) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Signing mode");
		layoutHome();
		return;
	}

	fsm_sendFailure(FailureType_Failure_Other, "Unsupported feature");
}

void ethereum_signing_abort(void)
{
	if (signing) {
		layoutHome();
		signing = false;
	}
}
