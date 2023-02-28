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

static bool fsm_stellarCheckPath(uint32_t address_n_count,
                                 const uint32_t *address_n) {
  if (stellar_path_check(address_n_count, address_n)) {
    return true;
  }

  if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Forbidden key path"));
    return false;
  }

  return fsm_layoutPathWarning();
}

void fsm_msgStellarGetAddress(const StellarGetAddress *msg) {
  RESP_INIT(StellarAddress);

  CHECK_INITIALIZED

  CHECK_PIN

  if (!fsm_stellarCheckPath(msg->address_n_count, msg->address_n)) {
    layoutHome();
    return;
  }

  const HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
  if (!node) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive private key"));
    layoutHome();
    return;
  }

  stellar_publicAddressAsStr(node->public_key + 1, resp->address,
                             sizeof(resp->address));

  if (msg->has_show_display && msg->show_display) {
    if (!fsm_layoutAddress(resp->address, _("Public account ID"), false, 0,
                           msg->address_n, msg->address_n_count, true, NULL, 0,
                           0, NULL)) {
      return;
    }
  }

  msg_write(MessageType_MessageType_StellarAddress, resp);

  layoutHome();
}

void fsm_msgStellarSignTx(const StellarSignTx *msg) {
  CHECK_INITIALIZED
  CHECK_PIN

  if (!fsm_stellarCheckPath(msg->address_n_count, msg->address_n)) {
    layoutHome();
    return;
  }

  if (!stellar_signingInit(msg)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive private key"));
    layoutHome();
    return;
  }

  // Confirm transaction basics
  stellar_layoutTransactionSummary(msg);

  // Respond with a request for the first operation
  RESP_INIT(StellarTxOpRequest);

  msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
}

void fsm_msgStellarCreateAccountOp(const StellarCreateAccountOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmCreateAccountOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarPaymentOp(const StellarPaymentOp *msg) {
  CHECK_UNLOCKED

  // This will display additional dialogs to the user
  if (!stellar_confirmPaymentOp(msg)) return;

  // Last operation was confirmed, send a StellarSignedTx
  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarPathPaymentStrictReceiveOp(
    const StellarPathPaymentStrictReceiveOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmPathPaymentStrictReceiveOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarPathPaymentStrictSendOp(
    const StellarPathPaymentStrictSendOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmPathPaymentStrictSendOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarManageBuyOfferOp(const StellarManageBuyOfferOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmManageBuyOfferOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarManageSellOfferOp(const StellarManageSellOfferOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmManageSellOfferOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarCreatePassiveSellOfferOp(
    const StellarCreatePassiveSellOfferOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmCreatePassiveSellOfferOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarSetOptionsOp(const StellarSetOptionsOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmSetOptionsOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarChangeTrustOp(const StellarChangeTrustOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmChangeTrustOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarAllowTrustOp(const StellarAllowTrustOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmAllowTrustOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarAccountMergeOp(const StellarAccountMergeOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmAccountMergeOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarManageDataOp(const StellarManageDataOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmManageDataOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}

void fsm_msgStellarBumpSequenceOp(const StellarBumpSequenceOp *msg) {
  CHECK_UNLOCKED

  if (!stellar_confirmBumpSequenceOp(msg)) return;

  if (stellar_allOperationsConfirmed()) {
    RESP_INIT(StellarSignedTx);

    stellar_fillSignedTx(resp);
    msg_write(MessageType_MessageType_StellarSignedTx, resp);
    layoutHome();
  }
  // Request the next operation to sign
  else {
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
  }
}
