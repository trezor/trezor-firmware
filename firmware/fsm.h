/*
 * This file is part of the TREZOR project.
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

#ifndef __FSM_H__
#define __FSM_H__

#include "messages.pb.h"

// message functions

void fsm_sendSuccess(const char *text);
void fsm_sendFailure(FailureType code, const char *text);

void fsm_msgInitialize(Initialize *msg);
void fsm_msgPing(Ping *msg);
void fsm_msgChangePin(ChangePin *msg);
void fsm_msgWipeDevice(WipeDevice *msg);
void fsm_msgFirmwareErase(FirmwareErase *msg);
void fsm_msgFirmwareUpload(FirmwareUpload *msg);
void fsm_msgGetEntropy(GetEntropy *msg);
void fsm_msgGetPublicKey(GetPublicKey *msg);
void fsm_msgLoadDevice(LoadDevice *msg);
void fsm_msgResetDevice(ResetDevice *msg);
void fsm_msgSignTx(SignTx *msg);
//void fsm_msgPinMatrixAck(PinMatrixAck *msg);
void fsm_msgCancel(Cancel *msg);
void fsm_msgTxAck(TxAck *msg);
void fsm_msgCipherKeyValue(CipherKeyValue *msg);
void fsm_msgClearSession(ClearSession *msg);
void fsm_msgApplySettings(ApplySettings *msg);
//void fsm_msgButtonAck(ButtonAck *msg);
void fsm_msgGetAddress(GetAddress *msg);
void fsm_msgEntropyAck(EntropyAck *msg);
void fsm_msgSignMessage(SignMessage *msg);
void fsm_msgVerifyMessage(VerifyMessage *msg);
void fsm_msgEncryptMessage(EncryptMessage *msg);
void fsm_msgDecryptMessage(DecryptMessage *msg);
//void fsm_msgPassphraseAck(PassphraseAck *msg);
void fsm_msgEstimateTxSize(EstimateTxSize *msg);
void fsm_msgRecoveryDevice(RecoveryDevice *msg);
void fsm_msgWordAck(WordAck *msg);

// debug message functions
#if DEBUG_LINK
//void fsm_msgDebugLinkDecision(DebugLinkDecision *msg);
void fsm_msgDebugLinkGetState(DebugLinkGetState *msg);
void fsm_msgDebugLinkStop(DebugLinkStop *msg);
#endif

#endif
