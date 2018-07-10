/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "messages-bitcoin.pb.h"
#include "messages-crypto.pb.h"
#include "messages-debug.pb.h"
#include "messages-ethereum.pb.h"
#include "messages-management.pb.h"
#include "messages-nem.pb.h"
#include "messages-stellar.pb.h"

// message functions

void fsm_sendSuccess(const char *text);

#if DEBUG_LINK
void fsm_sendFailureDebug(Failure_FailureType code, const char *text, const char *source);

#define fsm_sendFailure(code, text) fsm_sendFailureDebug((code), (text), __FILE__ ":" VERSTR(__LINE__) ":")
#else
void fsm_sendFailure(Failure_FailureType code, const char *text);
#endif

void fsm_msgInitialize(Initialize *msg);
void fsm_msgGetFeatures(GetFeatures *msg);
void fsm_msgPing(Ping *msg);
void fsm_msgChangePin(ChangePin *msg);
void fsm_msgWipeDevice(WipeDevice *msg);
void fsm_msgGetEntropy(GetEntropy *msg);
void fsm_msgGetPublicKey(GetPublicKey *msg);
void fsm_msgLoadDevice(LoadDevice *msg);
void fsm_msgResetDevice(ResetDevice *msg);
void fsm_msgBackupDevice(BackupDevice *msg);
void fsm_msgSignTx(SignTx *msg);
//void fsm_msgPinMatrixAck(PinMatrixAck *msg);
void fsm_msgCancel(Cancel *msg);
void fsm_msgTxAck(TxAck *msg);
void fsm_msgCipherKeyValue(CipherKeyValue *msg);
void fsm_msgClearSession(ClearSession *msg);
void fsm_msgApplySettings(ApplySettings *msg);
void fsm_msgApplyFlags(ApplyFlags *msg);
//void fsm_msgButtonAck(ButtonAck *msg);
void fsm_msgGetAddress(GetAddress *msg);
void fsm_msgEntropyAck(EntropyAck *msg);
void fsm_msgSignMessage(SignMessage *msg);
void fsm_msgVerifyMessage(VerifyMessage *msg);
void fsm_msgSignIdentity(SignIdentity *msg);
void fsm_msgGetECDHSessionKey(GetECDHSessionKey *msg);
/* ECIES disabled
void fsm_msgEncryptMessage(EncryptMessage *msg);
void fsm_msgDecryptMessage(DecryptMessage *msg);
*/
//void fsm_msgPassphraseAck(PassphraseAck *msg);
void fsm_msgRecoveryDevice(RecoveryDevice *msg);
void fsm_msgWordAck(WordAck *msg);
void fsm_msgSetU2FCounter(SetU2FCounter *msg);
void fsm_msgEthereumGetAddress(EthereumGetAddress *msg);
void fsm_msgEthereumSignTx(EthereumSignTx *msg);
void fsm_msgEthereumTxAck(EthereumTxAck *msg);
void fsm_msgEthereumSignMessage(EthereumSignMessage *msg);
void fsm_msgEthereumVerifyMessage(EthereumVerifyMessage *msg);

void fsm_msgNEMGetAddress(NEMGetAddress *msg);
void fsm_msgNEMSignTx(NEMSignTx *msg);
void fsm_msgNEMDecryptMessage(NEMDecryptMessage *msg);

void fsm_msgCosiCommit(CosiCommit *msg);
void fsm_msgCosiSign(CosiSign *msg);

// Stellar
void fsm_msgStellarGetAddress(StellarGetAddress *msg);
void fsm_msgStellarGetPublicKey(StellarGetPublicKey *msg);
void fsm_msgStellarSignTx(StellarSignTx *msg);
void fsm_msgStellarPaymentOp(StellarPaymentOp *msg);
void fsm_msgStellarCreateAccountOp(StellarCreateAccountOp *msg);
void fsm_msgStellarPathPaymentOp(StellarPathPaymentOp *msg);
void fsm_msgStellarManageOfferOp(StellarManageOfferOp *msg);
void fsm_msgStellarCreatePassiveOfferOp(StellarCreatePassiveOfferOp *msg);
void fsm_msgStellarSetOptionsOp(StellarSetOptionsOp *msg);
void fsm_msgStellarChangeTrustOp(StellarChangeTrustOp *msg);
void fsm_msgStellarAllowTrustOp(StellarAllowTrustOp *msg);
void fsm_msgStellarAccountMergeOp(StellarAccountMergeOp *msg);
void fsm_msgStellarManageDataOp(StellarManageDataOp *msg);
void fsm_msgStellarBumpSequenceOp(StellarBumpSequenceOp *msg);

// debug message functions
#if DEBUG_LINK
//void fsm_msgDebugLinkDecision(DebugLinkDecision *msg);
void fsm_msgDebugLinkGetState(DebugLinkGetState *msg);
void fsm_msgDebugLinkStop(DebugLinkStop *msg);
void fsm_msgDebugLinkMemoryWrite(DebugLinkMemoryWrite *msg);
void fsm_msgDebugLinkMemoryRead(DebugLinkMemoryRead *msg);
void fsm_msgDebugLinkFlashErase(DebugLinkFlashErase *msg);
#endif

#endif
