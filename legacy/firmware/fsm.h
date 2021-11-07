/*
 * This file is part of the Trezor project, https://trezor.io/
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
void fsm_sendFailureDebug(FailureType code, const char *text,
                          const char *source);

#define fsm_sendFailure(code, text) \
  fsm_sendFailureDebug((code), (text), __FILE__ ":" VERSTR(__LINE__) ":")
#else
void fsm_sendFailure(FailureType code, const char *text);
#endif

// void fsm_msgPinMatrixAck(const PinMatrixAck *msg);   // tiny
// void fsm_msgButtonAck(const ButtonAck *msg);         // tiny
// void fsm_msgPassphraseAck(const PassphraseAck *msg); // tiny

// common
void fsm_msgInitialize(const Initialize *msg);
void fsm_msgGetFeatures(const GetFeatures *msg);
void fsm_msgPing(const Ping *msg);
void fsm_msgChangePin(const ChangePin *msg);
void fsm_msgChangeWipeCode(const ChangeWipeCode *msg);
void fsm_msgWipeDevice(const WipeDevice *msg);
void fsm_msgGetEntropy(const GetEntropy *msg);
#if DEBUG_LINK
void fsm_msgLoadDevice(const LoadDevice *msg);
#endif
void fsm_msgResetDevice(const ResetDevice *msg);
void fsm_msgEntropyAck(const EntropyAck *msg);
void fsm_msgBackupDevice(const BackupDevice *msg);
void fsm_msgCancel(const Cancel *msg);
void fsm_msgLockDevice(const LockDevice *msg);
void fsm_msgEndSession(const EndSession *msg);
void fsm_msgApplySettings(const ApplySettings *msg);
void fsm_msgApplyFlags(const ApplyFlags *msg);
void fsm_msgRecoveryDevice(const RecoveryDevice *msg);
void fsm_msgWordAck(const WordAck *msg);
void fsm_msgSetU2FCounter(const SetU2FCounter *msg);
void fsm_msgGetNextU2FCounter(void);

// coin
void fsm_msgGetPublicKey(const GetPublicKey *msg);
void fsm_msgSignTx(const SignTx *msg);
void fsm_msgTxAck(
    TxAck *msg);  // not const because we mutate input/output scripts
void fsm_msgGetAddress(const GetAddress *msg);
void fsm_msgSignMessage(const SignMessage *msg);
void fsm_msgVerifyMessage(const VerifyMessage *msg);

// crypto
void fsm_msgCipherKeyValue(const CipherKeyValue *msg);
void fsm_msgSignIdentity(const SignIdentity *msg);
void fsm_msgGetECDHSessionKey(const GetECDHSessionKey *msg);
void fsm_msgCosiCommit(const CosiCommit *msg);
void fsm_msgCosiSign(const CosiSign *msg);

// debug
#if DEBUG_LINK
// void fsm_msgDebugLinkDecision(const DebugLinkDecision *msg); // tiny
void fsm_msgDebugLinkGetState(const DebugLinkGetState *msg);
void fsm_msgDebugLinkStop(const DebugLinkStop *msg);
void fsm_msgDebugLinkMemoryWrite(const DebugLinkMemoryWrite *msg);
void fsm_msgDebugLinkMemoryRead(const DebugLinkMemoryRead *msg);
void fsm_msgDebugLinkFlashErase(const DebugLinkFlashErase *msg);
#endif

// ethereum
void fsm_msgEthereumGetAddress(const EthereumGetAddress *msg);
void fsm_msgEthereumGetPublicKey(const EthereumGetPublicKey *msg);
void fsm_msgEthereumSignTx(const EthereumSignTx *msg);
void fsm_msgEthereumSignTxEIP1559(const EthereumSignTxEIP1559 *msg);
void fsm_msgEthereumTxAck(const EthereumTxAck *msg);
void fsm_msgEthereumSignMessage(const EthereumSignMessage *msg);
void fsm_msgEthereumVerifyMessage(const EthereumVerifyMessage *msg);

// nem
void fsm_msgNEMGetAddress(
    NEMGetAddress *msg);  // not const because we mutate msg->network
void fsm_msgNEMSignTx(
    NEMSignTx *msg);  // not const because we mutate msg->network
void fsm_msgNEMDecryptMessage(
    NEMDecryptMessage *msg);  // not const because we mutate msg->payload

// stellar
void fsm_msgStellarGetAddress(const StellarGetAddress *msg);
void fsm_msgStellarSignTx(const StellarSignTx *msg);
void fsm_msgStellarPaymentOp(const StellarPaymentOp *msg);
void fsm_msgStellarCreateAccountOp(const StellarCreateAccountOp *msg);
void fsm_msgStellarPathPaymentStrictReceiveOp(
    const StellarPathPaymentStrictReceiveOp *msg);
void fsm_msgStellarPathPaymentStrictSendOp(
    const StellarPathPaymentStrictSendOp *msg);
void fsm_msgStellarManageBuyOfferOp(const StellarManageBuyOfferOp *msg);
void fsm_msgStellarManageSellOfferOp(const StellarManageSellOfferOp *msg);
void fsm_msgStellarCreatePassiveSellOfferOp(
    const StellarCreatePassiveSellOfferOp *msg);
void fsm_msgStellarSetOptionsOp(const StellarSetOptionsOp *msg);
void fsm_msgStellarChangeTrustOp(const StellarChangeTrustOp *msg);
void fsm_msgStellarAllowTrustOp(const StellarAllowTrustOp *msg);
void fsm_msgStellarAccountMergeOp(const StellarAccountMergeOp *msg);
void fsm_msgStellarManageDataOp(const StellarManageDataOp *msg);
void fsm_msgStellarBumpSequenceOp(const StellarBumpSequenceOp *msg);

void fsm_msgRebootToBootloader(void);

bool fsm_layoutSignMessage(const uint8_t *msg, uint32_t len);
bool fsm_layoutVerifyMessage(const uint8_t *msg, uint32_t len);

#endif
